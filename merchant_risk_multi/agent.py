"""Multi-agent version of the investigation (Phase 3).

This is ADDED ALONGSIDE the single-agent version — nothing in
merchant_risk_agent/ is modified. We just import its tools and schema.

Instead of one agent that gathers AND judges, we use two specialists run in
order by a SequentialAgent:

    Coordinator (SequentialAgent)
      1. Gatherer  - has the tools, collects evidence, writes it to state
      2. Scorer    - no tools, reads the evidence, returns a validated RiskReport

Two things this version gives us that the single agent could not:
  * The scorer uses `output_schema=RiskReport`, so ADK GUARANTEES the output is
    a valid RiskReport — no manual JSON parsing like server/main.py does.
  * Because an agent with `output_schema` may NOT also use tools, splitting the
    work across two agents is exactly what makes "guaranteed structure + tools"
    possible at the same time.
"""

from __future__ import annotations

import os
import warnings

from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent

import warnings
warnings.filterwarnings("ignore", message=".*SequentialAgent is deprecated.*")

# SequentialAgent is deprecated in ADK 2.x in favour of the new (Alpha) graph
# Workflow API. We keep SequentialAgent on purpose: it is stable, still works,
# and is what current ADK tutorials use, while the graph Workflow cannot yet
# host a tool-looping agent (our gatherer) as a node. Silence just that one
# notice so it doesn't clutter the output.
warnings.filterwarnings("ignore", message=".*SequentialAgent is deprecated.*")

# Reuse the SAME tools and schema as the single-agent version.
from merchant_risk_agent.schemas import RiskReport
from merchant_risk_agent.tools import (
    check_sanctions,
    fetch_website,
    search_adverse_media,
    whois_lookup,
)

load_dotenv()

MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

# The risk vocabulary, written once and dropped into the scorer's instruction.
RISK_TAXONOMY = """
- prohibited_goods: drugs, weapons, counterfeit goods, adult content, illegal
  services, unlicensed pharmaceuticals.
- content_mismatch: the website does not match the stated business (a sign of
  transaction laundering).
- sanctions: the merchant or its owners appear on a sanctions list.
- new_domain: a very recently registered domain.
- adverse_media: public reports of fraud, scams, or regulatory action.
- shell_indicators: no real products, placeholder text, no contact details.
""".strip()


# ---------------------------------------------------------------------------
# 1. The GATHERER — has the tools, ONLY collects evidence (no scoring).
# ---------------------------------------------------------------------------
gatherer = Agent(
    name="evidence_gatherer",
    model=MODEL,
    description="Collects raw risk evidence about a merchant using the tools.",
    instruction="""
You are a merchant risk investigator. Your ONLY job is to GATHER evidence —
do not score, judge, or recommend anything.

Given a merchant name and website:
- Fetch the website to see what the merchant actually sells.
- Screen the merchant name with the sanctions tool.
- Check the domain age with the WHOIS tool.
- Check for adverse media.
Call the tools yourself; never ask the user to run them.

Then write a concise, factual EVIDENCE SUMMARY covering: what the site sells,
any sanctions matches, the domain age, the adverse-media status, and anything
notable. Report gaps honestly (e.g. "adverse media not checked"). Do NOT give a
score or a recommendation — just the facts you found.
""".strip(),
    tools=[fetch_website, check_sanctions, whois_lookup, search_adverse_media],
    # Save this agent's final text into session state under "evidence_summary",
    # so the next agent in the sequence can read it.
    output_key="evidence_summary",
)


# ---------------------------------------------------------------------------
# 2. The SCORER — no tools; turns the evidence into a validated RiskReport.
# ---------------------------------------------------------------------------
# Note the f-string below: {RISK_TAXONOMY} is filled in NOW by Python, while
# {{evidence_summary}} becomes a literal {evidence_summary} in the final string.
# ADK then fills THAT placeholder at runtime from session state — i.e. with the
# gatherer's output. Double braces = "leave this for ADK to substitute later".
scorer = Agent(
    name="risk_scorer",
    model=MODEL,
    description="Turns gathered evidence into a structured risk verdict.",
    instruction=f"""
You are a merchant risk analyst. You are given evidence that has ALREADY been
gathered about a merchant. Do NOT call any tools. Judge using only the evidence
below.

Risk categories to consider:
{RISK_TAXONOMY}

Scoring rules:
- risk_score is 0-100 (0 = clean, 100 = maximum risk).
- risk_level: 0-33 low, 34-66 medium, 67-100 high.
- recommendation: "approve" (low risk, no serious flags), "review" (medium risk
  or anything uncertain — a human decides), or "decline" (a sanctions hit or
  clear prohibited activity).
- When in doubt, prefer "review".
Fill merchant_name and website from the evidence. Every flag must include the
concrete evidence behind it.

EVIDENCE GATHERED:
{{evidence_summary}}
""".strip(),
    # With output_schema set, ADK forces the result into a valid RiskReport.
    # (This is also why the scorer may not have tools — hence the split.)
    output_schema=RiskReport,
    output_key="risk_report",
)


# ---------------------------------------------------------------------------
# 3. The COORDINATOR — runs gatherer, then scorer, sharing state between them.
#    Must be named `root_agent` for `adk web` to discover it.
# ---------------------------------------------------------------------------
root_agent = SequentialAgent(
    name="merchant_risk_pipeline",
    description="Runs the gatherer then the scorer to investigate a merchant.",
    sub_agents=[gatherer, scorer],
)
