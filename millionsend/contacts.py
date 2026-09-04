"""Contacts — team-global, addressable by id OR email (email wins).

Params are already snake_case (the wire casing). ``None`` in an update clears a
field; omit the key to leave it unchanged.
"""

from typing import Any, Dict, List, Optional

from ._client import Options, list_query, path_id, request, request_options


def _key(contact_id: Optional[str], email: Optional[str]) -> str:
    value = email if email is not None else (contact_id if contact_id is not None else "")
    return path_id(value)


def _params_key(params: Dict[str, Any]) -> str:
    """resend-python addresses a contact by ``id`` (or ``contact_id``) or ``email``."""
    return _key(params.get("contact_id", params.get("id")), params.get("email"))


class ContactTopics:
    @classmethod
    def list(
        cls, contact_id: Optional[str] = None, email: Optional[str] = None, id: Optional[str] = None
    ) -> Any:
        """GET /contacts/{idOrEmail}/topics — every team topic with the contact's effective
        ``subscription``; ``explicit`` is False when it is the topic default.
        """
        return request("GET", f"/contacts/{_key(contact_id or id, email)}/topics")

    @classmethod
    def update(cls, params: Dict[str, Any]) -> Any:
        """PATCH /contacts/{idOrEmail}/topics — body is the bare topics array."""
        return request("PATCH", f"/contacts/{_params_key(params)}/topics", body=params["topics"])


class ContactSegments:
    @classmethod
    def add(cls, params: Dict[str, Any]) -> Any:
        """POST /contacts/{idOrEmail}/segments/{segmentId}"""
        return request("POST", cls._path(params))

    @classmethod
    def remove(cls, params: Dict[str, Any]) -> Any:
        """DELETE /contacts/{idOrEmail}/segments/{segmentId}"""
        return request("DELETE", cls._path(params))

    @staticmethod
    def _path(params: Dict[str, Any]) -> str:
        return f"/contacts/{_params_key(params)}/segments/{path_id(params['segment_id'])}"


class ContactBatch:
    @classmethod
    def create(
        cls,
        params: List[Dict[str, Any]],
        options: Options = None,
        on_conflict: Optional[str] = None,
        batch_validation: Optional[str] = None,
    ) -> Any:
        """POST /contacts/batch — 1..1000 contacts (MillionSend extension).

        ``on_conflict`` is ``"error"`` (default), ``"skip"`` or ``"upsert"`` for an
        email that already belongs to a contact. ``batch_validation`` is
        ``"strict"`` (default) or ``"permissive"`` (failures listed in ``errors``).
        """
        query = {"on_conflict": on_conflict} if on_conflict is not None else None
        return request(
            "POST",
            "/contacts/batch",
            body=params,
            query=query,
            **request_options(options, batch_validation=batch_validation),
        )


class Contacts:
    # Mirrors Resend's nesting: Contacts.Topics.update(...), Contacts.Segments.add(...).
    Topics = ContactTopics
    Segments = ContactSegments
    Batch = ContactBatch

    @classmethod
    def create(cls, params: Dict[str, Any]) -> Any:
        return request("POST", "/contacts", body=params)

    @classmethod
    def get(
        cls, contact_id: Optional[str] = None, email: Optional[str] = None, id: Optional[str] = None
    ) -> Any:
        """GET /contacts/{idOrEmail} — ``id`` is resend-python's name for ``contact_id``."""
        return request("GET", f"/contacts/{_key(contact_id or id, email)}")

    @classmethod
    def update(cls, params: Dict[str, Any]) -> Any:
        body = dict(params)
        contact_id = body.pop("id", None)
        email = body.pop("email", None)
        return request("PATCH", f"/contacts/{_key(contact_id, email)}", body=body)

    @classmethod
    def remove(
        cls, contact_id: Optional[str] = None, email: Optional[str] = None, id: Optional[str] = None
    ) -> Any:
        return request("DELETE", f"/contacts/{_key(contact_id or id, email)}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
        segment_id: Optional[str] = None,
    ) -> Any:
        """GET /contacts, or GET /segments/{segment_id}/contacts when ``segment_id`` is given."""
        query = list_query(limit, after, before) or {}
        segment_id = query.pop("segment_id", segment_id)
        path = f"/segments/{path_id(segment_id)}/contacts" if segment_id else "/contacts"
        return request("GET", path, query=query or None)
