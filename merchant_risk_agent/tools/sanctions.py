"""Tool: screen a name against a sanctions list (OFAC SDN style).

Sanctions screening is non-negotiable in real onboarding: you may not do
business with sanctioned people or entities, full stop. This tool does a
simple fuzzy name match against a local CSV.

By default it reads `data/sample_sdn.csv`, a tiny made-up list so the project
runs out of the box. To use the real list, run `scripts/download_ofac.py` and
point SANCTIONS_FILE at the downloaded file (see the function below).

NOTE: real screening is much more involved (aliases, transliteration, fuzzy
scoring thresholds, secondary-sanctions logic). This is a learning version.
"""

from __future__ import annotations

import csv
import os
from difflib import SequenceMatcher
from pathlib import Path

# Default to the bundled sample so the project works with zero setup.
_DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "sample_sdn.csv"
_MATCH_THRESHOLD = 0.82  # how close a name must be to count as a hit


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def check_sanctions(name: str) -> dict:
    """Check whether a name appears on the sanctions list.

    Run this on the merchant's legal name and on the names of its owners or
    directors if you have them. Any high-confidence match is a hard stop.

    Args:
        name: The person or business name to screen, e.g. "Acme Trading LLC".

    Returns:
        A dict with:
          status: "success" or "error"
          query: the name that was screened
          match_found: True if at least one likely match was found
          matches: list of {name, program, score} for likely matches
    """
    file_path = Path(os.environ.get("SANCTIONS_FILE", _DEFAULT_FILE))
    if not file_path.exists():
        return {
            "status": "error",
            "query": name,
            "error": f"Sanctions file not found at {file_path}. "
            "Run scripts/download_ofac.py or set SANCTIONS_FILE.",
        }

    matches = []
    with file_path.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            listed_name = row.get("name", "")
            score = _similarity(name, listed_name)
            # Treat a substring hit as a strong signal too ("Acme" in "Acme Trading").
            if name.lower() in listed_name.lower() or score >= _MATCH_THRESHOLD:
                matches.append(
                    {
                        "name": listed_name,
                        "program": row.get("program", ""),
                        "score": round(max(score, 0.95 if name.lower() in listed_name.lower() else score), 3),
                    }
                )

    matches.sort(key=lambda m: m["score"], reverse=True)
    return {
        "status": "success",
        "query": name,
        "match_found": bool(matches),
        "matches": matches[:5],
    }

if __name__ == "__main__":
    import json
    print(json.dumps(check_sanctions("Redline Arms"), indent=2))