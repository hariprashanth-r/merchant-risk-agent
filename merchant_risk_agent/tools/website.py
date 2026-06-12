"""Tool: fetch and summarise a merchant's website.

THE MOST IMPORTANT THING ABOUT AN ADK TOOL IS ITS DOCSTRING.
ADK reads the function signature and this docstring to tell the language model
what the tool does, what arguments it takes, and what it returns. The model
uses that description to decide *when* to call the tool. So the docstring below
is not just documentation for humans, it is part of the prompt.

This tool answers the single most useful question in merchant risk:
"Does the website actually sell what the business claims to sell?"
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

# Be polite and identifiable. Real crawlers always send a User-Agent.
_HEADERS = {"User-Agent": "merchant-risk-agent/0.1 (learning project)"}
_MAX_CHARS = 4000  # keep the page text small so we don't blow up the context window


def fetch_website(url: str) -> dict:
    """Fetch a merchant's web page and return its visible text and metadata.

    Use this first in almost every investigation: it tells you what the
    business actually sells, which you can then compare against what they claim.

    Args:
        url: The merchant's website, e.g. "https://example-shop.com". A bare
            domain like "example-shop.com" is also accepted.

    Returns:
        A dict with:
          status: "success" or "error"
          url: the URL that was fetched
          title: the page <title>, if any
          description: the meta description, if any
          text_excerpt: the first few thousand characters of visible text
          error: present only when status is "error"
    """
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as exc:
        # An unreachable site is itself a (mild) risk signal, so we return a
        # clean error the agent can reason about rather than raising.
        return {"status": "error", "url": url, "error": str(exc)}

    soup = BeautifulSoup(resp.text, "html.parser")

    # Drop script/style so we keep human-visible words only.
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    description = ""
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        description = meta["content"].strip()

    text = " ".join(soup.get_text(separator=" ").split())

    return {
        "status": "success",
        "url": url,
        "title": title,
        "description": description,
        "text_excerpt": text[:_MAX_CHARS],
    }

if __name__ == "__main__":
    import json
    result = fetch_website("https://example.com")
    print(json.dumps(result, indent=2))