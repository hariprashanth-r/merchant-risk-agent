"""Tool: look up a domain's age via WHOIS.

Domain age is one of the most reliable cheap risk signals there is. A business
"established in 2005" whose website domain was registered three weeks ago is
worth a second look. Fraud rings spin up fresh domains constantly.

Uses the `python-whois` package. WHOIS data is inconsistent across registrars,
so this tool is deliberately defensive and never raises.
"""

from __future__ import annotations

from datetime import datetime, timezone


def whois_lookup(domain: str) -> dict:
    """Look up when a domain was registered and how old it is.

    A very new domain (under ~90 days) on a business that claims to be
    long-established is a meaningful risk signal worth flagging.

    Args:
        domain: A bare domain such as "example-shop.com" (no https://, no path).

    Returns:
        A dict with:
          status: "success" or "error"
          domain: the domain queried
          creation_date: ISO date string, or null if unknown
          age_days: integer age in days, or null if unknown
          registrar: registrar name, if available
    """
    # Strip scheme / path if the model passes a full URL by mistake.
    domain = domain.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        import whois  # imported lazily so the rest of the app loads without it
    except ImportError:
        return {
            "status": "error",
            "domain": domain,
            "error": "The 'python-whois' package is not installed. "
            "Run: pip install python-whois",
        }

    try:
        record = whois.whois(domain)
    except Exception as exc:  # python-whois raises many different error types
        return {"status": "error", "domain": domain, "error": str(exc)}

    creation = record.creation_date
    if isinstance(creation, list):  # some registrars return a list of dates
        creation = creation[0] if creation else None

    creation_iso = None
    age_days = None
    if isinstance(creation, datetime):
        if creation.tzinfo is None:
            creation = creation.replace(tzinfo=timezone.utc)
        creation_iso = creation.date().isoformat()
        age_days = (datetime.now(timezone.utc) - creation).days

    registrar = record.registrar if isinstance(record.registrar, str) else None

    return {
        "status": "success",
        "domain": domain,
        "creation_date": creation_iso,
        "age_days": age_days,
        "registrar": registrar,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(whois_lookup("github.com"), indent=2))