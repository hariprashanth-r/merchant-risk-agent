# Architecture

The whole point of this project is to show that **an AI agent is just one service
in an ordinary application**. Once you internalise that, agents stop feeling
mysterious.

## The four tiers

### 1. Frontend (`frontend/`)
Plain HTML, CSS, and JavaScript — no build step, no framework. It does three
things: collect a merchant name + website, POST them to the backend, and render
the returned verdict. Kept framework-free so the request/response contract is
completely visible. Once you're comfortable, swapping in React or Vue changes
nothing about the tiers behind it.

### 2. Backend API (`server/main.py`)
A FastAPI app. Its jobs:
- expose `POST /api/investigate` and `GET /api/investigations`,
- run the agent through ADK's `Runner`,
- validate the agent's output against the `RiskReport` schema,
- persist each result to SQLite,
- serve the frontend's static files.

The backend treats the agent like any other dependency it calls.

### 3. The agent (`merchant_risk_agent/`)
An ADK `Agent` = a model + an instruction + a list of tools. ADK runs the
reasoning loop. The agent never touches HTTP, the database, or the browser — it
only knows how to investigate and return a report.

### 4. Data sources (the tools)
Each tool reaches one real source: the merchant's website, a sanctions file,
WHOIS, and (once you build it) web search. Tools are the agent's senses.

## Request lifecycle

```
1. User submits "Acme Trading LLC" + "acme-trading.com" in the browser.
2. app.js  ──POST /api/investigate──►  FastAPI.
3. FastAPI builds a prompt and calls runner.run_async(...).
4. The agent loop begins:
      model: "I should see the site"      → calls fetch_website
      model: "now screen the name"        → calls check_sanctions
      model: "how old is the domain?"     → calls whois_lookup
      model: "any bad press?"             → calls search_adverse_media
      model: emits a JSON RiskReport.
5. FastAPI strips/parses the JSON, validates it with Pydantic.
6. FastAPI saves it to SQLite and returns it as the HTTP response.
7. app.js renders the verdict stamp, score gauge, and flags.
```

## Why the agent loop is not in your code

You never wrote a `while` loop that decides which tool to call next. That's the
value ADK adds: given the instruction and the tool docstrings, the model plans
the sequence itself. Your leverage is in two places — the **instruction** (the
policy) and the **tool docstrings** (what the model believes each tool can do).

## Where state lives

- **Conversation/session state**: held by ADK's session service (in-memory here;
  swap for a persistent one to keep multi-turn history).
- **Investigation results**: SQLite (`data/investigations.db`), written by the
  backend, independent of the agent.

This separation is deliberate. The agent stays stateless and testable; durable
records are the app's responsibility.

## Natural next architectural steps

- **Multi-agent** (Phase 3): split into a "gatherer" agent and a "scorer" agent
  using ADK's agent-as-a-tool pattern. This is also how you add the built-in
  Google Search tool cleanly.
- **Streaming**: stream tool-call events to the frontend so the user watches the
  investigation happen instead of waiting.
- **Human-in-the-loop**: route "review" verdicts to a queue a person clears.
- **Persistent sessions + auth**: once more than one analyst uses it.
  