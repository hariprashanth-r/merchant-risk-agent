"""Tests for the tools.

These run without an API key and without network access (except the website
test, which is skipped by default). Run them with:  pytest

Testing tools in isolation is good practice: the agent's behaviour is hard to
test deterministically, but a tool is just a function with inputs and outputs.
"""

from merchant_risk_agent.tools import check_sanctions, search_adverse_media


def test_sanctions_hits_known_name():
    result = check_sanctions("Acme Sanctioned Holdings")
    assert result["status"] == "success"
    assert result["match_found"] is True
    assert result["matches"][0]["name"] == "Acme Sanctioned Holdings"


def test_sanctions_clean_name():
    result = check_sanctions("Totally Normal Coffee Roasters")
    assert result["status"] == "success"
    assert result["match_found"] is False


def test_sanctions_partial_match():
    # Substring match should still surface the listed entity.
    result = check_sanctions("Redline Arms")
    assert result["match_found"] is True


def test_adverse_media_is_a_clean_stub():
    result = search_adverse_media("Anyone")
    assert result["status"] == "not_configured"
    assert result["hits"] == []
