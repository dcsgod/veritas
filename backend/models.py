"""
models.py — Pydantic data models for the Veritas research pipeline.
All fields match the spec's data model exactly.
"""
from __future__ import annotations
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ── Grade Literal ────────────────────────────────────────────────────────────
Grade = Literal["confirmed", "disputed", "unverified", "opinion"]
Stance = Literal["reports as fact", "disputes", "alleges", "opinion"]
EntityType = Literal["organization", "public_figure"]


# ── Source attribution for a single claim ───────────────────────────────────
class ClaimSource(BaseModel):
    outlet: str = Field(..., description="Name of the publication or outlet")
    url: str = Field(..., description="Direct URL to the article/page")
    stance: Stance = Field(..., description="How the outlet frames this claim")
    date: Optional[str] = Field(None, description="Publication date ISO 8601")
    lean: Optional[str] = Field(None, description="Editorial lean (auto-tagged)")


# ── Atomic claim ─────────────────────────────────────────────────────────────
class Claim(BaseModel):
    id: str = Field(..., description="Unique claim identifier e.g. c1")
    text: str = Field(..., description="Atomic factual claim, no interpretation")
    sources: list[ClaimSource] = Field(default_factory=list)
    grade: Grade = Field("unverified")
    notes: str = Field("", description="Why this grade was assigned")
    disconfirm_searched: bool = Field(
        False, description="Whether a disconfirm search was performed"
    )
    disconfirm_found: bool = Field(
        False, description="Whether disconfirming sources were found"
    )


# ── Entity (org or public figure only — never private citizens) ──────────────
class EntityAffiliation(BaseModel):
    claim_id: str
    description: str = ""


class Entity(BaseModel):
    name: str
    type: EntityType
    role: str = Field("", description="On-record role only")
    affiliations: list[EntityAffiliation] = Field(default_factory=list)
    note: str = Field("", description="Context note — no private citizens ever included")


# ── Timeline event ───────────────────────────────────────────────────────────
class TimelineEvent(BaseModel):
    date: str = Field(..., description="ISO 8601 date or partial date")
    event: str = Field(..., description="What happened, sourced from claims")
    claim_ids: list[str] = Field(default_factory=list)
    disputed: bool = False


# ── Image reference with attribution ────────────────────────────────────────
class ImageRef(BaseModel):
    url: str
    caption: str
    source_url: str
    attribution: str


# ── Verdict ──────────────────────────────────────────────────────────────────
class Verdict(BaseModel):
    confirmed_facts: list[str] = Field(default_factory=list, description="Claim IDs")
    disputed_points: list[str] = Field(default_factory=list, description="Claim IDs")
    unverifiable_claims: list[str] = Field(
        default_factory=list, description="Claim IDs"
    )
    opinion_claims: list[str] = Field(default_factory=list, description="Claim IDs")
    summary: str = Field(
        "",
        description=(
            "What is established vs contested — "
            "no judgment on legitimacy of the cause itself"
        ),
    )
    disconfirm_gaps: list[str] = Field(
        default_factory=list,
        description="Claims where disconfirming sources were searched but not found",
    )


# ── Full research report ──────────────────────────────────────────────────────
class ResearchReport(BaseModel):
    topic: str
    claims: list[Claim] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    images: list[ImageRef] = Field(default_factory=list)
    verdict: Optional[Verdict] = None
    translations: dict[str, Any] = Field(default_factory=dict)
    sub_questions: list[str] = Field(default_factory=list)
    generated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )


# ── LangGraph Pipeline State ──────────────────────────────────────────────────
class ResearchState(BaseModel):
    """Mutable state object threaded through all LangGraph nodes."""

    topic: str = ""
    sub_questions: list[str] = Field(default_factory=list)

    # Raw retrieved pages: list of {url, outlet, date, text, sub_question}
    retrieved_pages: list[dict] = Field(default_factory=list)

    # Extracted claims (before grading)
    raw_claims: list[Claim] = Field(default_factory=list)

    # Graded claims (after Stage 4)
    graded_claims: list[Claim] = Field(default_factory=list)

    # Graph data
    entities: list[Entity] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    images: list[ImageRef] = Field(default_factory=list)

    # Final outputs
    verdict: Optional[Verdict] = None
    translations: dict[str, Any] = Field(default_factory=dict)

    # Stage tracking
    current_stage: int = 0
    stage_errors: dict[str, str] = Field(default_factory=dict)

    # SSE event queue (stage name → payload)
    events: list[dict] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
