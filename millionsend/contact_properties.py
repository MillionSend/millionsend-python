"""Custom contact property definitions (``key`` + ``type`` string|number|date)."""

from typing import Any, Dict, Optional

from ._client import list_query, path_id, request, split_id


class ContactProperties:
    @classmethod
    def create(cls, params: Dict[str, Any]) -> Any:
        """POST /contact-properties — key, type (string|number|date), fallback_value?

        ``date`` is a MillionSend extension. Its values and ``fallback_value`` must read as an
        ISO 8601 date (midnight UTC) or date-time (UTC when it names no zone), or as Unix time in
        seconds or milliseconds from 2000 to 2100, or the write raises ``ValidationError`` (422).
        """
        return request("POST", "/contact-properties", body=params)

    @classmethod
    def get(cls, property_id: str) -> Any:
        return request("GET", f"/contact-properties/{path_id(property_id)}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        return request("GET", "/contact-properties", query=list_query(limit, after, before))

    @classmethod
    def update(cls, params: Dict[str, Any]) -> Any:
        """PATCH /contact-properties/{id} — ``{"id": ..., "fallback_value": ...}`` (None clears)."""
        property_id, body = split_id(params, "id")
        return request("PATCH", f"/contact-properties/{property_id}", body=body)

    @classmethod
    def remove(cls, property_id: str) -> Any:
        return request("DELETE", f"/contact-properties/{path_id(property_id)}")
