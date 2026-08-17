"""Dynamic segments — a saved filter over the team's contacts (MillionSend
extension, no Resend equivalent). ``get`` returns a live ``contact_count``."""

from typing import Any, Dict, Optional
from urllib.parse import quote

from ._client import list_query, request


def _q(value: Any) -> str:
    return quote(str(value), safe="")


class Segments:
    @classmethod
    def create(cls, params: Dict[str, Any]) -> Any:
        return request(
            "POST",
            "/segments",
            body={"name": params["name"], "filter": params["filter"]},
        )

    @classmethod
    def get(cls, segment_id: str) -> Any:
        return request("GET", f"/segments/{_q(segment_id)}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        return request("GET", "/segments", query=list_query(limit, after, before))

    @classmethod
    def update(cls, segment_id: str, params: Dict[str, Any]) -> Any:
        body = {k: params[k] for k in ("name", "filter") if k in params}
        return request("PATCH", f"/segments/{_q(segment_id)}", body=body)

    @classmethod
    def remove(cls, segment_id: str) -> Any:
        return request("DELETE", f"/segments/{_q(segment_id)}")
