"""
llm.py — Rate-limit aware multi-provider LLM client wrapper.

Key Features:
  1. max_retries=0 on AsyncGroq so the SDK never silently blocks for 30s+ on 429s.
  2. Instant fallback to Gemini API candidates if configured.
  3. Throttling lock on Groq calls to prevent concurrent request spikes that trigger 429.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import logging
from typing import Any

from groq import AsyncGroq
from google import genai as google_genai
from google.genai import types as genai_types
from dotenv import load_dotenv

from config import (
    GROQ_API_KEY,
    GEMINI_API_KEY,
    PRIMARY_MODEL,
    FAST_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    FORBIDDEN_INFERENCE_TERMS,
)

logger = logging.getLogger(__name__)

# ── Guardrail system prompt ───────────────────────────────────────────────────
GUARDRAIL_SYSTEM = """
You are a strict evidence-based research analyst. Rules (no exceptions):
1. CLAIMS, FACTS, OPINIONS are separate objects — never merge them.
2. Report only what sources say. Do NOT infer motives or hidden agendas.
3. Never use in your own voice: "politically motivated", "secretly wants",
   "brand-building", "hidden agenda", "deliberately fabricated", "false flag".
4. Never name or profile private citizens.
5. Political affiliation only when documented as public record.
6. Every grade (confirmed/disputed/unverified/opinion) must have a reason.
7. Absence of disconfirming sources ≠ confirmation. State this explicitly.
8. When asked for structured data: respond with ONLY valid JSON.
""".strip()

GEMINI_MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash-lite",
]

# Global throttle lock for Groq calls to prevent simultaneous burst spikes
_groq_lock = asyncio.Lock()


class LLMClient:
    """
    Groq client with max_retries=0 (no internal blocking) + instant Gemini fallback.
    """

    def __init__(self):
        load_dotenv()
        self._groq_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        self._gemini_key = os.getenv("GEMINI_API_KEY", GEMINI_API_KEY)

        # max_retries=0 ensures Groq SDK immediately raises 429 without sleeping 30+ seconds internally
        self._groq = AsyncGroq(api_key=self._groq_key, max_retries=0) if self._groq_key else None
        self._gemini_client = None
        if self._gemini_key and self._gemini_key != "your_gemini_key_here":
            try:
                self._gemini_client = google_genai.Client(api_key=self._gemini_key)
            except Exception as e:
                logger.warning(f"Could not init Gemini client: {e}")

    def _refresh_keys(self):
        """Reload .env keys if updated dynamically."""
        load_dotenv(override=True)
        g_key = os.getenv("GEMINI_API_KEY", "")
        if g_key and g_key != self._gemini_key and g_key != "your_gemini_key_here":
            self._gemini_key = g_key
            try:
                self._gemini_client = google_genai.Client(api_key=self._gemini_key)
                logger.info("Refreshed Gemini API client with new key.")
            except Exception as e:
                logger.warning(f"Failed to init refreshed Gemini key: {e}")

    def _build_system(self, system_extra: str, json_mode: bool) -> str:
        system = GUARDRAIL_SYSTEM
        if system_extra:
            system += "\n\n" + system_extra
        if json_mode:
            system += "\n\nIMPORTANT: Respond with ONLY valid JSON. No markdown fences, no prose."
        return system

    async def _try_gemini(self, system: str, user: str, max_tokens: int) -> str | None:
        """Attempt Gemini call across model candidates."""
        self._refresh_keys()
        if not self._gemini_client:
            return None

        full_prompt = f"{system}\n\n{user}"
        for model in GEMINI_MODEL_CANDIDATES:
            try:
                logger.info(f"Attempting fallback to Gemini model: {model}")
                response = await self._gemini_client.aio.models.generate_content(
                    model=model,
                    contents=full_prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=LLM_TEMPERATURE,
                        max_output_tokens=max_tokens,
                    ),
                )
                if response and response.text:
                    logger.info(f"Gemini ({model}) responded successfully ({len(response.text)} chars).")
                    return response.text
            except Exception as e:
                logger.warning(f"Gemini model {model} failed: {e}")
                continue

        return None

    async def _execute_call(
        self,
        model: str,
        system_extra: str,
        user_prompt: str,
        json_mode: bool,
        max_tokens: int,
    ) -> str:
        system = self._build_system(system_extra, json_mode)

        # Attempt 1: Try Groq with throttle lock
        if self._groq:
            try:
                async with _groq_lock:
                    await asyncio.sleep(0.4)  # throttle gap between Groq requests
                    response = await self._groq.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=LLM_TEMPERATURE,
                        max_tokens=max_tokens,
                    )
                text = response.choices[0].message.content
                logger.debug(f"Groq {model} responded ({len(text)} chars)")
                return text
            except Exception as groq_err:
                err_str = str(groq_err)
                logger.warning(f"Groq {model} direct error (no SDK wait): {err_str[:150]}")

                # Instant fallback to Gemini
                gemini_text = await self._try_gemini(system, user_prompt, max_tokens)
                if gemini_text:
                    return gemini_text

                # If Gemini not available, wait 5s then retry Groq once
                if "429" in err_str or "rate_limit" in err_str.lower():
                    logger.info("Gemini unavailable. Waiting 5s before retrying Groq...")
                    await asyncio.sleep(5)
                    async with _groq_lock:
                        retry_resp = await self._groq.chat.completions.create(
                            model=model,
                            messages=[
                                {"role": "system", "content": system},
                                {"role": "user", "content": user_prompt},
                            ],
                            temperature=LLM_TEMPERATURE,
                            max_tokens=max_tokens,
                        )
                        return retry_resp.choices[0].message.content
                raise groq_err

        # If Groq client not configured, try Gemini directly
        gemini_text = await self._try_gemini(system, user_prompt, max_tokens)
        if gemini_text:
            return gemini_text

        raise RuntimeError("No working LLM provider available.")

    async def call(
        self,
        user_prompt: str,
        system_extra: str = "",
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> str:
        """Llama 3.3 70B primary call with instant Gemini fallback."""
        tokens = max_tokens or LLM_MAX_TOKENS
        return await self._execute_call(PRIMARY_MODEL, system_extra, user_prompt, json_mode, tokens)

    async def fast_call(
        self,
        user_prompt: str,
        system_extra: str = "",
        json_mode: bool = False,
        max_tokens: int | None = None,
    ) -> str:
        """Llama 3.1 8B Instant primary call with instant Gemini fallback."""
        tokens = max_tokens or min(LLM_MAX_TOKENS, 2048)
        return await self._execute_call(FAST_MODEL, system_extra, user_prompt, json_mode, tokens)

    async def call_json(self, user_prompt: str, system_extra: str = "") -> Any:
        raw = await self.call(user_prompt, system_extra=system_extra, json_mode=True)
        return self._extract_json(raw)

    async def fast_call_json(self, user_prompt: str, system_extra: str = "") -> Any:
        raw = await self.fast_call(user_prompt, system_extra=system_extra, json_mode=True)
        return self._extract_json(raw)

    def _extract_json(self, text: str) -> Any:
        text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
            if match:
                try:
                    return json.loads(match.group(1))
                except Exception:
                    pass
            raise ValueError(f"Cannot parse JSON from LLM response:\n{text[:500]}")

    def check_guardrails(self, text: str) -> list[str]:
        tl = text.lower()
        return [t for t in FORBIDDEN_INFERENCE_TERMS if t.lower() in tl]


# Singleton
_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
