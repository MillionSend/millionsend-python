"""End-to-end smoke test against a real MillionSend instance.

Opt-in: runs only when MILLIONSEND_API_KEY is set (and, if not localhost:3001,
MILLIONSEND_BASE_URL). It exercises the audience + contact lifecycle, which needs
no verified domain. Sending is not asserted because it needs a verified sender
domain.

    MILLIONSEND_API_KEY=ms_... MILLIONSEND_BASE_URL=http://localhost:3001 \
        pytest -k e2e
"""

import os
import time

import pytest

import millionsend
from millionsend import NotFoundError

pytestmark = pytest.mark.skipif(
    not os.environ.get("MILLIONSEND_API_KEY"),
    reason="set MILLIONSEND_API_KEY to run the e2e lifecycle test",
)


def test_audience_and_contact_lifecycle():
    stamp = int(time.time() * 1000)
    audience = millionsend.Audiences.create({"name": f"sdk-e2e-{stamp}"})
    audience_id = audience.id
    assert audience_id
    try:
        email = f"sdk-e2e-{stamp}@example.com"
        millionsend.Contacts.create({"audience_id": audience_id, "email": email, "first_name": "Ada"})

        fetched = millionsend.Contacts.get(audience_id=audience_id, email=email)
        assert fetched.email == email
        assert fetched.first_name == "Ada"

        millionsend.Contacts.update({"audience_id": audience_id, "email": email, "unsubscribed": True})

        removed = millionsend.Contacts.remove(audience_id=audience_id, email=email)
        assert removed.deleted is True
    finally:
        millionsend.Audiences.remove(audience_id)


def test_not_found_raises():
    with pytest.raises(NotFoundError):
        millionsend.Contacts.get(email="does-not-exist@example.com")
