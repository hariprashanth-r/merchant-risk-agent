"""Tool: adverse-media screening (a deliberate extension point).

"Adverse media" means negative news: fraud accusations, lawsuits, regulatory
action, scam reports. Screening for it is a real part of risk investigation.

This file ships as a *documented stub* on purpose. A genuine implementation
needs a search capability, and there are two clean ways to add one. Wiring it
up yourself is the first real exercise of the project (see docs/LEARNING_PATH.md):

  Option A - ADK's built-in Google Search tool.
    from google.adk.tools import google_search
    Built-in tools have a constraint in current ADK: an agent that uses
    google_search generally can't also use custom function tools in the same
    agent. The standard pattern is to put google_search in its own sub-agent
    and call it via the "agent-as-a-tool" pattern. That is exactly the
    multi-agent design introduced in Phase 3.

  Option B - a search API you call yourself (Brave Search, SerpAPI, Tavily...).
    Implement the search inside this function, return structured hits, and the
    main agent can keep using it as a normal function tool.

Until you implement one of those, the tool returns a clear "not configured"
result. The agent is instructed to record that as a gap rather than guessing.
"""

from __future__ import annotations


def search_adverse_media(merchant_name: str) -> dict:
    """Search the web for negative news about a merchant (fraud, scams, lawsuits).

    Use this to check whether anyone has publicly reported the merchant for
    fraud, regulatory violations, or scams.

    Args:
        merchant_name: The business name to search for.

    Returns:
        A dict with:
          status: "success", "error", or "not_configured"
          query: the name searched
          hits: list of {title, url, snippet} (empty until you wire up search)
          note: guidance when the tool is not yet configured
    """
    # ---- BEGIN: replace this block with a real implementation (Option A or B) ----
    return {
        "status": "not_configured",
        "query": merchant_name,
        "hits": [],
        "note": "Adverse-media search is not wired up yet. See "
        "merchant_risk_agent/tools/adverse_media.py and docs/LEARNING_PATH.md. "
        "Treat this as 'no adverse media checked', not 'no adverse media found'.",
    }
    # ---- END ----
