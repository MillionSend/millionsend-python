"""Contacts — team-global, addressable by id OR email (email wins).

Params are already snake_case (the wire casing). ``None`` in an update clears a
field; omit the key to leave it unchanged.
"""

from typing import Any, Dict, Optional
from urllib.parse import quote

from ._client import list_query, request


def _key(contact_id: Optional[str], email: Optional[str]) -> str:
    value = email if email is not None else (contact_id if contact_id is not None else "")
    return quote(str(value), safe="")


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
        return request("POST", "/contacts", body=params)

    @classmethod
    def get(cls, contact_id: Optional[str] = None, email: Optional[str] = None) -> Any:
        return request("GET", f"/contacts/{_key(contact_id, email)}")

    @classmethod
    def update(cls, params: Dict[str, Any]) -> Any:
        body = dict(params)
        contact_id = body.pop("id", None)
        email = body.pop("email", None)
        return request("PATCH", f"/contacts/{_key(contact_id, email)}", body=body)

    @classmethod
    def remove(cls, contact_id: Optional[str] = None, email: Optional[str] = None) -> Any:
        return request("DELETE", f"/contacts/{_key(contact_id, email)}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        return request("GET", "/contacts", query=list_query(limit, after, before))
