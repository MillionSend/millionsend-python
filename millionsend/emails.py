"""Emails and batch sending.

``options`` is resend-python's ``{"idempotency_key": ..., "batch_validation": ...}``
dict; the same values are also accepted as keywords. Bodies are passed through
as given — every REST field (``tags``, ``attachments``, ``headers``,
``topic_id``, ``template``, …) reaches the wire unchanged.
"""

from typing import Any, Dict, List, Optional

from ._client import Options, list_query, path_id, request, request_options, split_id
from .receiving import Receiving


class Emails:
    # Mirrors resend-python: Emails.Receiving.list(), Emails.Receiving.Attachments.get(...).
    Receiving = Receiving

    @classmethod
    def send(
        cls,
        params: Dict[str, Any],
        options: Options = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """POST /emails — supports an Idempotency-Key.

        ``from`` may be an inbox's address on the shared domain while its ``sending_mode`` is
        ``"open"``: that exact address (no +tag), with no display name or the inbox's
        ``from_name``, no ``reply_to``, ``attachments``, ``headers`` or ``scheduled_at``, and at
        most 10 distinct recipients across to, cc and bcc.
        """
        return request("POST", "/emails", body=params, **request_options(options, idempotency_key))

    @classmethod
    def get(cls, email_id: str) -> Any:
        """GET /emails/{id}"""
        return request("GET", f"/emails/{path_id(email_id)}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        """GET /emails"""
        return request("GET", "/emails", query=list_query(limit, after, before))

    @classmethod
    def update(cls, params: Dict[str, Any]) -> Any:
        """PATCH /emails/{id} — ``{"id": ..., "scheduled_at": ...}``; scheduled, unsent emails only."""
        email_id, body = split_id(params, "id")
        return request("PATCH", f"/emails/{email_id}", body=body)

    @classmethod
    def get_insights(cls, email_id: str) -> Any:
        """GET /emails/{id}/insights — 404 until insights exist for the email."""
        return request("GET", f"/emails/{path_id(email_id)}/insights")

    @classmethod
    def cancel(cls, email_id: str) -> Any:
        """POST /emails/{id}/cancel — scheduled, unsent emails only."""
        return request("POST", f"/emails/{path_id(email_id)}/cancel")

    @classmethod
    def remove(cls, email_id: str) -> Any:
        """DELETE /emails/{id}"""
        return request("DELETE", f"/emails/{path_id(email_id)}")


class Batch:
    @classmethod
    def send(
        cls,
        params: List[Dict[str, Any]],
        options: Options = None,
        idempotency_key: Optional[str] = None,
        batch_validation: Optional[str] = None,
    ) -> Any:
        """POST /emails/batch — 1..100 emails in one call.

        ``batch_validation`` is ``"strict"`` (default: any invalid item rejects the
        batch) or ``"permissive"`` (valid items are sent, the rest come back in ``errors``).
        Items never send from the shared domain: such an item is refused as ``inbox_send_policy``.
        """
        return request(
            "POST",
            "/emails/batch",
            body=params,
            **request_options(options, idempotency_key, batch_validation),
        )
