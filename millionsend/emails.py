"""Emails and batch sending. Both accept a POST-only Idempotency-Key."""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ._client import request


class Emails:
    @classmethod
    def send(cls, params: Dict[str, Any], idempotency_key: Optional[str] = None) -> Any:
        """POST /emails — supports an Idempotency-Key."""
        return request("POST", "/emails", body=params, idempotency_key=idempotency_key)

    @classmethod
    def get(cls, email_id: str) -> Any:
        """GET /emails/{id}"""
        return request("GET", f"/emails/{quote(str(email_id), safe='')}")

    @classmethod
    def cancel(cls, email_id: str) -> Any:
        """POST /emails/{id}/cancel — scheduled, unsent emails only."""
        return request("POST", f"/emails/{quote(str(email_id), safe='')}/cancel")


class Batch:
    @classmethod
    def send(cls, params: List[Dict[str, Any]], idempotency_key: Optional[str] = None) -> Any:
        """POST /emails/batch — 1..100 emails in one call; supports an Idempotency-Key."""
        return request("POST", "/emails/batch", body=params, idempotency_key=idempotency_key)
