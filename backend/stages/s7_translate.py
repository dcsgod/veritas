"""
s7_translate.py — Stage 7: Translation Layer (Hindi).
Final-pass only — translates completed English report sections.
All reasoning, extraction, and grading is done in English first.
"""
from __future__ import annotations
import logging

from models import ResearchState
from llm import get_llm

logger = logging.getLogger(__name__)

TRANSLATE_SYSTEM = """
You are a professional Hindi translator. Translate the provided English text to Hindi.
Rules:
- Preserve all proper nouns (names, organizations, places) in their original form.
- Preserve claim IDs (c1, c2, etc.) exactly as-is.
- Preserve grade labels in English (confirmed, disputed, unverified, opinion) — 
  you may add Hindi translation in parentheses.
- Do not add commentary, interpretation, or additional information.
- Translate only — do not summarize or shorten.
"""

TRANSLATE_TEMPLATE = """
Translate the following to Hindi. Preserve all proper nouns and claim IDs unchanged.

Text:
{text}

Return only the translated Hindi text. No JSON, no markdown, no English.
"""


async def _translate_text(text: str, llm) -> str:
    """Translate a single text block to Hindi."""
    if not text or not text.strip():
        return ""
    prompt = TRANSLATE_TEMPLATE.format(text=text)
    try:
        result = await llm.fast_call(prompt, system_extra=TRANSLATE_SYSTEM)
        return result.strip()
    except Exception as e:
        logger.warning(f"[S7] Translation failed: {e}")
        return text  # Return original on failure


async def run_translate(state: ResearchState) -> ResearchState:
    """Stage 7: Translate final report sections to Hindi."""
    logger.info("[S7] Translating report to Hindi")
    llm = get_llm()

    synthesis = state.translations.get("_synthesis", {})

    # Build translation targets
    sections_to_translate = {
        "executive_summary": synthesis.get("executive_summary", ""),
        "section_origin": synthesis.get("section_origin", ""),
        "section_actors": synthesis.get("section_actors", ""),
        "section_escalation": synthesis.get("section_escalation", ""),
        "section_demands": synthesis.get("section_demands", ""),
        "section_counter_narratives": synthesis.get("section_counter_narratives", ""),
        "section_precedents": synthesis.get("section_precedents", ""),
        "verdict_summary": state.verdict.summary if state.verdict else "",
    }

    # Translate claim texts (top 20 for performance)
    claim_translations: dict[str, str] = {}
    for claim in state.graded_claims[:20]:
        translated = await _translate_text(claim.text, llm)
        claim_translations[claim.id] = translated

    # Translate section by section
    section_translations: dict[str, str] = {}
    for key, text in sections_to_translate.items():
        if text:
            section_translations[key] = await _translate_text(text, llm)
        else:
            section_translations[key] = ""

    state.translations["hi"] = {
        "sections": section_translations,
        "claims": claim_translations,
    }

    logger.info("[S7] Hindi translation complete")

    state.events.append({
        "stage": 7,
        "name": "translate",
        "status": "complete",
        "data": {
            "languages": ["hi"],
            "sections_translated": len(section_translations),
            "claims_translated": len(claim_translations),
        },
    })

    state.current_stage = 7
    return state
