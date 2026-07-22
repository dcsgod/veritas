"""
main.py — FastAPI application entry point.
Exposes POST /api/research → Server-Sent Events stream.
Each stage completion pushes a JSON event to the frontend.
"""
from __future__ import annotations
import asyncio
import json
import logging
import sys
import os

# Ensure backend directory is on path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from config import CORS_ORIGINS, APP_TITLE, APP_VERSION
from models import ResearchReport, ResearchState
from graph import get_graph

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title=APP_TITLE, version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response schemas ────────────────────────────────────────────────
class ResearchRequest(BaseModel):
    topic: str
    language: str = "en"  # "en" | "hi" | "both"


# ── SSE Helpers ───────────────────────────────────────────────────────────────

def sse_event(event_type: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    payload = json.dumps({"type": event_type, **data})
    return f"data: {payload}\n\n"


STAGE_LABELS = {
    1: "Topic Decomposition",
    2: "Multi-Source Retrieval",
    3: "Claim Extraction",
    4: "Cross-Verification & Grading",
    5: "Entity & Timeline Graph",
    6: "Report Synthesis",
    7: "Hindi Translation",
}


async def stream_research(topic: str, language: str):
    """
    Run the LangGraph pipeline and stream SSE events for each stage.
    Yields SSE-formatted strings.
    """
    graph = get_graph()

    # Initial state
    initial_state = ResearchState(topic=topic).model_dump()

    # Send start event
    yield sse_event("start", {"topic": topic, "total_stages": 7})

    try:
        # Stream through LangGraph nodes
        last_stage = 0

        async for chunk in graph.astream(initial_state, stream_mode="values"):
            # chunk is the full state after each node
            state = ResearchState(**chunk)
            current = state.current_stage

            # Emit any new events that were queued in this stage
            for event in state.events:
                stage_num = event.get("stage", 0)
                if stage_num > last_stage:
                    last_stage = stage_num
                    yield sse_event("stage_complete", {
                        "stage": stage_num,
                        "label": STAGE_LABELS.get(stage_num, f"Stage {stage_num}"),
                        "status": event.get("status", "complete"),
                        "data": event.get("data", {}),
                        "error": event.get("error"),
                    })

                    # Emit partial data after key stages
                    if stage_num == 3:
                        # Claims extracted
                        yield sse_event("partial_claims", {
                            "claims": [c.model_dump() for c in state.raw_claims[:10]],
                            "total": len(state.raw_claims),
                        })

                    elif stage_num == 4:
                        # Claims graded
                        yield sse_event("partial_claims_graded", {
                            "claims": [c.model_dump() for c in state.graded_claims],
                        })

                    elif stage_num == 5:
                        # Graph built
                        yield sse_event("partial_graph", {
                            "entities": [e.model_dump() for e in state.entities],
                            "timeline": [t.model_dump() for t in state.timeline],
                            "images": [i.model_dump() for i in state.images],
                        })

        # Final state — emit complete report
        final_state = ResearchState(**chunk)

        synthesis = final_state.translations.get("_synthesis", {})
        report = ResearchReport(
            topic=final_state.topic,
            claims=final_state.graded_claims,
            entities=final_state.entities,
            timeline=final_state.timeline,
            images=final_state.images,
            verdict=final_state.verdict,
            translations=final_state.translations,
            sub_questions=final_state.sub_questions,
        )

        yield sse_event("report_complete", {
            "report": report.model_dump(),
            "synthesis": synthesis,
            "errors": final_state.stage_errors,
        })

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        yield sse_event("error", {"message": str(e), "topic": topic})

    yield sse_event("done", {})


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/api/research")
async def research_endpoint(request: ResearchRequest):
    """
    POST /api/research
    Body: {"topic": "CJP protest in Delhi", "language": "hi"}
    Returns: Server-Sent Events stream
    """
    topic = request.topic.strip()
    if not topic:
        raise HTTPException(status_code=400, detail="topic is required")
    if len(topic) > 500:
        raise HTTPException(status_code=400, detail="topic too long (max 500 chars)")

    logger.info(f"Research request: '{topic}' lang={request.language}")

    return StreamingResponse(
        stream_research(topic, request.language),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "title": APP_TITLE,
    }


@app.get("/")
async def root():
    return {"message": f"{APP_TITLE} v{APP_VERSION} — POST /api/research to begin"}
