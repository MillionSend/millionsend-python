"""HTTP layer: config resolution, request dispatch, response wrapping.

Config (``api_key``, ``base_url``, ``timeout``) lives on the top-level
``millionsend`` package and is read here at call time, so setting
``millionsend.api_key = "..."`` — or the env vars — takes effect for every
resource call without re-instantiating anything.
"""

import json
import os
from typing import Any, Dict, Optional

import requests

from .errors import MillionSendError, MissingApiKeyError, raise_api_error

VERSION = "0.2.0"
DEFAULT_BASE_URL = "http://localhost:3001"
DEFAULT_TIMEOUT = 60.0

_JSON_METHODS = ("POST", "PATCH")


class Response(dict):
    """A ``dict`` that also allows attribute access (``resp.id`` == ``resp["id"]``).

    Nested dicts and list items are wrapped too, so ``resp.data[0].id`` works.
    """

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def _wrap(value: Any) -> Any:
    if isinstance(value, dict):
        return Response({k: _wrap(v) for k, v in value.items()})
    if isinstance(value, list):
        return [_wrap(v) for v in value]
    return value


def _config(name: str) -> Any:
    import millionsend  # partial at import time, fully populated at call time

    return getattr(millionsend, name, None)


def _api_key() -> str:
    key = _config("api_key") or os.environ.get("MILLIONSEND_API_KEY")
    if not key:
        raise MissingApiKeyError(
            "Missing API key. Set millionsend.api_key or the MILLIONSEND_API_KEY env var."
        )
    return key


def _base_url() -> str:
    base = _config("base_url") or os.environ.get("MILLIONSEND_BASE_URL") or DEFAULT_BASE_URL
    return base.rstrip("/")


def list_query(
    limit: Optional[int] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Flatten keyset list options into a query map (None values dropped)."""
    query: Dict[str, Any] = {}
    if limit is not None:
        query["limit"] = limit
    if after is not None:
        query["after"] = after
    if before is not None:
        query["before"] = before
    return query or None


def request(
    method: str,
    path: str,
    *,
    body: Any = None,
    query: Optional[Dict[str, Any]] = None,
    idempotency_key: Optional[str] = None,
) -> Any:
    """Dispatch one request and return the wrapped JSON body, or raise on error."""
    url = _base_url() + path
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Accept": "application/json",
        "User-Agent": f"millionsend-python/{VERSION}",
    }
    data = None
    if body is not None and method in _JSON_METHODS:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body)
    # Idempotency is POST-only on the wire; sending it elsewhere is a no-op.
    if idempotency_key and method == "POST":
        headers["Idempotency-Key"] = idempotency_key

    try:
        resp = requests.request(
            method, url, headers=headers, data=data, params=query, timeout=_config("timeout") or DEFAULT_TIMEOUT
        )
    except requests.exceptions.RequestException as exc:
        raise MillionSendError(
            str(exc) or "request failed", code="application_error", status_code=None
        ) from exc

    text = resp.text
    parsed: Any = None
    if text:
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = text

    if not 200 <= resp.status_code < 300:
        raise_api_error(resp.status_code, parsed)
    return _wrap(parsed)
