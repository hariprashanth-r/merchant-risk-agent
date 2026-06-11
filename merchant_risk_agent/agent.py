"""The Merchant Risk Investigation Agent.

This is the core of the project. An ADK agent is mostly three things:

  1. a model        - which Gemini model does the reasoning
  2. an instruction - the persona + the policy it follows (this is your prompt)
  3. tools          - the plain Python functions it is allowed to call

ADK runs the loop for you: the model reads the request, decides which tool to
call, reads the tool's result, decides what to do next, and eventually answers.
You never write that loop by hand.

The variable MUST be named `root_agent` so that `adk web` and `adk run` can
discover it.
"""

from __future__ import annotations

import os

from google.adk.agents import Agent

from .schemas import output_format_instructions
from .tools import (
    check_sanctions,
    fetch_website,
    search_adverse_media,
    whois_lookup,
)

# Pick the model from the environment so you can swap it without touching code.
# "gemini-2.5-flash" is fast and cheap and good enough to learn with.
MODEL = os.environ.get("MODEL", "gemini-2.5-flash")

# The instruction is the single most important thing you will tune in this
# project. It defines the analyst's job, the risk taxonomy it applies, how it
# should use its tools, and the exact shape of its final answer.
INSTRUCTION = f"""
You are a merchant risk analyst. Given a merchant's name and website, you
investigate whether it is safe to onboard them to a payments platform, and you
produce a structured risk report.

HOW TO WORK
- Always start by fetching the website to see what the merchant actually sells.
- Screen the merchant's name with the sanctions tool. A confident match is a
  hard stop: recommend "decline".
- Check the domain age with the WHOIS tool. A domain younger than ~90 days on a
  business that presents itself as established is a real risk signal.
- Check for adverse media (negative news, fraud reports, lawsuits).
- Call tools yourself; never ask the user to run them. If a tool returns an
  error or "not_configured", note the gap rather than guessing the answer.

WHAT TO LOOK FOR (risk taxonomy)
- prohibited_goods: drugs, weapons, counterfeit goods, adult content, illegal
  services, unlicensed pharmaceuticals, etc.
- content_mismatch: the website does not match the stated business (a classic
  sign of transaction laundering, where a clean storefront fronts for something
  else).
- sanctions: the merchant or its owners appear on a sanctions list.
- new_domain: a very recently registered domain.
- adverse_media: public reports of fraud, scams, or regulatory action.
- shell_indicators: no real products, placeholder text, no contact details.

HOW TO SCORE
- risk_score is 0-100 (0 = clean, 100 = maximum risk).
- Map to risk_level: 0-33 low, 34-66 medium, 67-100 high.
- Map to a recommendation:
    approve  - low risk, no serious flags.
    review   - medium risk, or anything you are unsure about. A human decides.
    decline  - sanctions hit or clear prohibited activity.
- When in doubt, prefer "review". The agent does not make irreversible calls
  on its own; a human always signs off on borderline cases.

{output_format_instructions()}
""".strip()


root_agent = Agent(
    name="merchant_risk_agent",
    model=MODEL,
    description="Investigates a merchant for onboarding risk and returns a "
    "structured verdict.",
    instruction=INSTRUCTION,
    tools=[
        fetch_website,
        check_sanctions,
        whois_lookup,
        search_adverse_media,
    ],
)
