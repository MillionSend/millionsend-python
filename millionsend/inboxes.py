"""Inboxes: an address that receives mail, read by an agent (``kind: "agent"``, the
default) or by people (``kind: "human"``).

Threads, labels and drafts mirror Resend's Inboxes beta; ``Safety``, ``Codes``,
``Quarantine`` and ``Drafts.reject`` are MillionSend extensions. Params are the
wire's snake_case, passed through as given.
"""

from typing import Any, Dict, Optional, Union

from ._client import Options, list_query, path_id, request, request_options, request_outcome


def _path(inbox_id: str, *segments: str) -> str:
    """``/inboxes/{inbox_id}/{segments…}`` with every id percent-encoded."""
    return "/".join(["/inboxes", path_id(inbox_id), *(path_id(s) for s in segments)])


class InboxSafety:
    @classmethod
    def get(cls, inbox_id: str) -> Any:
        """GET /inboxes/{id}/safety — who can write in and what the inbox may send."""
        return request("GET", _path(inbox_id, "safety"))

    @classmethod
    def update(cls, inbox_id: str, params: Dict[str, Any]) -> Any:
        """PATCH /inboxes/{id}/safety — omitted fields keep their value; inbox-scoped keys get a 403."""
        return request("PATCH", _path(inbox_id, "safety"), body=params)


class InboxCodes:
    @classmethod
    def latest(cls, inbox_id: str, params: Optional[Dict[str, Any]] = None, **query: Any) -> Any:
        """GET /inboxes/{id}/codes/latest — the newest delivered verification code or sign-in link.

        Query: ``from`` (an address, or a domain covering its subdomains; pass it in ``params``),
        ``wait`` (long-poll up to 50 s), ``max_age`` (seconds, 60..86400).
        """
        return request("GET", _path(inbox_id, "codes", "latest"), query=list_query(params, **query))


class InboxQuarantine:
    @classmethod
    def list(
        cls,
        inbox_id: str,
        limit: Union[int, Dict[str, Any], None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        """GET /inboxes/{id}/quarantine — held mail, newest first; full-access team keys only."""
        return request("GET", _path(inbox_id, "quarantine"), query=list_query(limit, after, before))

    @classmethod
    def release(cls, inbox_id: str, email_id: str, trust_sender: Optional[bool] = None) -> Any:
        """POST /inboxes/{id}/quarantine/{email_id}/release — ``trust_sender`` also allowlists the sender."""
        body = {"trust_sender": trust_sender} if trust_sender is not None else {}
        return request("POST", _path(inbox_id, "quarantine", email_id, "release"), body=body)


class InboxLabels:
    @classmethod
    def list(cls, inbox_id: str) -> Any:
        """GET /inboxes/{id}/labels — every label, oldest first (not paginated)."""
        return request("GET", _path(inbox_id, "labels"))

    @classmethod
    def create(cls, inbox_id: str, params: Dict[str, Any]) -> Any:
        """POST /inboxes/{id}/labels — name, color? (``#RRGGBB``; random when omitted)."""
        return request("POST", _path(inbox_id, "labels"), body=params)

    @classmethod
    def update(cls, inbox_id: str, label_id: str, params: Dict[str, Any]) -> Any:
        return request("PATCH", _path(inbox_id, "labels", label_id), body=params)

    @classmethod
    def remove(cls, inbox_id: str, label_id: str) -> Any:
        """DELETE /inboxes/{id}/labels/{label_id} — also removes it from every thread."""
        return request("DELETE", _path(inbox_id, "labels", label_id))


class InboxThreadEmails:
    @classmethod
    def list(
        cls,
        inbox_id: str,
        thread_id: str,
        limit: Union[int, Dict[str, Any], None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        include_quarantined: Optional[bool] = None,
    ) -> Any:
        """GET /inboxes/{id}/threads/{thread_id}/emails — oldest first; ``after`` pages toward newer.

        ``include_quarantined=True`` adds held messages (full-access team keys only).
        """
        query = list_query(limit, after, before, include_quarantined=include_quarantined)
        return request("GET", _path(inbox_id, "threads", thread_id, "emails"), query=query)

    @classmethod
    def get(
        cls, inbox_id: str, thread_id: str, email_id: str, include_quarantined: Optional[bool] = None
    ) -> Any:
        """GET …/emails/{email_id} — a quarantined message needs ``include_quarantined=True`` and a
        full-access team key; otherwise it raises ``EmailQuarantinedError``."""
        query = list_query(include_quarantined=include_quarantined)
        return request("GET", _path(inbox_id, "threads", thread_id, "emails", email_id), query=query)

    @classmethod
    def reply(
        cls,
        inbox_id: str,
        thread_id: str,
        email_id: str,
        params: Dict[str, Any],
        options: Options = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """POST …/emails/{email_id}/reply — html/text, cc, bcc, subject, reply_all, requires_approval.

        Returns ``{"kind": "sent", "email": {...}}``, or ``{"kind": "draft", "draft": {...}}``
        when the inbox's rules hold the reply for a person to approve (HTTP 202).
        """
        key = request_options(options, idempotency_key)["idempotency_key"]
        path = _path(inbox_id, "threads", thread_id, "emails", email_id, "reply")
        return request_outcome(path, body=params, idempotency_key=key)

    @classmethod
    def forward(
        cls,
        inbox_id: str,
        thread_id: str,
        email_id: str,
        params: Dict[str, Any],
        options: Options = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """POST …/emails/{email_id}/forward — to, cc, bcc, html/text note, subject, requires_approval.

        Same outcome shape as :meth:`reply`.
        """
        key = request_options(options, idempotency_key)["idempotency_key"]
        path = _path(inbox_id, "threads", thread_id, "emails", email_id, "forward")
        return request_outcome(path, body=params, idempotency_key=key)


class InboxThreads:
    Emails = InboxThreadEmails

    @classmethod
    def list(
        cls,
        inbox_id: str,
        limit: Union[int, Dict[str, Any], None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        **filters: Any,
    ) -> Any:
        """GET /inboxes/{id}/threads — most recently active first.

        Filters: ``folders`` and ``labels`` (lists, sent comma-separated), ``read``,
        ``include_quarantined``.
        """
        return request("GET", _path(inbox_id, "threads"), query=list_query(limit, after, before, **filters))

    @classmethod
    def search(
        cls,
        inbox_id: str,
        limit: Union[int, Dict[str, Any], None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        **filters: Any,
    ) -> Any:
        """GET /inboxes/{id}/threads/search — subject, sender and recipients.

        Filters: those of :meth:`list` plus ``query``, ``from``/``to``/``cc``/``bcc`` (lists),
        ``has_attachment``, ``start_date``, ``end_date``. Pass ``from`` in the options dict.
        """
        return request(
            "GET", _path(inbox_id, "threads", "search"), query=list_query(limit, after, before, **filters)
        )

    @classmethod
    def get(cls, inbox_id: str, thread_id: str) -> Any:
        return request("GET", _path(inbox_id, "threads", thread_id))

    @classmethod
    def update(cls, inbox_id: str, thread_id: str, params: Dict[str, Any]) -> Any:
        """PATCH /inboxes/{id}/threads/{thread_id} — read, folder, label_id."""
        return request("PATCH", _path(inbox_id, "threads", thread_id), body=params)

    @classmethod
    def remove(cls, inbox_id: str, thread_id: str) -> Any:
        """DELETE /inboxes/{id}/threads/{thread_id} — moves it to trash, purged after 30 days."""
        return request("DELETE", _path(inbox_id, "threads", thread_id))


class InboxDrafts:
    @classmethod
    def list(
        cls,
        inbox_id: str,
        limit: Union[int, Dict[str, Any], None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        """GET /inboxes/{id}/drafts — unsent drafts, most recently updated first."""
        return request("GET", _path(inbox_id, "drafts"), query=list_query(limit, after, before))

    @classmethod
    def create(cls, inbox_id: str, params: Dict[str, Any]) -> Any:
        """POST /inboxes/{id}/drafts — to, cc, bcc, subject, html, text, and for a reply draft both
        thread_id and reply_to_email_id. A second reply draft for the same email returns the first."""
        return request("POST", _path(inbox_id, "drafts"), body=params)

    @classmethod
    def get(cls, inbox_id: str, draft_id: str) -> Any:
        return request("GET", _path(inbox_id, "drafts", draft_id))

    @classmethod
    def update(cls, inbox_id: str, draft_id: str, params: Dict[str, Any]) -> Any:
        """PATCH /inboxes/{id}/drafts/{draft_id} — ``None`` clears a field."""
        return request("PATCH", _path(inbox_id, "drafts", draft_id), body=params)

    @classmethod
    def remove(cls, inbox_id: str, draft_id: str) -> Any:
        return request("DELETE", _path(inbox_id, "drafts", draft_id))

    @classmethod
    def send(
        cls,
        inbox_id: str,
        draft_id: str,
        options: Options = None,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        """POST /inboxes/{id}/drafts/{draft_id}/send — no body.

        Returns ``{"kind": "sent", "email": {object, id, thread_id, email_id}}``, or
        ``{"kind": "draft", "draft": {...}}`` when the rules hold it for approval. A key restricted
        to the inbox cannot send a draft that waits for approval (``approval_required``).
        """
        key = request_options(options, idempotency_key)["idempotency_key"]
        return request_outcome(_path(inbox_id, "drafts", draft_id, "send"), idempotency_key=key)

    @classmethod
    def reject(cls, inbox_id: str, draft_id: str) -> Any:
        """POST /inboxes/{id}/drafts/{draft_id}/reject — approvers only."""
        return request("POST", _path(inbox_id, "drafts", draft_id, "reject"))


class Inboxes:
    Safety = InboxSafety
    Codes = InboxCodes
    Quarantine = InboxQuarantine
    Labels = InboxLabels
    Threads = InboxThreads
    Drafts = InboxDrafts

    @classmethod
    def create(cls, params: Optional[Dict[str, Any]] = None) -> Any:
        """POST /inboxes — email_address?, name?, from_name?, forwarding?, kind? (default
        ``"agent"``), expires_in? (``"24h"``, ``"7d"``, or None for never), safety? (partial).

        Without ``email_address`` the inbox gets a random address on the instance's shared domain.
        """
        return request("POST", "/inboxes", body=params or {})

    @classmethod
    def list(
        cls,
        limit: Union[int, Dict[str, Any], None] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        kind: Optional[str] = None,
    ) -> Any:
        """GET /inboxes — newest first; ``kind`` is ``"agent"`` or ``"human"``."""
        return request("GET", "/inboxes", query=list_query(limit, after, before, kind=kind))

    @classmethod
    def get(cls, inbox_id: str) -> Any:
        """GET /inboxes/{id_or_email} — by id or by address."""
        return request("GET", _path(inbox_id))

    @classmethod
    def update(cls, inbox_id: str, params: Dict[str, Any]) -> Any:
        """PATCH /inboxes/{id} — name, from_name (``""`` removes it), expires_in."""
        return request("PATCH", _path(inbox_id), body=params)

    @classmethod
    def remove(cls, inbox_id: str) -> Any:
        """DELETE /inboxes/{id} — removes its threads, drafts and labels, and revokes its keys."""
        return request("DELETE", _path(inbox_id))
