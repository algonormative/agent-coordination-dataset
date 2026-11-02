"""Minimal read-only Moltbook API client used by extract.py.

The key comes from MOLTBOOK_API_KEY and goes in the Authorization header only;
it is never printed or written to disk.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://www.moltbook.com"


def load_key() -> str:
    key = os.environ.get("MOLTBOOK_API_KEY", "").strip()
    if not key:
        sys.exit("set MOLTBOOK_API_KEY to a Moltbook agent API key")
    return key


def request(method: str, path: str, key: str, timeout: int = 30):
    """One HTTP call. Errors come back as dicts rather than exceptions."""
    req = urllib.request.Request(
        BASE + path, method=method,
        headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode(errors="replace").strip()
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode(errors="replace")[:600]}
    except (urllib.error.URLError, TimeoutError) as e:
        return {"transport_error": str(e)}
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"parse_error": raw[:600]}
