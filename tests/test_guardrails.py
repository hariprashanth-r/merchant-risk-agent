"""Guardrail tests — the 'must never happen' checks (Layer 5).

These are the deterministic, tool-level guardrails: they need no API key and run
in CI on every commit. The agent-level guardrails (e.g. "a sanctions hit must
never be approved") live in evals/run_eval.py because they require running the
model.
"""

from merchant_risk_agent.tools import check_sanctions


def test_known_sanctioned_name_is_flagged():
    # A name on the list MUST be caught — this is a hard requirement.
    assert check_sanctions("Acme Sanctioned Holdings")["match_found"] is True


def test_known_sanctioned_individual_is_flagged():
    assert check_sanctions("Maria Testperson")["match_found"] is True


def test_clean_name_is_not_flagged():
    # A clearly unrelated name must NOT produce a false positive.
    assert check_sanctions("Friendly Neighborhood Bakery")["match_found"] is False
