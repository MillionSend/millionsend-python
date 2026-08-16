"""Audiences — named contact lists (Resend-compatible)."""

from typing import Any, Dict, Optional
from urllib.parse import quote

from ._client import list_query, request


class Audiences:
    @classmethod
    def create(cls, params: Dict[str, Any]) -> Any:
        return request("POST", "/audiences", body={"name": params["name"]})

    @classmethod
    def get(cls, audience_id: str) -> Any:
        return request("GET", f"/audiences/{quote(str(audience_id), safe='')}")

    @classmethod
    def list(
        cls,
        limit: Optional[int] = None,
        after: Optional[str] = None,
        before: Optional[str] = None,
    ) -> Any:
        return request("GET", "/audiences", query=list_query(limit, after, before))

    @classmethod
    def remove(cls, audience_id: str) -> Any:
        return request("DELETE", f"/audiences/{quote(str(audience_id), safe='')}")
