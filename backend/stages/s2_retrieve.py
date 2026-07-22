"""
s2_retrieve.py — Stage 2: Parallel Retrieval.
For each sub-question: Tavily search → fetch top pages → structured page objects.
"""
from __future__ import annotations
import asyncio
import logging
import re
from urllib.parse import urlparse

import httpx
from tavily import AsyncTavilyClient

from config import (
    TAVILY_API_KEY,
    TAVILY_MAX_RESULTS,
    TAVILY_SEARCH_DEPTH,
    MAX_PAGE_CHARS,
    OUTLET_LEANS,
)
from models import ResearchState

logger = logging.getLogger(__name__)
tavily = AsyncTavilyClient(api_key=TAVILY_API_KEY)


def _get_lean(url: str) -> str:
    """Look up editorial lean from config map."""
    try:
        domain = urlparse(url).netloc.lower().lstrip("www.")
        for key, lean in OUTLET_LEANS.items():
            if key in domain:
                return lean
    except Exception:
        pass
    return "unknown"


def _outlet_name(url: str) -> str:
    """Extract clean outlet name from URL."""
    try:
        domain = urlparse(url).netloc.lower().lstrip("www.")
        # Remove TLD for display
        parts = domain.split(".")
        return parts[0].title() if parts else domain
    except Exception:
        return url


def _clean_text(text: str) -> str:
    """Normalize whitespace and truncate."""
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_PAGE_CHARS]


async def _search_question(question: str) -> list[dict]:
    """Run Tavily search for one sub-question. Returns list of page dicts."""
    pages = []
    try:
        logger.info(f"[S2] Searching: {question[:80]}")
        result = await tavily.search(
            query=question,
            search_depth=TAVILY_SEARCH_DEPTH,
            max_results=TAVILY_MAX_RESULTS,
            include_answer=False,
            include_raw_content=True,
        )
        for item in result.get("results", []):
            url = item.get("url", "")
            pages.append({
                "url": url,
                "outlet": _outlet_name(url),
                "lean": _get_lean(url),
                "date": item.get("published_date", ""),
                "title": item.get("title", ""),
                "text": _clean_text(
                    item.get("raw_content") or item.get("content", "")
                ),
                "sub_question": question,
            })
    except Exception as e:
        logger.error(f"[S2] Tavily search failed for '{question[:50]}': {e}")
    return pages


async def _disconfirm_search(claim_text: str, original_url: str) -> list[dict]:
    """
    Search specifically for sources that would disagree with a claim.
    Excludes the original outlet domain.
    """
    pages = []
    try:
        domain = urlparse(original_url).netloc.lstrip("www.")
        query = f"{claim_text} -site:{domain} disputed OR denied OR contradicted OR refuted"
        result = await tavily.search(
            query=query,
            search_depth=TAVILY_SEARCH_DEPTH,
            max_results=4,
            include_answer=False,
            include_raw_content=True,
        )
        for item in result.get("results", []):
            url = item.get("url", "")
            pages.append({
                "url": url,
                "outlet": _outlet_name(url),
                "lean": _get_lean(url),
                "date": item.get("published_date", ""),
                "title": item.get("title", ""),
                "text": _clean_text(
                    item.get("raw_content") or item.get("content", "")
                ),
                "sub_question": f"disconfirm: {claim_text[:80]}",
            })
    except Exception as e:
        logger.warning(f"[S2] Disconfirm search failed: {e}")
    return pages


async def run_retrieve(state: ResearchState) -> ResearchState:
    """Stage 2: Search all sub-questions in parallel, collect pages."""
    logger.info(f"[S2] Retrieving for {len(state.sub_questions)} sub-questions")

    tasks = [_search_question(q) for q in state.sub_questions]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_pages = []
    seen_urls: set[str] = set()

    for result in results:
        if isinstance(result, Exception):
            logger.warning(f"[S2] A search task failed: {result}")
            continue
        for page in result:
            url = page.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_pages.append(page)

    state.retrieved_pages = all_pages
    logger.info(f"[S2] Retrieved {len(all_pages)} unique pages")

    state.events.append({
        "stage": 2,
        "name": "retrieve",
        "status": "complete",
        "data": {
            "page_count": len(all_pages),
            "outlets": list({p["outlet"] for p in all_pages}),
        },
    })

    state.current_stage = 2
    return state
