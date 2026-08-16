"""Exception hierarchy for the MillionSend SDK.

On any non-2xx response the API returns ``{"statusCode", "name", "message"}``.
``name`` is the stable discriminant; each known name maps to a subclass so
callers can ``except NotFoundError``. Client-side/transport failures that never
reached the API raise the base error with ``status_code=None``.
"""

from typing import Optional


class MillionSendError(Exception):
    """Base for every SDK error.

    Attributes:
        code: the API's stable ``name`` discriminant (e.g. ``"validation_error"``),
            or ``None`` for a client-side failure.
        message: human-readable message.
        status_code: HTTP status, or ``None`` when the request never reached the API.
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class MissingApiKeyError(MillionSendError):
    """No API key was configured (option or MILLIONSEND_API_KEY)."""


class ValidationError(MillionSendError):
    pass


class NotFoundError(MillionSendError):
    pass


class RestrictedApiKeyError(MillionSendError):
    pass


class SendingPausedError(MillionSendError):
    pass


class InvalidIdempotentRequestError(MillionSendError):
    pass


class ApplicationError(MillionSendError):
    pass


# name discriminant -> exception class; unknown names fall back to the base.
ERROR_TYPES = {
    "validation_error": ValidationError,
    "not_found": NotFoundError,
    "restricted_api_key": RestrictedApiKeyError,
    "sending_paused": SendingPausedError,
    "invalid_idempotent_request": InvalidIdempotentRequestError,
    "application_error": ApplicationError,
}


def raise_api_error(status: int, parsed: object) -> None:
    """Coerce a parsed non-2xx body into the canonical error and raise it."""
    if isinstance(parsed, dict):
        name = parsed.get("name")
        name = name if isinstance(name, str) else "application_error"
        message = parsed.get("message")
        message = message if isinstance(message, str) else f"Request failed with status {status}"
        status_code = parsed.get("statusCode")
        status_code = status_code if isinstance(status_code, int) else status
    else:
        name = "application_error"
        message = f"Request failed with status {status}"
        status_code = status
    raise ERROR_TYPES.get(name, MillionSendError)(message, code=name, status_code=status_code)
