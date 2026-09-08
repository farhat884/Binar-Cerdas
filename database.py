"""Shared synchronous Turso/libSQL database client and small SQL helpers."""
import json
import os
import uuid
from datetime import datetime, timezone

import libsql_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("TURSO_DATABASE_URL")
token = os.getenv("TURSO_AUTH_TOKEN")

if not url:
    raise RuntimeError("TURSO_DATABASE_URL belum diset")
if not token:
    raise RuntimeError("TURSO_AUTH_TOKEN belum diset")

# libsql:// is mapped to WebSocket by libsql-client. HTTPS is more reliable
# for this Flask/Vercel deployment and is already supported by Turso.
if url.startswith("libsql://"):
    url = "https://" + url[len("libsql://"):]

db = libsql_client.create_client_sync(url, auth_token=token)


def new_id():
    return uuid.uuid4().hex[:20]


def utcnow_iso():
    return datetime.now(timezone.utc).isoformat()


def fetch_all(sql, params=()):
    result = db.execute(sql, params)
    columns = list(getattr(result, "columns", []) or [])
    return [dict(zip(columns, row)) for row in result.rows]


def fetch_one(sql, params=()):
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    return db.execute(sql, params)


def json_dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads(value, default=None):
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def as_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}
