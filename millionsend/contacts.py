"""Contacts — addressable by id OR email (email wins), audience-scoped or top-level.

Params are already snake_case (the wire casing). ``None`` in an update clears a
field; omit the key to leave it unchanged.
"""

from typing import Any, Dict, Optional
from urllib.parse import quote

from ._client import list_query, request


def _q(value: Any) -> str:
    return quote(str(value), safe="")


def _key(contact_id: Optional[str], email: Optional[str]) -> str:
    return _q(email if email is not None else (contact_id if contact_id is not None else ""))


def _path(
    contact_id: Optional[str] = None,
    email: Optional[str] = None,
    audience_id: Optional[str] = None,
) -> str:
    key = _key(contact_id, email)
    if audience_id:
        return f"/audiences/{_q(audience_id)}/contacts/{key}"
    return f"/contacts/{key}"


class ContactTopics:
    @classmethod
    def update(cls, params: Dict[str, Any]) -> Any:
        """PATCH /contacts/{idOrEmail}/topics — body is the bare topics array."""
        key = _key(params.get("id"), params.get("email"))
        return request("PATCH", f"/contacts/{key}/topics", body=params["topics"])


class Contacts:
    # Mirrors Resend's ``contacts.topics.update`` nesting: Contacts.Topics.update(...).
    Topics = ContactTopics

    @classmethod
    def create(cls, params: Dict[str, Any]) -> Any:
        body = dict(params)
        audience_id = body.pop("audience_id", None)
        path = f"/audiences/{_q(audience_id)}/contacts" if audience_id else "/contacts"
        return request("POST", path, body=body)

    @classmethod
    def get(
        cls,
        contact_id: Optional[str] = None,
        email: Optional[str] = None,
        audience_id: Optional[str] = None,
    ) -> Any:
        return request("GET", _path(contact_id, email, audience_id))

    @classmethod
    def update(cls, params: Dict[str, Any]) -> Any:
        body = dict(params)
        contact_id = body.pop("id", None)
        email = body.pop("email", None)
        audience_id = body.pop("audience_id", None)
        return request("PATCH", _path(contact_id, email, audience_id), body=body)

    @classmethod
    def remove(
        cls,
        contact_id: Optional[str] = None,
        email: Optional[str] = None,
        audience_id: Optional[str] = None,
    ) -> Any:
        return request("DELETE", _path(contact_id, email, audience_id))

    @classmethod
    def list(
        cls,
        audience_id: Optional[str] = None,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        path = f"/audiences/{_q(audience_id)}/contacts" if audience_id else "/contacts"
        return request("GET", path, query=list_query(limit, after, before))
