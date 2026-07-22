"""
config.py — Veritas configuration: models, API settings, guardrails.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── LLM Models ──────────────────────────────────────────────────────────────
# Big model: only for synthesis (Stage 6) — costs more TPM
PRIMARY_MODEL = "llama-3.3-70b-versatile"    # Groq — 12,000 TPM free
# Fast model: extraction, verification, graph, translate — 5x higher TPM
FAST_MODEL    = "llama-3.1-8b-instant"        # Groq — 60,000 TPM free
FALLBACK_MODEL = "gemini-2.0-flash"           # Google fallback
FALLBACK_MODEL_LITE = "gemini-2.0-flash-lite" # Google lite fallback (higher quota)

LLM_TEMPERATURE = 0.1                         # Low temp → deterministic extraction
LLM_MAX_TOKENS  = 4096                        # Reduced from 8192 — saves TPM

# ── Rate Limit Controls ──────────────────────────────────────────────────────
EXTRACT_BATCH_SIZE = 3   # Stage 3: pages processed in parallel (was 5)
VERIFY_BATCH_SIZE  = 2   # Stage 4: claims verified in parallel (was 4)
BATCH_SLEEP_SECS   = 1.5 # Pause between batches (was 0.5)

# ── Retrieval ────────────────────────────────────────────────────────────────
TAVILY_MAX_RESULTS = 6          # per sub-question
TAVILY_SEARCH_DEPTH = "advanced"
PLAYWRIGHT_TIMEOUT_MS = 20000
MAX_PAGE_CHARS = 8000           # truncate very long pages before LLM call

# ── Grade Values (canonical) ─────────────────────────────────────────────────
GRADE_CONFIRMED = "confirmed"
GRADE_DISPUTED = "disputed"
GRADE_UNVERIFIED = "unverified"
GRADE_OPINION = "opinion"

# ── Guardrail: Forbidden Inference Terms ─────────────────────────────────────
# Any LLM output containing these in a non-quoted/attributed context is flagged.
FORBIDDEN_INFERENCE_TERMS = [
    "politically motivated",
    "secretly wants",
    "brand-building",
    "ambition drives",
    "hidden agenda",
    "deliberately fabricated",
    "orchestrated by",
    "propaganda campaign",  # only OK if attributed to a named source's claim
    "provocateur",
    "false flag",
]

# ── Ideological Lean Tags (for multi-outlet triangulation) ───────────────────
# Used to validate that "confirmed" claims come from cross-lean corroboration.
OUTLET_LEANS = {
    "thehindu.com": "centre-left",
    "thewire.in": "left",
    "ndtv.com": "centre",
    "indiatoday.in": "centre",
    "theprint.in": "centre",
    "opindia.com": "right",
    "swarajyamag.com": "right",
    "scroll.in": "left",
    "telegraphindia.com": "centre-left",
    "firstpost.com": "centre-right",
    "hindustantimes.com": "centre",
    "timesofindia.com": "centre",
    "livemint.com": "centre",
    "businessstandard.com": "centre",
    "news18.com": "centre-right",
    "zeenews.india.com": "right",
    "bbc.com": "international",
    "reuters.com": "international",
    "apnews.com": "international",
    "aljazeera.com": "international",
}

# ── App ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"]
APP_TITLE = "Veritas — Claim Verification Engine"
APP_VERSION = "1.0.0"
