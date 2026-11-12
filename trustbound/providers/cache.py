"""SQLite response cache: identical requests are never paid for twice."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any


class ResponseCache:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=60)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, provider TEXT, model TEXT,"
            " purpose TEXT, request TEXT, response TEXT, created_at REAL)")
        self._conn.commit()

    def get(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT response FROM responses WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key: str, provider: str, model: str, purpose: str,
            request: dict[str, Any], response: dict[str, Any]) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO responses VALUES (?,?,?,?,?,?,?)",
                (key, provider, model, purpose, json.dumps(request, ensure_ascii=False),
                 json.dumps(response, ensure_ascii=False), time.time()))
            self._conn.commit()

    def __len__(self) -> int:
        with self._lock:
            return int(self._conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0])

    def close(self) -> None:
        with self._lock:
            self._conn.close()
