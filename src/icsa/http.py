"""Polite HTTP client: retries, rate limiting and a small disk cache."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import requests

CACHE_DIR = Path(os.environ.get("ICSA_CACHE", ".cache"))
USER_AGENT = "interview-calibrated-sourcing-agent/0.1 (+https://github.com/davemendoza/interview-calibrated-sourcing-agent)"


class Http:
    def __init__(self, min_interval: float = 0.25, cache_hours: float = 20.0) -> None:
        self.session = requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT
        self.min_interval = min_interval
        self.cache_seconds = cache_hours * 3600
        self._last = 0.0

    def _cache_path(self, url: str, params: dict | None, headers: dict | None) -> Path:
        auth_free = {k: v for k, v in (headers or {}).items() if k.lower() not in {"authorization", "x-api-key"}}
        raw = json.dumps([url, params or {}, auth_free], sort_keys=True)
        return CACHE_DIR / (hashlib.sha256(raw.encode()).hexdigest() + ".json")

    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None):
        path = self._cache_path(url, params, headers)
        if path.exists() and time.time() - path.stat().st_mtime < self.cache_seconds:
            return json.loads(path.read_text())
        data = self._fetch(url, params, headers).json()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        return data

    def get_text(self, url: str) -> str:
        return self._fetch(url, None, None).text

    def _fetch(self, url: str, params: dict | None, headers: dict | None) -> requests.Response:
        for attempt in range(4):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            resp = self.session.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code in (429, 502, 503, 504):
                time.sleep(2 ** attempt * 2)
                continue
            if resp.status_code == 403 and resp.headers.get("X-RateLimit-Remaining") == "0":
                reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
                raise RuntimeError(f"GitHub rate limit reached; resets at {time.ctime(reset)}")
            resp.raise_for_status()
            return resp
        resp.raise_for_status()
        return resp
