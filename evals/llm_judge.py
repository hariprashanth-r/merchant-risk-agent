"""LLM-as-judge — Layer 4 evaluation.

The score and recommendation can be checked against labels (see run_eval.py),
but the report's free-text `summary` and each flag's `evidence` cannot — there's
no single "correct" wording. So we grade them with another model: a JUDGE agent
that reads the gathered evidence and the produced report and decides whether
every claim in the report is actually supported by the evidence.

This is how you catch the most dangerous failure in compliance — the agent
inventing a fact ("the owner was convicted of fraud") that no tool ever found.

The judge itself is just an Agent with an output_schema, exactly like the scorer
in the multi-agent pipeline. It has no tools; it only reasons.

Run:  python -m evals.llm_judge      (needs GOOGLE_API_KEY)
"""

from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

from google.adk.agents import Agent


class JudgeVerdict(BaseModel):
    """The judge's structured assessment of one report."""

    faithful: bool = Field(
        description="True only if EVERY factual claim in the report is supported "
        "by the evidence."
    )
    faithfulness_score: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of the report's claims that are supported by the "
        "evidence (1.0 = all supported).",
    )
    hallucinations: list[str] = Field(
        default_factory=list,
        description="Each specific claim in the report that the evidence does "
        "NOT support.",
    )
    reasoning: str = Field(description="A brief explanation of the assessment.")


# The judge agent. No tools — it only compares two texts and returns a verdict.
judge_agent = Agent(
    name="faithfulness_judge",
    model=os.environ.get("JUDGE_MODEL", "gemini-2.5-flash"),
    description="Judges whether a risk report is supported by the gathered evidence.",
    instruction="""
You are a strict evaluator of an AI-generated merchant risk report. You are given
the EVIDENCE that was gathered and the REPORT the agent produced.

Decide whether every factual claim in the report's summary and flags is supported
by the evidence:
- faithful: true ONLY if no claim is unsupported.
- faithfulness_score: the fraction of the report's claims supported by the
  evidence (1.0 means all supported).
- hallucinations: list each specific claim in the report that the evidence does
  NOT support.
- reasoning: explain briefly.

Be strict. If the report asserts a fact that the evidence does not contain, that
is a hallucination even if it sounds plausible. Reasonable summarisation of facts
that ARE present is fine.
""".strip(),
    output_schema=JudgeVerdict,
)


async def judge(evidence: str, report_json: str) -> JudgeVerdict:
    """Run the judge agent on one (evidence, report) pair."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    ss = InMemorySessionService()
    runner = Runner(agent=judge_agent, app_name="judge", session_service=ss)
    session = await ss.create_session(app_name="judge", user_id="judge")

    prompt = f"EVIDENCE:\n{evidence}\n\nREPORT:\n{report_json}"
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    text = ""
    async for ev in runner.run_async(
        user_id="judge", session_id=session.id, new_message=msg
    ):
        if ev.is_final_response() and ev.content and ev.content.parts:
            text = ev.content.parts[0].text or ""
    return JudgeVerdict.model_validate_json(text)


# A built-in demo: one faithful report and one with a planted hallucination.
_EVIDENCE = (
    "Website sells specialty coffee beans and brewing equipment. "
    "Sanctions screening: no matches. Domain age: ~4000 days (well established). "
    "Adverse media: not checked."
)
_FAITHFUL_REPORT = (
    '{"summary": "Established specialty coffee retailer. No sanctions matches and '
    'a long-standing domain. Adverse media was not checked.", '
    '"recommendation": "approve"}'
)
_HALLUCINATED_REPORT = (
    '{"summary": "Coffee retailer. The owner was convicted of fraud in 2019, and '
    'the domain was registered last month.", "recommendation": "decline"}'
)


async def _demo() -> None:
    for label, report in [("FAITHFUL", _FAITHFUL_REPORT),
                          ("HALLUCINATED", _HALLUCINATED_REPORT)]:
        verdict = await judge(_EVIDENCE, report)
        print(f"\n===== {label} report =====")
        print(verdict.model_dump_json(indent=2))


if __name__ == "__main__":
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Set GOOGLE_API_KEY in .env to run the judge (it calls the model).")
        print("It will grade two built-in reports — one faithful, one with a")
        print("planted hallucination (a fabricated fraud conviction) — and should")
        print("catch the second.")
    else:
        asyncio.run(_demo())
