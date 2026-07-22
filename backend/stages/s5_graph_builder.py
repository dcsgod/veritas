"""
s5_graph_builder.py — Stage 5: Entity & Timeline Graph Builder.
Scans graded claims → extracts entities (orgs + public figures) + timeline events.
All edges are claim-sourced. Private individuals are excluded.
"""
from __future__ import annotations
import asyncio
import logging
from datetime import datetime

from models import (
    Claim,
    Entity,
    EntityAffiliation,
    EntityType,
    ImageRef,
    ResearchState,
    TimelineEvent,
)
from llm import get_llm

logger = logging.getLogger(__name__)

ENTITY_SYSTEM = """
Extract only PUBLIC entities: named organizations and named public figures (politicians,
officials, spokespeople, journalists). NEVER include private individuals.
Political affiliation is only noted when it is a matter of documented public record.
Do not infer affiliation from behavior. Do not assign motives.
"""

ENTITY_TEMPLATE = """
From the following list of graded claims, extract all named organizations and
named public figures who appear on the record.

Claims:
{claims_text}

Return JSON:
{{
  "entities": [
    {{
      "name": "full name",
      "type": "organization | public_figure",
      "role": "documented on-record role only (e.g., 'Chief Justice of India', 'President, XYZ NGO')",
      "mentioned_in_claims": ["c1", "c3"],
      "note": "any documented public-record affiliation or context"
    }}
  ],
  "timeline_events": [
    {{
      "date": "YYYY-MM-DD or YYYY-MM or YYYY",
      "event": "what happened, sourced from claims",
      "claim_ids": ["c1", "c2"],
      "disputed": false
    }}
  ]
}}

Notes:
- Do not create entities for unnamed individuals ("protesters", "police officers").
- Only named, verifiable public figures and organizations.
- Timeline events must be traceable to at least one claim ID.
- Mark an event as disputed:true if associated claims have grade "disputed".
"""

IMAGE_SEARCH_TEMPLATE = """
Given this research topic and the claims below, identify up to 5 specific image searches
that would produce VERIFIABLE, attributable images for the report.
Each image should have a clear source (news outlet, government, court records).
Do NOT suggest stock photos or unattributed images.

Topic: {topic}
Key claims: {key_claims}

Return JSON:
{{
  "image_searches": [
    {{
      "description": "what to search for",
      "suggested_query": "search query",
      "expected_source": "outlet name or type"
    }}
  ]
}}
"""


async def _extract_entities_timeline(claims: list[Claim], llm) -> tuple[list[Entity], list[TimelineEvent]]:
    """LLM extraction of entities and timeline from graded claims."""
    claims_text = "\n".join(
        f"[{c.id}] ({c.grade}) {c.text}"
        for c in claims[:40]  # keep prompt reasonable
    )

    prompt = ENTITY_TEMPLATE.format(claims_text=claims_text)

    try:
        result = await llm.fast_call_json(prompt, system_extra=ENTITY_SYSTEM)
    except Exception as e:
        logger.error(f"[S5] Entity/timeline extraction failed: {e}")
        return [], []

    entities: list[Entity] = []
    seen_names: set[str] = set()

    for e in result.get("entities", []):
        name = e.get("name", "").strip()
        if not name or name.lower() in seen_names:
            continue
        seen_names.add(name.lower())

        etype = e.get("type", "organization")
        if etype not in ("organization", "public_figure"):
            etype = "organization"

        affiliations = [
            EntityAffiliation(claim_id=cid, description="")
            for cid in e.get("mentioned_in_claims", [])
        ]

        entities.append(
            Entity(
                name=name,
                type=etype,
                role=e.get("role", ""),
                affiliations=affiliations,
                note=e.get("note", ""),
            )
        )

    timeline: list[TimelineEvent] = []
    for t in result.get("timeline_events", []):
        date = t.get("date", "")
        event_text = t.get("event", "").strip()
        if not date or not event_text:
            continue
        timeline.append(
            TimelineEvent(
                date=date,
                event=event_text,
                claim_ids=t.get("claim_ids", []),
                disputed=t.get("disputed", False),
            )
        )

    # Sort timeline by date
    def _sort_key(te: TimelineEvent) -> str:
        return te.date or "9999"

    timeline.sort(key=_sort_key)

    return entities, timeline


async def run_graph_builder(state: ResearchState) -> ResearchState:
    """Stage 5: Build entity graph + timeline from graded claims."""
    logger.info(f"[S5] Building graph from {len(state.graded_claims)} graded claims")
    llm = get_llm()

    entities, timeline = await _extract_entities_timeline(state.graded_claims, llm)

    state.entities = entities
    state.timeline = timeline

    # Build image references from retrieved pages that have thumbnails/images
    images: list[ImageRef] = []
    seen_img_urls: set[str] = set()
    for page in state.retrieved_pages:
        url = page.get("url", "")
        title = page.get("title", "")
        outlet = page.get("outlet", "Unknown")
        if url and title and url not in seen_img_urls:
            images.append(
                ImageRef(
                    url=url,
                    caption=title,
                    source_url=url,
                    attribution=f"{outlet} — {page.get('date', 'date unknown')}",
                )
            )
            seen_img_urls.add(url)
            if len(images) >= 8:
                break

    state.images = images

    logger.info(
        f"[S5] Entities: {len(entities)}, Timeline events: {len(timeline)}, Images: {len(images)}"
    )

    state.events.append({
        "stage": 5,
        "name": "graph_build",
        "status": "complete",
        "data": {
            "entity_count": len(entities),
            "timeline_count": len(timeline),
            "image_count": len(images),
        },
    })

    state.current_stage = 5
    return state
