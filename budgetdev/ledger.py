import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Ledger:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        return sqlite3.connect(self.path)

    def _initialize(self):
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                    model TEXT NOT NULL, action TEXT NOT NULL, prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL, total_tokens INTEGER NOT NULL,
                    success INTEGER NOT NULL, error TEXT, metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                    tool_name TEXT NOT NULL, arguments_json TEXT NOT NULL, success INTEGER NOT NULL,
                    result_summary TEXT, error TEXT, duration_ms REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def log_llm_call(self, model, action, prompt_tokens=0, completion_tokens=0,
                     total_tokens=0, success=True, error=None, metadata=None):
        with self._connect() as db:
            db.execute(
                """INSERT INTO llm_calls
                (created_at, model, action, prompt_tokens, completion_tokens, total_tokens,
                 success, error, metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (self._now(), model, action, prompt_tokens, completion_tokens, total_tokens,
                 int(success), error, json.dumps(metadata or {})),
            )

    def log_tool_call(self, tool_name, arguments=None, success=True, result_summary="",
                      error=None, duration_ms=0):
        with self._connect() as db:
            db.execute(
                """INSERT INTO tool_calls
                (created_at, tool_name, arguments_json, success, result_summary, error, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (self._now(), tool_name, json.dumps(arguments or {}), int(success),
                 result_summary, error, duration_ms),
            )

    def total_tokens(self):
        with self._connect() as db:
            return db.execute("SELECT COALESCE(SUM(total_tokens), 0) FROM llm_calls").fetchone()[0]

    def calls_by_tool(self):
        with self._connect() as db:
            rows = db.execute(
                "SELECT tool_name, COUNT(*) FROM tool_calls GROUP BY tool_name"
            ).fetchall()
        return {name: count for name, count in rows}

    def summary(self) -> dict[str, Any]:
        with self._connect() as db:
            llm_calls = db.execute("SELECT COUNT(*) FROM llm_calls").fetchone()[0]
            tool_calls = db.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]
            rows = db.execute(
                "SELECT model, SUM(total_tokens) FROM llm_calls GROUP BY model"
            ).fetchall()
        return {
            "total_tokens": self.total_tokens(),
            "llm_calls": llm_calls,
            "tool_calls": tool_calls,
            "tokens_by_model": {model: tokens for model, tokens in rows},
            "calls_by_tool": self.calls_by_tool(),
        }
