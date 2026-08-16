"""Official Python SDK for MillionSend — a self-hostable, Resend-compatible email API.

Configure once at the module level, then call resource classes::

    import millionsend

    millionsend.api_key = "ms_123"
    millionsend.base_url = "https://mail.acme.dev"  # self-hosted: no cloud default

    email = millionsend.Emails.send({
        "from": "Acme <onboarding@acme.dev>",
        "to": "delivered@resend.dev",
        "subject": "Hello",
        "html": "<strong>it works</strong>",
    })
    print(email.id)

``api_key`` / ``base_url`` also read from ``MILLIONSEND_API_KEY`` /
``MILLIONSEND_BASE_URL``. Errors raise :class:`MillionSendError` subclasses.
"""

import os
from typing import Optional

from ._client import VERSION as __version__
from ._client import Response
from .audiences import Audiences
from .broadcasts import Broadcasts
from .contacts import Contacts
from .emails import Batch, Emails
from .errors import (
    ApplicationError,
    InvalidIdempotentRequestError,
    MillionSendError,
    MissingApiKeyError,
    NotFoundError,
    RestrictedApiKeyError,
    SendingPausedError,
    ValidationError,
)
from .segments import Segments
from .topics import Topics

# Module-level config (resend-python style). Env vars seed the defaults; either
# these globals or the env vars are read at call time.
api_key: Optional[str] = os.environ.get("MILLIONSEND_API_KEY")
base_url: Optional[str] = os.environ.get("MILLIONSEND_BASE_URL")
timeout: Optional[float] = None

__all__ = [
    "api_key",
    "base_url",
    "timeout",
    "Emails",
    "Batch",
    "Audiences",
    "Contacts",
    "Topics",
    "Broadcasts",
    "Segments",
    "Response",
    "MillionSendError",
    "MissingApiKeyError",
    "ValidationError",
    "NotFoundError",
    "RestrictedApiKeyError",
    "SendingPausedError",
    "InvalidIdempotentRequestError",
    "ApplicationError",
    "__version__",
]
