"""Request wiring, config, and error parsing over the mocked HTTP layer."""

import pytest
import requests

import millionsend
import millionsend._client as _client
from millionsend import (
    MillionSendError,
    MissingApiKeyError,
    NotFoundError,
    ValidationError,
)


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.setattr(millionsend, "api_key", None)
    monkeypatch.delenv("MILLIONSEND_API_KEY", raising=False)
    with pytest.raises(MissingApiKeyError):
        millionsend.Emails.get("e1")


def test_api_key_from_env(monkeypatch):
    monkeypatch.setattr(millionsend, "api_key", None)
    monkeypatch.setenv("MILLIONSEND_API_KEY", "ms_env")

    calls = []

    def fake(method, url, headers=None, **kw):
        calls.append(headers["Authorization"])

        class R:
            status_code = 200
            text = "{}"

        return R()

    monkeypatch.setattr(millionsend, "base_url", "https://api.test")
    monkeypatch.setattr(_client.requests, "request", fake)
    millionsend.Emails.get("e1")
    assert calls[0] == "Bearer ms_env"


def test_base_url_default_and_trailing_slash(monkeypatch):
    monkeypatch.setattr(millionsend, "api_key", "ms_test")
    monkeypatch.setattr(millionsend, "base_url", "https://api.test/")
    seen = {}

    def fake(method, url, headers=None, **kw):
        seen["url"] = url

        class R:
            status_code = 200
            text = "{}"

        return R()

    monkeypatch.setattr(_client.requests, "request", fake)
    millionsend.Emails.get("e1")
    assert seen["url"] == "https://api.test/emails/e1"


def test_auth_accept_user_agent_and_content_type(http):
    millionsend.Emails.send({"from": "a@x.dev", "to": "b@x.dev", "subject": "s", "html": "<p>h</p>"})
    h = http.calls[0]["headers"]
    assert h["Authorization"] == "Bearer ms_test"
    assert h["Accept"] == "application/json"
    assert h["Content-Type"] == "application/json"
    assert h["User-Agent"].startswith("millionsend-python/")


def test_no_content_type_on_get(http):
    millionsend.Emails.get("e1")
    assert "Content-Type" not in http.calls[0]["headers"]


def test_idempotency_key_on_post_only(http):
    millionsend.Emails.send(
        {"from": "a@x.dev", "to": "b@x.dev", "subject": "s", "text": "t"},
        idempotency_key="key-123",
    )
    assert http.calls[0]["headers"]["Idempotency-Key"] == "key-123"


def test_returns_wrapped_dict_with_attribute_access(http):
    http.body = {"id": "abc", "data": [{"id": "1"}]}
    res = millionsend.Emails.send({"from": "a@x.dev", "to": "b@x.dev", "subject": "s", "text": "t"})
    assert res["id"] == "abc"
    assert res.id == "abc"
    assert res.data[0].id == "1"


def test_error_parsed_into_typed_exception(http):
    http.status = 422
    http.body = {"statusCode": 422, "name": "validation_error", "message": "bad"}
    with pytest.raises(ValidationError) as ei:
        millionsend.Emails.send({"from": "a@x.dev", "to": "b@x.dev", "subject": "s", "text": "t"})
    assert ei.value.code == "validation_error"
    assert ei.value.message == "bad"
    assert ei.value.status_code == 422
    assert isinstance(ei.value, MillionSendError)


def test_not_found_maps_to_subclass(http):
    http.status = 404
    http.body = {"statusCode": 404, "name": "not_found", "message": "nope"}
    with pytest.raises(NotFoundError):
        millionsend.Emails.get("missing")


def test_non_canonical_body_falls_back(http):
    http.status = 500
    http.body = "gateway boom"
    with pytest.raises(MillionSendError) as ei:
        millionsend.Emails.get("e1")
    assert ei.value.code == "application_error"
    assert ei.value.status_code == 500
    assert ei.value.message == "Request failed with status 500"


def test_transport_failure_has_status_code_none(http):
    http.exc = requests.exceptions.ConnectionError("ECONNREFUSED")
    with pytest.raises(MillionSendError) as ei:
        millionsend.Emails.get("e1")
    assert ei.value.status_code is None
    assert "ECONNREFUSED" in ei.value.message
    # transport failures are the base error, never a typed API subclass
    assert type(ei.value) is MillionSendError
