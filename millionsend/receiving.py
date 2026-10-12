"""Received mail — ``Emails.Receiving``, mirroring resend-python, plus MillionSend's
server-side reply, forward, erase and long-poll.

Everything in a received email was written by its sender: show its ``html`` only in
a sandbox, and give an LLM the ``extracted_text`` rather than the ``html``.
"""

from typing import Any, Dict, Optional, Union

from ._client import Options, list_query, path_id, request, request_options, request_outcome


def _path(email_id: str) -> str:
    return f"/emails/receiving/{path_id(email_id)}"


class ReceivingAttachments:
    @classmethod
    def list(
        cls,
        email_id: str,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        """GET /emails/receiving/{email_id}/attachments — every attachment unless ``limit`` is given,
        each with a signed ``download_url`` valid for one hour."""
        return request("GET", f"{_path(email_id)}/attachments", query=list_query(limit, after, before))

    @classmethod
    def get(cls, email_id: str, attachment_id: str) -> Any:
        """GET /emails/receiving/{email_id}/attachments/{id}"""
        return request("GET", f"{_path(email_id)}/attachments/{path_id(attachment_id)}")


class Receiving:
    Attachments = ReceivingAttachments

    @classmethod
    def list(
        cls,
        limit: Union[int, Dict[str, Any], None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        **filters: Any,
    ) -> Any:
        """GET /emails/receiving — newest first.

        Filters (wire names): ``wait`` (long-poll up to 50 s for a match; the answer then also
        carries ``held``), ``since``, ``inbox_id``, ``to``, ``from``, ``subject_contains``,
        ``unread``, ``include_quarantined``, ``quarantined``. ``from`` is a Python keyword, so
        pass it in the options dict: ``Receiving.list({"from": "example.com", "wait": 30})``.
        """
        return request("GET", "/emails/receiving", query=list_query(limit, after, before, **filters))

    @classmethod
    def get(
        cls,
        email_id: str,
        params: Optional[Dict[str, Any]] = None,
        html_format: Optional[str] = None,
    ) -> Any:
        """GET /emails/receiving/{id} — ``html_format`` is ``"data_uri"`` (default) or ``"cid"``,
        as a keyword or in resend-python's params dict."""
        return request("GET", _path(email_id), query=list_query(params, html_format=html_format))

    @classmethod
    def reply(
        cls,
        email_id: str,
        params: Dict[str, Any],
        options: Options = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """POST /emails/receiving/{id}/reply — text/html, subject, cc, bcc, reply_all,
        requires_approval, from, inbox_id.

        Returns ``{"kind": "sent", "email": {...}}``, or ``{"kind": "draft", "draft": {...}}``
        when the inbox's rules hold the reply for a person to approve (HTTP 202).
        """
        key = request_options(options, idempotency_key)["idempotency_key"]
        return request_outcome(f"{_path(email_id)}/reply", body=params, idempotency_key=key)

    @classmethod
    def forward(
        cls,
        email_id: str,
        params: Dict[str, Any],
        options: Options = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """POST /emails/receiving/{id}/forward — to, cc, bcc, text/html note, subject,
        requires_approval, from, inbox_id, mode (``"inline"`` or ``"attachment"``).

        Same outcome shape as :meth:`reply`.
        """
        key = request_options(options, idempotency_key)["idempotency_key"]
        return request_outcome(f"{_path(email_id)}/forward", body=params, idempotency_key=key)

    @classmethod
    def remove(cls, email_id: str) -> Any:
        """DELETE /emails/receiving/{id} — erases the message now instead of at the end of retention."""
        return request("DELETE", _path(email_id))
