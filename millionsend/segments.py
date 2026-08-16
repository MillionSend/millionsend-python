"""Dynamic segments — a saved filter over an audience's contacts (MillionSend
extension, no Resend equivalent). Path is ``/segments2``; ``get`` returns a live
``contact_count``."""

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
            "/segments2",
            body={
                "name": params["name"],
                "audience_id": params["audience_id"],
                "filter": params["filter"],
            },
        )

    @classmethod
    def get(cls, segment_id: str) -> Any:
        return request("GET", f"/segments2/{_q(segment_id)}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        return request("GET", "/segments2", query=list_query(limit, after, before))

    @classmethod
    def update(cls, segment_id: str, params: Dict[str, Any]) -> Any:
        body = {k: params[k] for k in ("name", "filter") if k in params}
        return request("PATCH", f"/segments2/{_q(segment_id)}", body=body)

    @classmethod
    def remove(cls, segment_id: str) -> Any:
        return request("DELETE", f"/segments2/{_q(segment_id)}")
