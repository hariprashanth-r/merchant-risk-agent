# Learning path

Work through these in order. Each phase ends with an exercise that changes the
code, because you learn agents by tuning them, not by reading about them.

---

## Phase 0 — Run it and watch it think
**Goal:** understand the agent loop and that a tool is a function with a docstring.

1. Follow the Quickstart in the README and run `adk web`.
2. Investigate two merchants: a normal business and `"Acme Sanctioned Holdings"`.
3. In the trace panel, watch the order of tool calls. Notice you never told it
   that order — it decided.

**Exercise:** open `merchant_risk_agent/tools/website.py` and worsen the
docstring (delete the description). Restart, run again. Does the agent still call
it at the right time? Restore the docstring. This shows the docstring is part of
the prompt.

---

## Phase 1 — Wire up adverse media (your first real tool)
**Goal:** add a genuine data source the agent can call.

`merchant_risk_agent/tools/adverse_media.py` is a stub. Implement it one of two ways:

- **Option A — a search API you call.** Sign up for a search API (Brave Search,
  Tavily, or SerpAPI all have free tiers). Inside `search_adverse_media`, query
  `"{merchant_name} fraud OR scam OR lawsuit"`, and return the top hits as
  `{title, url, snippet}`. This keeps it a normal function tool.
- **Option B — ADK's built-in Google Search.** `from google.adk.tools import
  google_search`. Built-in tools can't share an agent with custom function tools
  in current ADK, so you'll put it in its own sub-agent — which is exactly Phase 3.

**Exercise:** after wiring Option A, investigate a business that has had public
trouble and confirm an `adverse_media` flag appears with a real URL as evidence.

---

## Phase 2 — Make the verdict trustworthy
**Goal:** tighten the structured output and the scoring policy.

1. Read `merchant_risk_agent/schemas.py`. Add a new field to `RiskReport`, e.g.
   `confidence: Literal["low","medium","high"]`. Update
   `output_format_instructions()` to describe it.
2. Re-run. Does the agent populate it? Does validation still pass?
3. Tune the `INSTRUCTION` scoring rules in `agent.py` until borderline cases land
   on `review` rather than `approve`.

**Exercise:** intentionally feed a tricky case (a vague one-page site with no
products) and adjust the prompt until the agent reliably flags `shell_indicators`.

---

## Phase 3 — Go multi-agent
**Goal:** learn ADK's agent-as-a-tool pattern and separate gathering from judging.

Split the work:
- a **gatherer** agent whose only job is to collect evidence (and which can now
  hold the built-in `google_search` tool), and
- a **scorer** agent that takes the gathered evidence and produces the
  `RiskReport`.

The root agent calls the gatherer, then the scorer. This is cleaner, easier to
test, and is the standard way to combine built-in and custom tools.

**Exercise:** give the gatherer and scorer different models (a cheaper model to
gather, a stronger one to judge) and compare cost vs quality.

---

## Phase 4 — Evaluate and keep a human in the loop
**Goal:** measure quality and design escalation, like a real system.

1. Build a small test set: ~10 merchants you've labelled yourself (clean / risky),
   as a JSON or CSV file.
2. Run each through the agent and compare the recommendation to your label.
   Count false approvals (worst) and false declines (annoying). Look at ADK's
   built-in evaluation tooling for a structured way to do this.
3. In the frontend, add a "Reviewer queue": any `review` verdict lands in a list
   a human can mark approved/declined. Now the agent assists rather than decides.

**Exercise:** find one merchant the agent gets wrong, then fix it with a prompt
change *without* breaking the cases it already gets right. That tension —
improving one case without regressing others — is the real job.

---

## Where to go after

- Stream tool-call events to the UI so users watch the investigation live.
- Add transaction-monitoring signals (velocity, refund rates) for *ongoing* risk,
  not just onboarding.
- Replace the in-memory session service with a persistent one and add auth.
- Containerise and deploy (ADK supports Cloud Run and Agent Engine).
