import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

APP_NAME = "Webhook Receiver"
DB_PATH = os.getenv("DB_PATH", "data/webhooks.db")
WEBHOOK_API_KEY = os.getenv("WEBHOOK_API_KEY", "").strip()

app = FastAPI(title=APP_NAME, version="1.0.0")


def get_connection() -> sqlite3.Connection:
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS webhook_events (
                id TEXT PRIMARY KEY,
                received_at TEXT NOT NULL,
                content_type TEXT,
                source_ip TEXT,
                payload TEXT NOT NULL
            )
            """
        )
        conn.commit()


@app.on_event("startup")
def startup() -> None:
    initialize_database()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": APP_NAME,
        "status": "running",
        "health": "/health",
        "webhook_endpoint": "POST /webhook",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def receive_webhook(
    request: Request,
    x_webhook_secret: str | None = Header(default=None),
) -> JSONResponse:
    # Set WEBHOOK_API_KEY in the hosting environment to enforce authentication.
    # Configure the sending application to pass it as X-Webhook-Secret.
    if WEBHOOK_API_KEY and x_webhook_secret != WEBHOOK_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing webhook secret")

    try:
        payload: Any = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Request body must contain valid JSON")

    event_id = str(uuid.uuid4())
    received_at = datetime.now(timezone.utc).isoformat()
    content_type = request.headers.get("content-type")
    source_ip = request.client.host if request.client else None

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO webhook_events (id, received_at, content_type, source_ip, payload)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                event_id,
                received_at,
                content_type,
                source_ip,
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        conn.commit()

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "Webhook received and stored",
            "event_id": event_id,
            "received_at": received_at,
        },
    )


@app.get("/events")
def list_events(limit: int = 20) -> dict[str, Any]:
    # Basic event viewer. Protect this route before exposing it publicly.
    limit = max(1, min(limit, 100))
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, received_at, content_type, source_ip, payload
            FROM webhook_events
            ORDER BY received_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return {
        "count": len(rows),
        "events": [
            {
                "id": row["id"],
                "received_at": row["received_at"],
                "content_type": row["content_type"],
                "source_ip": row["source_ip"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ],
    }
