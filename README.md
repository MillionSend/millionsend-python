# millionsend

Official Python SDK for [MillionSend](https://github.com/MillionSend/millionsend) — a self-hostable, [Resend](https://resend.com)-compatible email API on AWS SES.

The API is wire-compatible with Resend and this SDK deliberately mirrors the shape of the `resend` PyPI package, so migrating is mostly a find-and-replace: swap the import, set `base_url` to your instance.

## Install

```bash
pip install millionsend
```

Requires Python 3.9+. Depends only on `requests`.

## Quickstart

```python
import millionsend

millionsend.api_key = "ms_123"
millionsend.base_url = "https://mail.acme.dev"  # your instance

email = millionsend.Emails.send({
    "from": "Acme <onboarding@acme.dev>",
    "to": "delivered@resend.dev",
    "subject": "Hello from MillionSend",
    "html": "<strong>It works!</strong>",
})

print(email.id)  # responses support both email["id"] and email.id
```

## Configuration

Config is module-level (no client object to construct):

```python
import millionsend

millionsend.api_key  = "ms_123"                  # or env MILLIONSEND_API_KEY
millionsend.base_url = "https://mail.acme.dev"   # or env MILLIONSEND_BASE_URL
millionsend.timeout  = 30                        # optional, seconds (default 60)
```

- `api_key` falls back to `MILLIONSEND_API_KEY`. Missing key raises `MissingApiKeyError` on the first call.
- `base_url` falls back to `MILLIONSEND_BASE_URL`, then `http://localhost:3001`. MillionSend is self-hosted, so **set this to your deployment in production.**

Request/response casing: request params are plain dicts in the API's `snake_case` (`reply_to`, `scheduled_at`, `first_name`). Responses are `dict` subclasses that also allow attribute access (`resp.id`, `resp.data[0].id`).

## Errors

Every call raises on a non-2xx response. The base is `MillionSendError`; known error names map to subclasses so you can catch them:

```python
from millionsend import NotFoundError, MillionSendError

try:
    contact = millionsend.Contacts.get(email="ghost@acme.dev")
except NotFoundError:
    ...  # 404
except MillionSendError as e:
    print(e.code, e.status_code, e.message)
```

- `e.code` is the stable `name` discriminant (`validation_error`, `not_found`, `restricted_api_key`, `sending_paused`, `invalid_idempotent_request`, …).
- `e.status_code` is the HTTP status, or `None` for client-side/transport failures (connection refused, DNS, timeout).

Subclasses: `ValidationError`, `NotFoundError`, `RestrictedApiKeyError`, `SendingPausedError`, `InvalidIdempotentRequestError`, `ApplicationError`, `MissingApiKeyError`.

## Resources

### Emails

```python
millionsend.Emails.send(payload, idempotency_key="order-42")  # POST /emails
millionsend.Emails.get(email_id)                              # GET /emails/{id}
millionsend.Emails.cancel(email_id)                           # POST /emails/{id}/cancel (scheduled only)
millionsend.Batch.send([payload_a, payload_b], idempotency_key="batch-1")  # up to 100
```

`to` / `cc` / `bcc` / `reply_to` accept a string or a list of strings.

### Contacts

Contacts are team-global — one record per email address, no audiences to manage.

```python
millionsend.Contacts.create({
    "email": "ada@acme.dev",
    "first_name": "Ada",
    "properties": {"plan": "pro"},
})
millionsend.Contacts.get(email="ada@acme.dev")  # by id or email (email wins)
millionsend.Contacts.get("contact-id")          # bare id works too
millionsend.Contacts.update({"id": "contact-id", "unsubscribed": True, "first_name": None})  # None clears
millionsend.Contacts.remove(email="ada@acme.dev")
millionsend.Contacts.list(limit=50)

# Topic subscriptions (granular unsubscribe) — mirrors resend's contacts.topics.update
millionsend.Contacts.Topics.update({
    "email": "ada@acme.dev",
    "topics": [{"id": "topic-id", "subscription": "opt_out"}],
})
```

Creating a contact whose email already exists on the team (case-insensitive) answers 409 and raises `ValidationError`.

### Topics

```python
millionsend.Topics.create({"name": "Product updates", "default_subscription": "opt_in"})
millionsend.Topics.get(topic_id)
millionsend.Topics.list()      # bare {"data": [...]} — topics are unpaginated
millionsend.Topics.remove(topic_id)
```

### Broadcasts

Target a saved segment (`segment_id`) and/or a topic (`topic_id`); set neither to send to every contact.

```python
broadcast = millionsend.Broadcasts.create({
    "segment_id": segment.id,  # optional
    "from": "Acme <news@acme.dev>",
    "subject": "Launch",
    "html": "<p>Hi {{{FIRST_NAME|there}}}</p>",
})
millionsend.Broadcasts.list()
millionsend.Broadcasts.get(broadcast.id)
millionsend.Broadcasts.update(broadcast.id, {"subject": "Launch 🚀"})       # draft only
millionsend.Broadcasts.send(broadcast.id, scheduled_at="2026-09-01T09:00:00Z")  # omit to send now
millionsend.Broadcasts.cancel(broadcast.id)  # scheduled only
millionsend.Broadcasts.remove(broadcast.id)  # draft only
```

### Segments (MillionSend extension)

Dynamic segments are a saved filter over the team's contacts — a MillionSend feature with **no Resend equivalent**.

```python
segment = millionsend.Segments.create({
    "name": "Pro plan",
    "filter": {"match": "all", "conditions": [
        {"field": "property:plan", "op": "equals", "value": "pro"},
    ]},
})
millionsend.Segments.get(segment.id)   # includes a live contact_count
millionsend.Segments.list()
millionsend.Segments.update(segment.id, {"name": "Pro tier"})
millionsend.Segments.remove(segment.id)
```

## Migrating from Resend

```diff
- import resend
- resend.api_key = "re_123"
+ import millionsend
+ millionsend.api_key = "ms_123"
+ millionsend.base_url = "https://mail.acme.dev"

- resend.Emails.send({...})
+ millionsend.Emails.send({...})
```

Method names and payloads match. Notes:

- **Domains and API keys** are managed in the MillionSend dashboard, not via the API, so there are no `Domains` / `ApiKeys` resources here.
- **No audiences**: contacts are team-global, so there is no `Audiences` resource and no `audience_id` params. Resend's `Segments` is an alias of audiences; MillionSend's `Segments` is the distinct dynamic-filter feature.
- MillionSend raises on API errors just like `resend`; the exception carries `.code` / `.status_code` / `.message`.

## License

MIT
