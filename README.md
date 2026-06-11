# Merchant Risk Investigation Agent

An AI agent that investigates a merchant for onboarding risk and returns a
structured verdict — **approve**, **review**, or **decline** — with the evidence
behind every flag. Built with [Google's Agent Development Kit (ADK)](https://google.github.io/adk-docs/)
and wrapped in a small full-stack web app.

This is a **learning project**. It is deliberately readable, heavily commented,
and built up in phases so you can understand every piece. It is *not* a
production compliance system, and the bundled sanctions list is fake sample data.

---

## What it does

You give it a merchant name and website. The agent then:

1. **Fetches the website** to see what the business actually sells.
2. **Screens the name** against a sanctions list (OFAC SDN style).
3. **Checks the domain age** — brand-new domains are a classic fraud signal.
4. **Checks for adverse media** (this one is a wired-up-it-yourself exercise).
5. **Writes a verdict**: a 0–100 risk score, a recommendation, and a list of
   flags, each with concrete evidence.

The agent recommends; a human makes the final call. That mirrors how real
Know-Your-Business (KYB) and onboarding teams work.

---

## What you'll learn

- **Agent fundamentals** — how an ADK agent loops over model + tools, and why a
  tool is just a Python function with a good docstring.
- **Tool design** — turning real data sources (a website, a sanctions file,
  WHOIS) into things a model can call.
- **Structured output** — forcing a messy investigation into a validated schema.
- **Full-stack wiring** — a FastAPI backend, a SQLite store, and a plain-JS
  frontend, with the agent as just one tier.
- **The risk domain** — sanctions, transaction laundering, content mismatch,
  domain-age signals, and why humans stay in the loop.

A phased plan with exercises lives in [`docs/LEARNING_PATH.md`](docs/LEARNING_PATH.md).
The system design is in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

---

## Architecture at a glance

```
   Browser (frontend/)            FastAPI (server/)              ADK agent (merchant_risk_agent/)
 ┌───────────────────┐        ┌────────────────────┐         ┌──────────────────────────────┐
 │  enter merchant   │  POST  │  /api/investigate  │  runs   │  root_agent (Gemini)         │
 │  show verdict     ├───────►│  validate + store  ├────────►│   ├─ fetch_website           │
 │  list past cases  │  JSON  │  SQLite            │ events  │   ├─ check_sanctions         │
 └───────────────────┘◄───────┤  serve frontend    │◄────────┤   ├─ whois_lookup            │
                              └────────────────────┘         │   └─ search_adverse_media    │
                                                             └──────────────────────────────┘
```

The agent is one service. Everything else is a normal web app around it.

---

## Quickstart

### Prerequisites
- Python 3.11+
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)
  (no credit card needed)

### 1. Install
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your API key
```bash
cp .env.example .env
# open .env and paste your key into GOOGLE_API_KEY
```

### 3a. Run it the quick way — the ADK playground
No frontend needed. This is the best way to *watch the agent think*.
```bash
adk web
```
Open the URL it prints, pick `merchant_risk_agent`, and type:
> Investigate the merchant "Blue Ridge Coffee" with website bluebottlecoffee.com

You'll see each tool call and its result in the trace panel.

### 3b. Run it as a full-stack app
```bash
uvicorn server.main:app --reload
```
Open **http://localhost:8000**, enter a merchant, and watch the verdict appear.

(There's also a `Makefile`: `make install`, `make web`, `make serve`, `make test`.)

---

## Things to try

- A normal business (should approve): a real local bakery's site.
- A sanctions hit (should decline): name it **"Acme Sanctioned Holdings"** — that
  name is in the bundled sample list (`data/sample_sdn.csv`).
- A brand-new domain: register-date signals push the score up.

Then open `merchant_risk_agent/agent.py` and change the `INSTRUCTION`. Re-run.
Prompt tuning *is* most of agent engineering — feel how much the wording moves
the result.

---

## Project structure

```
merchant-risk-agent/
├── merchant_risk_agent/      # the agent (this is the core)
│   ├── agent.py              # root_agent: model + instruction + tools
│   ├── schemas.py            # the RiskReport output shape (Pydantic)
│   └── tools/                # one file per tool, each a documented function
│       ├── website.py
│       ├── sanctions.py
│       ├── whois_lookup.py
│       └── adverse_media.py  # a stub you implement (first exercise)
├── server/main.py            # FastAPI: runs the agent, stores results, serves UI
├── frontend/                 # plain HTML/CSS/JS console
├── data/sample_sdn.csv       # fake sanctions data so it runs out of the box
├── scripts/download_ofac.py  # fetch the real OFAC list
├── tests/test_tools.py       # tool tests (no API key needed)
└── docs/                     # ARCHITECTURE.md and LEARNING_PATH.md
```

---

## Push it to GitHub

This folder is already a git repository with one commit. To publish it:

```bash
# create an empty repo on github.com first (no README), then:
git remote add origin https://github.com/<you>/merchant-risk-agent.git
git branch -M main
git push -u origin main
```

Your `.env` is gitignored, so your key stays private.

---

## Important notes

- **Not real compliance.** Sanctions screening here is a fuzzy name match against
  fake sample data. Real screening handles aliases, transliteration, scoring
  thresholds, and legal nuance. Never use this to make actual onboarding
  decisions.
- **ADK moves fast** (roughly bi-weekly releases). If an import or API name in
  `server/main.py` doesn't match your installed version, check the current docs
  at <https://google.github.io/adk-docs/>. Pin your version in `requirements.txt`.
- **The human decides.** The agent is built to escalate uncertainty to "review",
  not to auto-decide borderline cases.

MIT licensed. Built to be taken apart.
