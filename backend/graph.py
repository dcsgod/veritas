"""
graph.py — LangGraph StateGraph wiring all 7 Veritas pipeline stages.
Each node is a stage. State flows through sequentially.
Stage failures produce partial reports (not crashes).
"""
from __future__ import annotations
import logging
from typing import Any

from langgraph.graph import StateGraph, END

from models import ResearchState
from stages.s1_decompose import run_decompose
from stages.s2_retrieve import run_retrieve
from stages.s3_extract import run_extract
from stages.s4_verify import run_verify
from stages.s5_graph_builder import run_graph_builder
from stages.s6_synthesize import run_synthesize
from stages.s7_translate import run_translate

logger = logging.getLogger(__name__)


# ── Safe wrappers (catch exceptions, allow pipeline to continue) ─────────────

async def node_decompose(state: dict) -> dict:
    s = ResearchState(**state)
    s = await run_decompose(s)
    return s.model_dump()


async def node_retrieve(state: dict) -> dict:
    s = ResearchState(**state)
    try:
        s = await run_retrieve(s)
    except Exception as e:
        logger.error(f"[Graph] Stage 2 failed: {e}")
        s.stage_errors["s2"] = str(e)
        s.events.append({"stage": 2, "name": "retrieve", "status": "error", "error": str(e)})
    return s.model_dump()


async def node_extract(state: dict) -> dict:
    s = ResearchState(**state)
    try:
        s = await run_extract(s)
    except Exception as e:
        logger.error(f"[Graph] Stage 3 failed: {e}")
        s.stage_errors["s3"] = str(e)
        s.events.append({"stage": 3, "name": "extract", "status": "error", "error": str(e)})
    return s.model_dump()


async def node_verify(state: dict) -> dict:
    s = ResearchState(**state)
    try:
        s = await run_verify(s)
    except Exception as e:
        logger.error(f"[Graph] Stage 4 failed: {e}")
        s.stage_errors["s4"] = str(e)
        s.graded_claims = s.raw_claims  # pass ungraded claims forward
        s.events.append({"stage": 4, "name": "verify", "status": "error", "error": str(e)})
    return s.model_dump()


async def node_graph_build(state: dict) -> dict:
    s = ResearchState(**state)
    try:
        s = await run_graph_builder(s)
    except Exception as e:
        logger.error(f"[Graph] Stage 5 failed: {e}")
        s.stage_errors["s5"] = str(e)
        s.events.append({"stage": 5, "name": "graph_build", "status": "error", "error": str(e)})
    return s.model_dump()


async def node_synthesize(state: dict) -> dict:
    s = ResearchState(**state)
    try:
        s = await run_synthesize(s)
    except Exception as e:
        logger.error(f"[Graph] Stage 6 failed: {e}")
        s.stage_errors["s6"] = str(e)
        s.events.append({"stage": 6, "name": "synthesize", "status": "error", "error": str(e)})
    return s.model_dump()


async def node_translate(state: dict) -> dict:
    s = ResearchState(**state)
    try:
        s = await run_translate(s)
    except Exception as e:
        logger.error(f"[Graph] Stage 7 failed: {e}")
        s.stage_errors["s7"] = str(e)
        s.events.append({"stage": 7, "name": "translate", "status": "error", "error": str(e)})
    return s.model_dump()


# ── Build the graph ───────────────────────────────────────────────────────────

def build_veritas_graph():
    """Construct and compile the LangGraph pipeline."""
    builder = StateGraph(dict)  # state is plain dict (Pydantic serialized)

    builder.add_node("decompose", node_decompose)
    builder.add_node("retrieve", node_retrieve)
    builder.add_node("extract", node_extract)
    builder.add_node("verify", node_verify)
    builder.add_node("graph_build", node_graph_build)
    builder.add_node("synthesize", node_synthesize)
    builder.add_node("translate", node_translate)

    builder.set_entry_point("decompose")
    builder.add_edge("decompose", "retrieve")
    builder.add_edge("retrieve", "extract")
    builder.add_edge("extract", "verify")
    builder.add_edge("verify", "graph_build")
    builder.add_edge("graph_build", "synthesize")
    builder.add_edge("synthesize", "translate")
    builder.add_edge("translate", END)

    return builder.compile()


# Singleton compiled graph
_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_veritas_graph()
    return _graph
