"""FastAPI server - the tier that makes this a full-stack app.

The agent is just one service. This file:
  - runs the agent on demand via ADK's Runner,
  - validates the agent's JSON against our RiskReport schema,
  - saves each investigation to a small SQLite database,
  - serves the frontend and a tiny JSON API the frontend calls.

Run it with:  uvicorn server.main:app --reload
Then open:     http://localhost:8000
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything that needs the API key.
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ADK runtime pieces.
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from merchant_risk_agent.agent import root_agent
from merchant_risk_agent.schemas import RiskReport

APP_NAME = "merchant_risk"
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "investigations.db"
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

app = FastAPI(title="Merchant Risk Investigation Agent")

# One Runner + session service for the whole app. The Runner is what actually
# drives the agent loop. (API names here can shift between ADK versions; if an
# import fails, check the current docs at google.github.io/adk-docs.)
session_service = InMemorySessionService()
runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)


# ---------------------------------------------------------------------------
# Database (plain sqlite3 - no ORM, so you can see exactly what is happening)
# ---------------------------------------------------------------------------
def init_db() -> None:
    DB_PATH.parent.mkdir(exist_ok=True)
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS investigations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                merchant_name TEXT NOT NULL,
                website TEXT NOT NULL,
                risk_score INTEGER,
                risk_level TEXT,
                recommendation TEXT,
                report_json TEXT NOT NULL
            )
            """
        )
        conn.commit()


def save_investigation(report: RiskReport) -> int:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        cur = conn.execute(
            """INSERT INTO investigations
               (created_at, merchant_name, website, risk_score, risk_level,
                recommendation, report_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                report.merchant_name,
                report.website,
                report.risk_score,
                report.risk_level,
                report.recommendation,
                report.model_dump_json(),
            ),
        )
        conn.commit()
        return cur.lastrowid


def list_investigations(limit: int = 20) -> list[dict]:
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM investigations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Running the agent
# ---------------------------------------------------------------------------
async def run_agent(merchant_name: str, website: str) -> str:
    """Run one investigation and return the agent's final text response."""
    user_id = "analyst"
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=user_id
    )
    prompt = (
        "Investigate this merchant and return your JSON verdict.\n"
        f"Merchant name: {merchant_name}\n"
        f"Website: {website}"
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=message
    ):
        if event.is_final_response() and event.content and event.content.parts:
            final_text = event.content.parts[0].text or ""
    return final_text


def parse_report(raw: str, merchant_name: str, website: str) -> RiskReport:
    """Turn the agent's text into a validated RiskReport.

    The agent is told to return pure JSON, but models sometimes wrap it in
    ```json fences or add a stray sentence. We strip the obvious cases, then
    validate. If parsing fails we raise a clear error instead of returning junk.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[len("json"):]
    # Grab the outermost JSON object if there is surrounding prose.
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Agent did not return valid JSON: {exc}. Raw start: {raw[:200]}",
        )

    data.setdefault("merchant_name", merchant_name)
    data.setdefault("website", website)
    try:
        return RiskReport.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise HTTPException(status_code=502, detail=f"Report failed validation: {exc}")


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
class InvestigateRequest(BaseModel):
    merchant_name: str
    website: str


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.post("/api/investigate", response_model=RiskReport)
async def investigate(req: InvestigateRequest) -> RiskReport:
    raw = await run_agent(req.merchant_name, req.website)
    report = parse_report(raw, req.merchant_name, req.website)
    save_investigation(report)
    return report


@app.get("/api/investigations")
def investigations() -> list[dict]:
    return list_investigations()


# Serve the frontend. Keep this LAST so it doesn't shadow the /api routes.
@app.get("/")
def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")
