"""Disk cache for Gnani responses, so no call is ever paid for twice."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any


def request_key(params: dict[str, Any], payload: bytes = b"") -> str:
    blob = json.dumps(params, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob + b"\0" + payload).hexdigest()


def cached_bytes(cache_dir: Path, namespace: str, key: str, call: Callable[[], bytes]) -> bytes:
    path = cache_dir / namespace / f"{key}.bin"
    if path.exists():
        return path.read_bytes()
    data = call()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data
