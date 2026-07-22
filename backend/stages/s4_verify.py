"""
s4_verify.py — Stage 4: Cross-Verification & Grading.
For each claim: search for disconfirming sources → grade with LLM.
Grade logic (strict):
  - confirmed: ≥2 independent outlets from DIFFERENT lean brackets agree
  - disputed: outlets disagree
  - unverified: single source or no corroboration found
  - opinion: source itself frames it as interpretation
"""
from __future__ import annotations
import asyncio
import logging
from urllib.parse import urlparse

from models import Claim, ClaimSource, ResearchState
from stages.s2_retrieve import _disconfirm_search, _outlet_name, _get_lean
from llm import get_llm

logger = logging.getLogger(__name__)

VERIFY_SYSTEM = """
You are a strict claim grader. You apply these grades:
- confirmed: 2 or more INDEPENDENT sources from DIFFERENT editorial leans report this as fact.
  "Different leans" means at least one left/centre-left AND one right/centre-right, 
  OR at least two international/neutral outlets. Multiple outlets of the same lean do NOT confirm.
- disputed: Sources explicitly contradict each other about this claim.
- unverified: Only one source, or only same-lean sources, or no corroboration found.
- opinion: The source itself labels this as editorial, analysis, or personal view — not reporting.

Rules:
- Never upgrade a grade based on how many same-lean outlets repeat it.
- Absence of disconfirming sources ≠ confirmation. State this explicitly when relevant.
- Political affiliation is only noted if a source documents it on record.
"""

VERIFY_TEMPLATE = """
Claim to grade: "{claim_text}"

Primary sources reporting this claim:
{primary_sources}

Disconfirming / alternative sources found:
{disconfirm_sources}

Disconfirm search was run: {disconfirm_searched}
Disconfirming sources found: {disconfirm_found}

Apply the grading rules and return JSON:
{{
  "grade": "confirmed | disputed | unverified | opinion",
  "notes": "explain the grade in 1-2 sentences. If no disconfirming sources found, say so explicitly.",
  "disconfirm_found": true | false
}}
"""


def _leans_are_diverse(sources: list[ClaimSource]) -> bool:
    """Check if sources span at least two different lean brackets."""
    left_set = {"left", "centre-left"}
    right_set = {"right", "centre-right"}
    intl_set = {"international"}
    neutral_set = {"centre"}

    leans = {s.lean for s in sources if s.lean}

    has_left = bool(leans & left_set)
    has_right = bool(leans & right_set)
    has_intl = bool(leans & intl_set)
    has_neutral = bool(leans & neutral_set)

    # Diverse = left + right, OR left/right + neutral, OR 2+ internationals
    if has_left and has_right:
        return True
    if (has_left or has_right) and has_neutral:
        return True
    if has_intl and len([l for l in leans if l in intl_set]) >= 2:
        return True
    if has_intl and (has_left or has_right or has_neutral):
        return True
    return False


def _format_sources(sources: list[ClaimSource]) -> str:
    if not sources:
        return "None"
    lines = []
    for s in sources:
        lines.append(
            f"- {s.outlet} (lean: {s.lean or 'unknown'}, stance: {s.stance}, date: {s.date or 'unknown'})"
        )
    return "\n".join(lines)


async def _grade_claim(claim: Claim, llm) -> Claim:
    """Run disconfirm search + LLM grading for one claim."""
    # Fast path: opinion claims (source already flags it)
    if any(s.stance == "opinion" for s in claim.sources):
        claim.grade = "opinion"
        claim.notes = "Source(s) frame this as editorial opinion, not reporting."
        claim.disconfirm_searched = False
        return claim

    # Run disconfirm search
    disconfirm_pages = []
    if claim.sources:
        primary_url = claim.sources[0].url
        disconfirm_pages = await _disconfirm_search(claim.text, primary_url)
    claim.disconfirm_searched = True

    # Add disconfirming sources to claim
    disconfirm_sources: list[ClaimSource] = []
    seen_urls = {s.url for s in claim.sources}
    for page in disconfirm_pages:
        url = page.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            ds = ClaimSource(
                outlet=page.get("outlet", "Unknown"),
                url=url,
                stance="disputes",
                date=page.get("date", ""),
                lean=page.get("lean", "unknown"),
            )
            disconfirm_sources.append(ds)

    claim.disconfirm_found = len(disconfirm_sources) > 0

    # Quick rule-based grading before LLM call
    all_sources = claim.sources + disconfirm_sources
    fact_sources = [s for s in claim.sources if s.stance == "reports as fact"]
    dispute_sources = [s for s in all_sources if s.stance == "disputes"]

    # Quick grade: disputed if explicit contradictions found
    if dispute_sources and fact_sources:
        # Let LLM decide nuance
        pass
    elif len(fact_sources) >= 2 and _leans_are_diverse(fact_sources):
        claim.grade = "confirmed"
        claim.notes = (
            f"Reported as fact by {len(fact_sources)} sources across diverse editorial leans."
        )
        if not claim.disconfirm_found:
            claim.notes += " No disconfirming sources found (absence ≠ confirmation)."
        claim.sources.extend(disconfirm_sources)
        return claim

    # LLM grading for nuanced cases
    prompt = VERIFY_TEMPLATE.format(
        claim_text=claim.text,
        primary_sources=_format_sources(claim.sources),
        disconfirm_sources=_format_sources(disconfirm_sources),
        disconfirm_searched=claim.disconfirm_searched,
        disconfirm_found=claim.disconfirm_found,
    )

    try:
        result = await llm.fast_call_json(prompt, system_extra=VERIFY_SYSTEM)
        grade = result.get("grade", "unverified")
        if grade not in ("confirmed", "disputed", "unverified", "opinion"):
            grade = "unverified"
        claim.grade = grade
        claim.notes = result.get("notes", "")
        claim.disconfirm_found = result.get("disconfirm_found", claim.disconfirm_found)
    except Exception as e:
        logger.warning(f"[S4] Grading LLM call failed for claim {claim.id}: {e}")
        claim.grade = "unverified"
        claim.notes = "Grading failed; defaulting to unverified."

    claim.sources.extend(disconfirm_sources)
    return claim


async def run_verify(state: ResearchState) -> ResearchState:
    """Stage 4: Cross-verify and grade all extracted claims."""
    logger.info(f"[S4] Verifying {len(state.raw_claims)} claims")
    llm = get_llm()

    # batch_size=2: each verify call also fires a disconfirm Tavily search,
    # so 2 parallel is enough to keep network + LLM busy without 429s.
    claims = state.raw_claims
    graded: list[Claim] = []
    batch_size = 2  # was 4

    for i in range(0, len(claims), batch_size):
        batch = claims[i : i + batch_size]
        tasks = [_grade_claim(c, llm) for c in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for j, r in enumerate(results):
            if isinstance(r, Claim):
                graded.append(r)
            else:
                logger.warning(f"[S4] Claim grading exception: {r}")
                batch[j].grade = "unverified"
                batch[j].notes = f"Verification error: {r}"
                graded.append(batch[j])
        if i + batch_size < len(claims):
            await asyncio.sleep(2.0)  # was 0.5

    state.graded_claims = graded

    grade_counts = {}
    for c in graded:
        grade_counts[c.grade] = grade_counts.get(c.grade, 0) + 1
    logger.info(f"[S4] Grade distribution: {grade_counts}")

    state.events.append({
        "stage": 4,
        "name": "verify",
        "status": "complete",
        "data": {"grade_distribution": grade_counts, "total": len(graded)},
    })

    state.current_stage = 4
    return state
