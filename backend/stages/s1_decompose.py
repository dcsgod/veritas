"""
s1_decompose.py — Stage 1: Topic Decomposition.
Breaks the user's topic into checkable sub-questions across 6 dimensions.
"""
from __future__ import annotations
import logging
from models import ResearchState
from llm import get_llm

logger = logging.getLogger(__name__)

DECOMPOSE_SYSTEM = """
You are a research analyst breaking a topic into precise, checkable sub-questions.
Do NOT hypothesize about answers. Do NOT assign blame, motive, or interpretation.
Generate only questions — not assertions.
"""

DECOMPOSE_TEMPLATE = """
Topic: {topic}

Break this topic into exactly 6 checkable sub-questions, one per dimension:

(a) Triggering event: What was the specific event, statement, or action that
    started this topic? What was its original wording and context?

(b) Organizations and named public figures: Which organizations and named public
    figures are documented as involved? (On-record only — no inference.)

(c) Escalation sequence: What was the documented sequence of events leading to
    the current state? What changed over time?

(d) Stated demands: What did each named party formally state as their demands
    or position? Quote or paraphrase from on-record statements only.

(e) Counter-claims: What counter-claims or alternative accounts have been made
    by other named parties? Include claims from all sides.

(f) Comparable precedents: What comparable past events in India (if any) are
    documented in public record?

Return a JSON object with this exact structure:
{{
  "sub_questions": [
    {{"dimension": "triggering_event", "question": "..."}},
    {{"dimension": "actors", "question": "..."}},
    {{"dimension": "escalation", "question": "..."}},
    {{"dimension": "demands", "question": "..."}},
    {{"dimension": "counter_claims", "question": "..."}},
    {{"dimension": "precedents", "question": "..."}}
  ]
}}
"""


async def run_decompose(state: ResearchState) -> ResearchState:
    """Stage 1: Decompose topic into sub-questions."""
    logger.info(f"[S1] Decomposing topic: {state.topic}")
    llm = get_llm()

    prompt = DECOMPOSE_TEMPLATE.format(topic=state.topic)

    try:
        result = await llm.fast_call_json(prompt, system_extra=DECOMPOSE_SYSTEM)
        sub_questions = [
            sq["question"] for sq in result.get("sub_questions", [])
        ]
        state.sub_questions = sub_questions
        logger.info(f"[S1] Generated {len(sub_questions)} sub-questions")

        state.events.append({
            "stage": 1,
            "name": "decompose",
            "status": "complete",
            "data": {"sub_questions": sub_questions},
        })

    except Exception as e:
        logger.error(f"[S1] Decomposition failed: {e}")
        state.stage_errors["s1"] = str(e)
        # Fallback: generic sub-questions
        state.sub_questions = [
            f"What was the triggering event for: {state.topic}?",
            f"Which organizations and named figures are involved in: {state.topic}?",
            f"What is the documented escalation sequence for: {state.topic}?",
            f"What are the stated demands of each party in: {state.topic}?",
            f"What counter-claims have been made regarding: {state.topic}?",
            f"What comparable past events in India relate to: {state.topic}?",
        ]

    state.current_stage = 1
    return state
