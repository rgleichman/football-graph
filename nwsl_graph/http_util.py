from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_USER_AGENT = "curl/8.0"
_CTX = ssl.create_default_context()


def get_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if params:
        q = urllib.parse.urlencode(params)
        sep = "&" if "?" in url else "?"
        full = f"{url}{sep}{q}" if params else url
    else:
        full = url
    req = urllib.request.Request(full, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=90, context=_CTX) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=60, context=_CTX) as resp:
        return resp.read()
