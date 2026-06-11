"""Data shapes for a merchant risk investigation.

The agent gathers messy evidence from several tools, but the *output* of an
investigation should always be a clean, predictable structure. That is what
these Pydantic models are for: they describe the final verdict so the API,
the database, and the frontend can all rely on the same shape.

Why Pydantic? It validates data at runtime. If the model returns a risk_score
of 250 or a recommendation of "maybe", validation fails loudly instead of
silently corrupting your report.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

# These three decisions mirror how real onboarding / underwriting teams work:
# most merchants are auto-approved, a minority need a human to look, and a few
# are clearly declined. The agent never makes the final call alone on "review".
Recommendation = Literal["approve", "review", "decline"]
Severity = Literal["low", "medium", "high"]
RiskLevel = Literal["low", "medium", "high"]


class RiskFlag(BaseModel):
    """A single risk signal the agent found, with the evidence behind it.

    Every flag must carry evidence. A flag without evidence is just an opinion,
    and in compliance work an opinion you can't show your reviewer is useless.
    """

    category: str = Field(
        description="Short risk category, e.g. 'prohibited_goods', 'sanctions', "
        "'new_domain', 'content_mismatch', 'adverse_media'."
    )
    severity: Severity = Field(description="How serious this single signal is.")
    evidence: str = Field(
        description="The concrete fact that triggered the flag, in one or two "
        "sentences. Quote or paraphrase what a tool actually returned."
    )


class RiskReport(BaseModel):
    """The full result of investigating one merchant."""

    merchant_name: str
    website: str
    risk_score: int = Field(ge=0, le=100, description="0 = clean, 100 = maximum risk.")
    risk_level: RiskLevel
    recommendation: Recommendation
    flags: List[RiskFlag] = Field(default_factory=list)
    summary: str = Field(
        description="A 2-4 sentence narrative a human reviewer can read first."
    )


def output_format_instructions() -> str:
    """Build the snippet of agent instructions that pins down the JSON shape.

    We keep this next to the schema so the prompt and the validator never drift
    apart. If you add a field above, the agent is told about it here too.
    """
    return (
        "When you have finished gathering evidence, output ONLY a single JSON "
        "object (no markdown fences, no commentary) with exactly these keys:\n"
        '  "merchant_name": string\n'
        '  "website": string\n'
        '  "risk_score": integer 0-100\n'
        '  "risk_level": one of "low" | "medium" | "high"\n'
        '  "recommendation": one of "approve" | "review" | "decline"\n'
        '  "flags": a list of objects, each with "category" (string), '
        '"severity" ("low"|"medium"|"high"), and "evidence" (string)\n'
        '  "summary": a 2-4 sentence string for a human reviewer\n'
        "If a tool could not return data, do not invent it. Record the gap as a "
        "low-severity flag instead."
    )
