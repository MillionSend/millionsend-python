"""Broadcasts — draft, schedule, send, and cancel campaigns.

Targeting is an optional ``segment_id`` and/or ``topic_id`` on create/update;
neither set means every contact of the team.
"""

from typing import Any, Dict, Optional

from ._client import list_query, path_id, request


class Broadcasts:
    @classmethod
    def create(cls, params: Dict[str, Any]) -> Any:
        return request("POST", "/broadcasts", body=params)

    @classmethod
    def get(cls, broadcast_id: str) -> Any:
        return request("GET", f"/broadcasts/{path_id(broadcast_id)}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        return request("GET", "/broadcasts", query=list_query(limit, after, before))

    @classmethod
    def update(cls, broadcast_id: str, params: Dict[str, Any]) -> Any:
        """PATCH /broadcasts/{id} — draft only."""
        return request("PATCH", f"/broadcasts/{path_id(broadcast_id)}", body=params)

    @classmethod
    def remove(cls, broadcast_id: str) -> Any:
        """DELETE /broadcasts/{id} — draft only."""
        return request("DELETE", f"/broadcasts/{path_id(broadcast_id)}")

    @classmethod
    def send(cls, broadcast_id: str, scheduled_at: Optional[str] = None) -> Any:
        """POST /broadcasts/{id}/send — omit scheduled_at to send now."""
        body = {"scheduled_at": scheduled_at} if scheduled_at is not None else {}
        return request("POST", f"/broadcasts/{path_id(broadcast_id)}/send", body=body)

    @classmethod
    def cancel(cls, broadcast_id: str) -> Any:
        """POST /broadcasts/{id}/cancel — scheduled only."""
        return request("POST", f"/broadcasts/{path_id(broadcast_id)}/cancel")
