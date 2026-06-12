"""Evaluation harness for the merchant risk agent (Phase 4).

Runs the agent over a labeled "golden" set of merchants and reports:
  - a confusion matrix (expected vs predicted recommendation),
  - accuracy and recall on the "decline" class,
  - a COST-WEIGHTED score (a false approval of a risky merchant hurts most),
  - guardrail gates that must NEVER fail (e.g. a sanctions hit must not approve).

The process exits non-zero if any guardrail fails — so it works as a CI gate.

Run:  python -m evals.run_eval        (or: make eval)

Needs your GOOGLE_API_KEY (it runs the real agent). WITHOUT a key it still runs
the deterministic, tool-level guardrail and tells you how to run the full suite.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from merchant_risk_agent.schemas import RiskReport

GOLDEN = Path(__file__).resolve().parent / "golden_merchants.json"
LABELS = ["approve", "review", "decline"]

# Cost of predicting <pred> when the truth is <truth>. 0 means correct.
# This table encodes the asymmetric reality of risk: letting a bad merchant in
# is far more expensive than turning a good one away.
COST = {
    ("approve", "decline"): 10,  # let a bad merchant in — the worst error
    ("approve", "review"): 3,
    ("review", "decline"): 2,    # at least escalated to a human
    ("decline", "approve"): 2,   # lost a good merchant (recoverable)
    ("decline", "review"): 1,
    ("review", "approve"): 1,    # unnecessary friction
}


def cost(pred: str, truth: str) -> int:
    return 0 if pred == truth else COST.get((pred, truth), 1)


# ---------------------------------------------------------------------------
# Deterministic guardrail — needs NO API key (tests the tool directly).
# ---------------------------------------------------------------------------
def deterministic_guardrail() -> bool:
    """A known sanctioned name MUST be flagged by the sanctions tool."""
    from merchant_risk_agent.tools import check_sanctions

    res = check_sanctions("Acme Sanctioned Holdings")
    ok = res.get("match_found") is True
    print(f"[guardrail] sanctions tool flags a known SDN name : {'PASS' if ok else 'FAIL'}")
    return ok


# ---------------------------------------------------------------------------
# Running the agent (needs the API key).
# ---------------------------------------------------------------------------
async def run_agent(name: str, website: str) -> str:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    from merchant_risk_agent.agent import root_agent

    ss = InMemorySessionService()
    runner = Runner(agent=root_agent, app_name="eval", session_service=ss)
    session = await ss.create_session(app_name="eval", user_id="eval")
    prompt = (
        "Investigate this merchant and return your JSON verdict.\n"
        f"Merchant name: {name}\nWebsite: {website}"
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])

    text = ""
    async for ev in runner.run_async(
        user_id="eval", session_id=session.id, new_message=msg
    ):
        if ev.is_final_response() and ev.content and ev.content.parts:
            text = ev.content.parts[0].text or ""
    return text


def parse(text: str, name: str, website: str) -> RiskReport:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        if t.startswith("json"):
            t = t[4:]
    s, e = t.find("{"), t.rfind("}")
    if s != -1 and e != -1:
        t = t[s : e + 1]
    data = json.loads(t)
    data.setdefault("merchant_name", name)
    data.setdefault("website", website)
    return RiskReport.model_validate(data)


# ---------------------------------------------------------------------------
# Reporting.
# ---------------------------------------------------------------------------
def print_report(rows, matrix, total_cost, guardrail_failures, det_ok) -> None:
    print("\n=== Per-merchant results ===")
    print(f"{'merchant':32} {'expected':9} {'predicted':10} result")
    correct = 0
    for name, truth, pred in rows:
        if pred == truth:
            correct += 1
        print(f"{name[:31]:32} {truth:9} {pred:10} {'ok' if pred == truth else 'MISS'}")

    n = len(rows)
    print("\n=== Confusion matrix (rows = expected, cols = predicted) ===")
    print(" " * 10 + "".join(f"{p:>9}" for p in LABELS))
    for t in LABELS:
        print(f"{t:>10}" + "".join(f"{matrix[t][p]:>9}" for p in LABELS))

    decline_total = sum(matrix["decline"].values())
    decline_hit = matrix["decline"]["decline"]

    print("\n=== Metrics ===")
    print(f"accuracy            : {correct}/{n} = {correct / n:.0%}")
    line = f"recall on 'decline' : {decline_hit}/{decline_total}"
    if decline_total:
        line += f" = {decline_hit / decline_total:.0%}"
    print(line)
    print(f"cost-weighted score : {total_cost}  (lower is better; false approvals weigh most)")

    print("\n=== Guardrails (must pass) ===")
    print(f"  sanctions tool flags known SDN name : {'PASS' if det_ok else 'FAIL'}")
    if guardrail_failures:
        print(f"  sanctioned merchant NOT approved    : FAIL -> {guardrail_failures}")
    else:
        print("  sanctioned merchant NOT approved    : PASS")

    verdict = "PASS" if (det_ok and not guardrail_failures) else "FAIL"
    print(f"\nOVERALL GUARDRAIL VERDICT: {verdict}")


# ---------------------------------------------------------------------------
# Main.
# ---------------------------------------------------------------------------
def main() -> None:
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))
    print(f"Loaded {len(cases)} golden cases from {GOLDEN.name}\n")

    det_ok = deterministic_guardrail()

    if not os.environ.get("GOOGLE_API_KEY"):
        print("\nNo GOOGLE_API_KEY set — ran the deterministic guardrail only.")
        print("Add your key to .env to run the full golden-set evaluation.")
        sys.exit(0 if det_ok else 1)

    matrix = {t: {p: 0 for p in LABELS} for t in LABELS}
    total_cost = 0
    guardrail_failures: list[str] = []
    rows = []

    for c in cases:
        print(f"  investigating: {c['name']} ...")
        text = asyncio.run(run_agent(c["name"], c["website"]))
        try:
            pred = parse(text, c["name"], c["website"]).recommendation
        except Exception as ex:  # noqa: BLE001 — record, don't crash the eval
            print(f"    (could not parse verdict: {ex})")
            pred = "ERROR"
        truth = c["expected_recommendation"]
        rows.append((c["name"], truth, pred))
        if pred in LABELS:
            matrix[truth][pred] += 1
            total_cost += cost(pred, truth)
            if c.get("hard_stop") and pred == "approve":
                guardrail_failures.append(c["name"])

    print_report(rows, matrix, total_cost, guardrail_failures, det_ok)
    sys.exit(1 if (guardrail_failures or not det_ok) else 0)


if __name__ == "__main__":
    main()
