"""
s3_extract.py — Stage 3: Claim Extraction.
For each retrieved page, extract atomic claims with source + stance tagging.
Deduplicates near-identical claims across pages.
"""
from __future__ import annotations
import asyncio
import logging
import uuid

from models import Claim, ClaimSource, ResearchState
from llm import get_llm

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM = """
You extract atomic, checkable claims from news articles.
Rules:
- Each claim must be a single verifiable assertion (one sentence).
- Do not merge multiple claims into one.
- Do not add interpretation, motive speculation, or judgment.
- Do not identify or profile private/unnamed individuals.
- For each claim, record: the outlet's stance (reports as fact | disputes | alleges | opinion).
- Quote the minimal supporting text (paraphrase, not verbatim copy).
"""

EXTRACT_TEMPLATE = """
Source: {outlet} | URL: {url} | Date: {date}
Sub-question this page addresses: {sub_question}

Article text:
{text}

Extract all atomic, checkable claims from this article. For each claim:
- state it as a single, direct assertion (not a question)
- record the outlet's stance on it
- note if it's attributed to a named person/org

Return JSON:
{{
  "claims": [
    {{
      "text": "atomic claim text",
      "stance": "reports as fact | disputes | alleges | opinion",
      "attributed_to": "name of person/org who said it, or null if outlet's own reporting",
      "supporting_quote": "brief paraphrase of supporting text"
    }}
  ]
}}

If the article contains no checkable claims relevant to the sub-question, return {{"claims": []}}.
"""


def _are_similar(a: str, b: str) -> bool:
    """Simple overlap check to deduplicate near-identical claims."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b) / max(len(words_a), len(words_b))
    return overlap > 0.75


async def _extract_from_page(page: dict, llm) -> list[dict]:
    """Extract claims from one retrieved page."""
    if not page.get("text", "").strip():
        return []

    prompt = EXTRACT_TEMPLATE.format(
        outlet=page.get("outlet", "Unknown"),
        url=page.get("url", ""),
        date=page.get("date", "unknown date"),
        sub_question=page.get("sub_question", ""),
        text=page["text"],
    )

    try:
        result = await llm.fast_call_json(prompt, system_extra=EXTRACT_SYSTEM)
        raw_claims = result.get("claims", [])
        # Attach page metadata to each claim
        for rc in raw_claims:
            rc["_url"] = page.get("url", "")
            rc["_outlet"] = page.get("outlet", "Unknown")
            rc["_lean"] = page.get("lean", "unknown")
            rc["_date"] = page.get("date", "")
        return raw_claims
    except Exception as e:
        logger.warning(f"[S3] Extraction failed for {page.get('url', '?')[:60]}: {e}")
        return []


async def run_extract(state: ResearchState) -> ResearchState:
    """Stage 3: Extract atomic claims from all retrieved pages."""
    logger.info(f"[S3] Extracting claims from {len(state.retrieved_pages)} pages")
    llm = get_llm()

    # Process pages in small batches — 8B model has 60K TPM but
    # each page prompt is ~1K tokens, so batch_size=3 keeps us safe.
    all_raw: list[dict] = []
    pages = state.retrieved_pages
    batch_size = 3  # was 5

    for i in range(0, len(pages), batch_size):
        batch = pages[i : i + batch_size]
        tasks = [_extract_from_page(p, llm) for p in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, list):
                all_raw.extend(r)
            elif isinstance(r, Exception):
                logger.warning(f"[S3] Batch extraction exception: {r}")
        if i + batch_size < len(pages):
            await asyncio.sleep(1.5)  # was 0.5 — gives 8B model breathing room

    # Build Claim objects, deduplicating by text similarity
    claims: list[Claim] = []
    claim_texts: list[str] = []
    claim_counter = 1

    for rc in all_raw:
        text = rc.get("text", "").strip()
        if not text or len(text) < 10:
            continue

        # Deduplicate
        is_dup = any(_are_similar(text, existing) for existing in claim_texts)
        if is_dup:
            # Instead of adding duplicate, find the existing claim and add source
            for existing_claim in claims:
                if _are_similar(text, existing_claim.text):
                    existing_claim.sources.append(
                        ClaimSource(
                            outlet=rc.get("_outlet", "Unknown"),
                            url=rc.get("_url", ""),
                            stance=rc.get("stance", "alleges"),
                            date=rc.get("_date", ""),
                            lean=rc.get("_lean", "unknown"),
                        )
                    )
                    break
            continue

        # New claim
        stance = rc.get("stance", "alleges")
        if stance not in ("reports as fact", "disputes", "alleges", "opinion"):
            stance = "alleges"

        claim = Claim(
            id=f"c{claim_counter}",
            text=text,
            sources=[
                ClaimSource(
                    outlet=rc.get("_outlet", "Unknown"),
                    url=rc.get("_url", ""),
                    stance=stance,
                    date=rc.get("_date", ""),
                    lean=rc.get("_lean", "unknown"),
                )
            ],
            grade="unverified",
            notes=rc.get("supporting_quote", ""),
        )
        claims.append(claim)
        claim_texts.append(text)
        claim_counter += 1

    state.raw_claims = claims
    logger.info(f"[S3] Extracted {len(claims)} unique claims")

    state.events.append({
        "stage": 3,
        "name": "extract",
        "status": "complete",
        "data": {"claim_count": len(claims)},
    })

    state.current_stage = 3
    return state
