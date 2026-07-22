"""
s6_synthesize.py — Stage 6: Report Synthesis.
Synthesizes the structured report from graded claims only.
No new claims are introduced. No motive inference. Verdict summarizes evidence state.
"""
from __future__ import annotations
import logging

from models import Claim, ResearchState, Verdict
from llm import get_llm

logger = logging.getLogger(__name__)

SYNTHESIS_SYSTEM = """
You are synthesizing a research report from pre-graded, pre-verified claims.
Hard rules:
1. Use ONLY the provided graded claims. Do NOT add new claims or facts.
2. State each claim's grade explicitly (confirmed / disputed / unverified / opinion).
3. Do NOT render a verdict on whether any movement's cause is valid or just.
4. Do NOT use motive-inference language.
5. When a pattern is evidenced in the claims (e.g., repeated uncorrected distortions),
   attribute that pattern to what the sourced claims show — do not assert it as your own conclusion.
6. If no disconfirming sources were found for a claim, state that explicitly.
7. The verdict summarizes what is established vs. contested — nothing more.
"""

SYNTHESIS_TEMPLATE = """
Topic: {topic}

Graded Claims ({claim_count} total):
{claims_section}

Entity Summary:
{entity_summary}

Timeline Summary:
{timeline_summary}

Write a structured research report. Return JSON:
{{
  "executive_summary": "2-3 sentence overview of what is documented vs contested",
  "section_origin": "What triggered this topic — only confirmed/unverified/disputed claims",
  "section_actors": "Documented organizations and public figures, on-record roles only",
  "section_escalation": "Documented sequence of events with claim grades",
  "section_demands": "Stated demands from each named party",
  "section_counter_narratives": "Alternative accounts from named parties",
  "section_precedents": "Comparable past events if evidenced in claims",
  "verdict": {{
    "confirmed_facts": ["claim IDs where grade=confirmed"],
    "disputed_points": ["claim IDs where grade=disputed"],
    "unverifiable_claims": ["claim IDs where grade=unverified"],
    "opinion_claims": ["claim IDs where grade=opinion"],
    "disconfirm_gaps": ["claim IDs where disconfirm was searched but nothing found"],
    "summary": "1-2 paragraphs: what is established, what is contested, what remains unverifiable. No judgment on cause legitimacy."
  }}
}}
"""


def _format_claims_for_synthesis(claims: list[Claim]) -> str:
    lines = []
    for c in claims:
        source_str = "; ".join(
            f"{s.outlet} ({s.stance})" for s in c.sources[:3]
        )
        disconfirm_note = ""
        if c.disconfirm_searched and not c.disconfirm_found:
            disconfirm_note = " [Disconfirm searched: no opposing sources found]"
        lines.append(
            f"[{c.id}] GRADE:{c.grade.upper()} | {c.text}\n"
            f"   Sources: {source_str}{disconfirm_note}\n"
            f"   Notes: {c.notes}"
        )
    return "\n\n".join(lines)


def _format_entities(entities) -> str:
    if not entities:
        return "No named entities extracted."
    return "\n".join(
        f"- {e.name} ({e.type}): {e.role}" for e in entities
    )


def _format_timeline(timeline) -> str:
    if not timeline:
        return "No timeline events extracted."
    return "\n".join(
        f"- {t.date}: {t.event} [{'DISPUTED' if t.disputed else 'reported'}] (claims: {', '.join(t.claim_ids)})"
        for t in timeline
    )


async def run_synthesize(state: ResearchState) -> ResearchState:
    """Stage 6: Synthesize the full structured report from graded claims."""
    logger.info(f"[S6] Synthesizing report from {len(state.graded_claims)} graded claims")
    llm = get_llm()

    claims_section = _format_claims_for_synthesis(state.graded_claims)
    entity_summary = _format_entities(state.entities)
    timeline_summary = _format_timeline(state.timeline)

    prompt = SYNTHESIS_TEMPLATE.format(
        topic=state.topic,
        claim_count=len(state.graded_claims),
        claims_section=claims_section,
        entity_summary=entity_summary,
        timeline_summary=timeline_summary,
    )

    try:
        result = await llm.call_json(prompt, system_extra=SYNTHESIS_SYSTEM)

        # Build Verdict object from synthesis result
        v = result.get("verdict", {})
        verdict = Verdict(
            confirmed_facts=v.get("confirmed_facts", []),
            disputed_points=v.get("disputed_points", []),
            unverifiable_claims=v.get("unverifiable_claims", []),
            opinion_claims=v.get("opinion_claims", []),
            disconfirm_gaps=v.get("disconfirm_gaps", []),
            summary=v.get("summary", ""),
        )

        # Also auto-build verdict from graded claims as cross-check
        for c in state.graded_claims:
            cid = c.id
            if c.grade == "confirmed" and cid not in verdict.confirmed_facts:
                verdict.confirmed_facts.append(cid)
            elif c.grade == "disputed" and cid not in verdict.disputed_points:
                verdict.disputed_points.append(cid)
            elif c.grade == "unverified" and cid not in verdict.unverifiable_claims:
                verdict.unverifiable_claims.append(cid)
            elif c.grade == "opinion" and cid not in verdict.opinion_claims:
                verdict.opinion_claims.append(cid)
            if c.disconfirm_searched and not c.disconfirm_found:
                if cid not in verdict.disconfirm_gaps:
                    verdict.disconfirm_gaps.append(cid)

        state.verdict = verdict

        # Store synthesis sections in translations as base (English)
        state.translations["_synthesis"] = {
            "executive_summary": result.get("executive_summary", ""),
            "section_origin": result.get("section_origin", ""),
            "section_actors": result.get("section_actors", ""),
            "section_escalation": result.get("section_escalation", ""),
            "section_demands": result.get("section_demands", ""),
            "section_counter_narratives": result.get("section_counter_narratives", ""),
            "section_precedents": result.get("section_precedents", ""),
        }

        # Guardrail check on verdict summary
        violations = llm.check_guardrails(verdict.summary)
        if violations:
            logger.warning(f"[S6] Guardrail violations in synthesis: {violations}")
            verdict.summary += (
                f"\n\n[Note: Some flagged inference language detected. "
                f"Terms: {', '.join(violations)}. Manual review recommended.]"
            )

    except Exception as e:
        logger.error(f"[S6] Synthesis failed: {e}")
        state.stage_errors["s6"] = str(e)
        # Build verdict from graded claims as fallback
        verdict = Verdict()
        for c in state.graded_claims:
            if c.grade == "confirmed":
                verdict.confirmed_facts.append(c.id)
            elif c.grade == "disputed":
                verdict.disputed_points.append(c.id)
            elif c.grade == "unverified":
                verdict.unverifiable_claims.append(c.id)
            elif c.grade == "opinion":
                verdict.opinion_claims.append(c.id)
        verdict.summary = "Synthesis failed. Verdict built directly from graded claims."
        state.verdict = verdict

    state.events.append({
        "stage": 6,
        "name": "synthesize",
        "status": "complete",
        "data": {
            "confirmed": len(state.verdict.confirmed_facts),
            "disputed": len(state.verdict.disputed_points),
            "unverified": len(state.verdict.unverifiable_claims),
            "opinion": len(state.verdict.opinion_claims),
        },
    })

    state.current_stage = 6
    return state
