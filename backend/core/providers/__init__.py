"""
Eraya provider facades - the agentic-AI integration layer.

Every module here follows the same rule as the 3-tier cascade: optional, lazy,
and graceful. A missing package or API key never raises into the request path;
the caller simply falls back to deterministic behaviour.

    from core.providers import llm, risk, memory, ingestion, orchestration, assets

    plan = llm.complete_json(system, user)        # Groq -> Kimi -> Featherless
    md   = ingestion.fetch_markdown(url)          # Firecrawl -> ZenRows -> BrightData
    orchestration.notify("guardian.veto", {...})  # n8n webhook
"""
from . import config  # noqa: F401

__all__ = ["config", "llm", "risk", "memory", "ingestion", "orchestration", "assets", "status"]


def status() -> dict:
    """Which providers are currently configured (key present)."""
    from . import llm
    keys = [
        "GROQ_API_KEY", "KIMI_API_KEY", "FEATHERLESS_API_KEY", "SARVAM_API_KEY",
        "HF_TOKEN", "TABPFN_API_KEY", "PINECONE_API_KEY", "CYBORGDB_API_KEY",
        "FIRECRAWL_API_KEY", "BRIGHTDATA_API_KEY", "ZENROWS_API_KEY", "TINYFISH_API_KEY",
        "N8N_WEBHOOK_URL", "ZERVE_API_KEY", "STITCH_API_KEY", "PEXELS_API_KEY",
    ]
    return {
        "llm_chain": llm.available(),
        "configured": [k for k in keys if config.get(k)],
    }
