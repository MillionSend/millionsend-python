"""Subscription topics — granular unsubscribe categories. GET /topics is a bare
``{"data": [...]}`` (unpaginated)."""

from typing import Any, Dict
from urllib.parse import quote

from ._client import request


class Topics:
    @classmethod
    def create(cls, params: Dict[str, Any]) -> Any:
        return request("POST", "/topics", body=params)

    @classmethod
    def get(cls, topic_id: str) -> Any:
        return request("GET", f"/topics/{quote(str(topic_id), safe='')}")

    @classmethod
    def list(cls) -> Any:
        return request("GET", "/topics")

    @classmethod
    def remove(cls, topic_id: str) -> Any:
        return request("DELETE", f"/topics/{quote(str(topic_id), safe='')}")
