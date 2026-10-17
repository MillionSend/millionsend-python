# millionsend

Official Python SDK for [MillionSend](https://github.com/MillionSend/millionsend) — a self-hostable, [Resend](https://resend.com)-compatible email API on AWS SES.

The API is wire-compatible with Resend and this SDK deliberately mirrors the shape of the `resend` PyPI package, so migrating is mostly a find-and-replace: swap the import and the key. MillionSend Cloud works with just the key; a self-hosted instance also sets `base_url`.

## Install

```bash
pip install millionsend
```

Requires Python 3.9+. Depends only on `requests`.

## Quickstart

```python
import millionsend

millionsend.api_key = "ms_123"
millionsend.base_url = "https://mail.acme.dev"  # self-hosted only; omit for MillionSend Cloud

email = millionsend.Emails.send({
    "from": "Acme <onboarding@acme.dev>",
    "to": "success@simulator.amazonses.com",
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
millionsend.allow_insecure_http = False          # accept a non-loopback http:// base_url
```

- `api_key` falls back to `MILLIONSEND_API_KEY`. Missing key raises `MissingApiKeyError` on the first call.
- `base_url` falls back to `MILLIONSEND_BASE_URL`, then `https://api.millionsend.com` (MillionSend Cloud). Self-hosting? Set it to your instance's origin.
- Plain `http://` is only accepted for loopback hosts (`localhost`, `127.0.0.1`, `::1`); any other `http://` URL raises `MillionSendError` on the first call, since the API key is sent as a bearer header. Set `millionsend.allow_insecure_http = True` to talk to a non-TLS instance elsewhere (e.g. inside a private network).

Request/response casing: request params are plain dicts in the API's `snake_case` (`reply_to`, `scheduled_at`, `first_name`) and are sent to the wire as given — nothing is filtered or renamed. Responses are `dict` subclasses that also allow attribute access (`resp.id`, `resp.data[0].id`).

List methods take keyword arguments (`list(limit=50, after=cursor)`) or resend-python's params dict (`list({"limit": 50, "after": cursor})`).

### Request options

`Emails.send`, `Batch.send` and `Contacts.Batch.create` take resend-python's options dict as the second argument, or the same values as keywords:

```python
millionsend.Emails.send(payload, {"idempotency_key": "order-42"})
millionsend.Emails.send(payload, idempotency_key="order-42")

millionsend.Batch.send(payloads, {"idempotency_key": "batch-1", "batch_validation": "permissive"})
millionsend.Batch.send(payloads, batch_validation="permissive")
```

- `idempotency_key` → `Idempotency-Key` header (POST only). A replay with the same key and body returns the original ids; a different body raises `InvalidIdempotentRequestError`.
- `batch_validation` → `x-batch-validation` header: `"strict"` (default) rejects the whole batch on the first invalid item; `"permissive"` processes the valid items and lists the rest in the response's `errors[]`: `{index, message}` for emails, plus `statusCode` and `name` for contacts.

### Pagination

Keyset lists return `{"object": "list", "has_more", "data"}` and take `limit`, `after` and `before`. Most are newest first: `after` takes a page's last id and pages toward older items, and `before` takes its first id and pages toward newer ones (still newest first inside the page). `has_more` refers to the direction you page in. Threads are most recently active first, a thread's emails oldest first (`after` pages toward newer), and drafts most recently updated first; labels and topics aren't paginated. The SDK doesn't page for you.

To sync only what's new, page toward newer items from the newest id you stored:

```python
page = millionsend.Emails.list(before=newest_stored_id, limit=100)
while page.data:
    store(page.data)
    if not page.has_more:
        break
    page = millionsend.Emails.list(before=page.data[0].id, limit=100)
```

A cursor whose item was deleted raises `ValidationError` (422) on the top-level lists and `Emails.Receiving.list`, and `NotFoundError` (404) on the `Inboxes` lists: start again without a cursor and stop at ids you already have.

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
- `e.retry_after` is the response's `retry-after` header in seconds, or `None` when it had none (see [Retries](#retries)).
- `Emails.send` / `Batch.send` raise `AllRecipientsSuppressedError` (422 `all_recipients_suppressed`) when every `to` recipient is on the suppression list or opted out of the send's `topic_id`. An `Emails.send` that the suppression list alone refuses still keeps a metadata-only `suppressed` email, which fires `email.suppressed`, and each retry keeps another, even with the same `idempotency_key` (a refused send doesn't hold its key).
- `Inboxes.Quarantine.release` raises the base `MillionSendError` with `e.code` `trust_not_allowed` (403) or `held_by_screening` (409), see [Inboxes](#inboxes); it answers `forbidden` (403) and `screening_unavailable` (503) only to MCP clients.

Subclasses: `MissingApiKeyError`, `InvalidApiKeyError`, `ValidationError`, `AllRecipientsSuppressedError`, `InvalidParameterError`, `InvalidPayloadError`, `PayloadTooLargeError`, `NotFoundError`, `ConflictError`, `ForbiddenError`, `RestrictedApiKeyError`, `SendingPausedError`, `RateLimitExceededError`, `DailyQuotaExceededError`, `PlanLimitReachedError`, `InvalidIdempotentRequestError`, `ConcurrentIdempotentRequestsError`, `InboxSendPolicyError`, `InboxSendCapReachedError`, `ApprovalRequiredError`, `EmailQuarantinedError`, `EmailBlockedError`, `TooManyWaitsError`, `NameReviewUnavailableError`, `InternalServerError`, `ApplicationError`. Unknown names raise the base `MillionSendError`. A body that isn't JSON, such as an older server's plain-text 404 for an unknown route, raises `ApplicationError` with the HTTP status. Messages are for people and may change: branch on `e.code` and `e.status_code`, not on the message.

### Retries

The SDK never retries by itself. After `e.retry_after` seconds it's worth retrying:

- `NameReviewUnavailableError` (503; 60 seconds, or 300 while a new team's subdomain waits for its review);
- `RateLimitExceededError` when `e.retry_after` is 60 or less (the per-minute limits);
- `TooManyWaitsError`.

`InboxSendCapReachedError` and a `RateLimitExceededError` for the day's name-review budget last until the next UTC midnight, so don't retry them in the same process; the review budget shares the per-minute limits' `rate_limit_exceeded` name, so decide on `e.retry_after`. Don't retry a 403, 404, 409 or 422.

- Sends (`Emails.send`, `Batch.send`, replies, forwards, `Drafts.send`): resend with the same `idempotency_key`. A batch replay returns the stored response, even if a recipient was refused or suppressed since. `{"kind": "draft"}` (HTTP 202) is a held draft, not a failure: never resend it.
- `Inboxes.create` takes no idempotency key. After a 503 or 429 nothing was created, so creating again is safe; after a timeout it may create a second inbox. With a chosen `username`, a 409 on the second try usually means the first one worked: fetch it with `Inboxes.get(email_address)`.

## Resources

### Emails

```python
millionsend.Emails.send({
    "from": "Acme <onboarding@acme.dev>",
    "to": ["ada@acme.dev"],
    "cc": "ops@acme.dev",
    "bcc": ["audit@acme.dev"],
    "reply_to": "support@acme.dev",
    "subject": "Your receipt",
    "html": "<p>Thanks!</p>",
    "text": "Thanks!",
    "scheduled_at": "in 2 hours",                        # or ISO 8601 with offset
    "tags": [{"name": "category", "value": "receipt"}],
    "topic_id": topic.id,                                # skip recipients opted out of the topic
    "headers": {"X-Entity-Ref-ID": "order-42"},
    "attachments": [{
        "filename": "receipt.pdf",
        "content": base64_pdf,                           # base64 string
        "content_type": "application/pdf",               # optional
        "content_id": "receipt",                         # optional, for cid: references
    }],
}, idempotency_key="order-42")

millionsend.Emails.get(email_id)                              # GET /emails/{id} (includes a nullable 0-10 `score`)
millionsend.Emails.list(limit=50, after=cursor)               # GET /emails
millionsend.Emails.update({"id": email_id, "scheduled_at": "2026-09-01T09:00:00Z"})  # PATCH, scheduled only
millionsend.Emails.cancel(email_id)                           # POST /emails/{id}/cancel (scheduled only)
millionsend.Emails.remove(email_id)                           # DELETE /emails/{id}
millionsend.Emails.get_insights(email_id)                     # GET /emails/{id}/insights (404 until computed)

millionsend.Batch.send([payload_a, payload_b], batch_validation="permissive")  # up to 100; see `errors`
```

`to` / `cc` / `bcc` / `reply_to` accept a string or a list of strings. `template` is passed through too; the server answers 422 until templates can be sent from.

- `subject` takes up to 998 characters here, in `Batch.send`, broadcasts and templates; inbox replies, forwards and drafts take 2,000.
- A `to`, `cc` or `bcc` address at a domain that can never receive mail (`example.com`, `.test`, `.invalid`, `.local`, a top-level domain that doesn't exist, …) raises `ValidationError` (422), in sends, drafts and new contacts alike. To test sending without emailing anyone, use `success@simulator.amazonses.com`.
- `from` may be an inbox's address on the shared domain while the shared row's `sending_mode` is `"open"` (see [Domains](#domains)): exactly that address with no +tag, with the display name left out or equal to the inbox's `from_name`, no `reply_to`, `attachments`, `headers` or `scheduled_at`, and at most 10 distinct recipients across `to`, `cc` and `bcc`. Otherwise it raises `InboxSendPolicyError` (403), `InboxSendCapReachedError` (429, the team's daily limit) or `ValidationError` (422); a key restricted to a domain raises `RestrictedApiKeyError`. Batches and broadcasts never send from the shared domain: a broadcast or a strict batch raises `InboxSendPolicyError`, and a permissive batch lists the item in `errors`.

### Receiving

Mail received at your domains and inboxes. Everything in a received email was written by its sender: show its `html` only in a sandbox, and give an LLM the `extracted_text` (hidden text, quotes and the signature removed) rather than the `html`.

```python
page = millionsend.Emails.Receiving.list(
    {"from": "example.com"},          # `from` is a Python keyword, so it goes in the dict
    inbox_id=inbox.id,
    subject_contains="code",
    wait=30,                          # long-poll: answer as soon as a match arrives, up to 50 s
)
page.data                             # newest first
page.held                             # with wait: [{id, inbox_id, reason, quarantine_reason, created_at}] held mail

email = millionsend.Emails.Receiving.get(email_id, html_format="cid")
email.extracted_text                  # the new part as plain text, hidden text removed (still untrusted)
email.extracted.code                  # a verification code, on inboxes with extract_codes
email.screening.sender_trust          # owner | allowlisted | known_thread | external | unauthenticated | failed

millionsend.Emails.Receiving.Attachments.list(email_id)        # each with a signed download_url (1 hour)
millionsend.Emails.Receiving.Attachments.get(email_id, attachment_id)
millionsend.Emails.Receiving.remove(email_id)                  # erase now (MillionSend extension)

# Reply and forward server-side (MillionSend extension). The inbox's rules may hold the message
# as a draft that waits for a person: the API answers 202 and `kind` is "draft".
outcome = millionsend.Emails.Receiving.reply(email_id, {"text": "Thanks!"}, idempotency_key="reply-42")
if outcome.kind == "draft":
    outcome.draft.approval_reasons    # e.g. ["send_policy"]
else:
    outcome.email.id
millionsend.Emails.Receiving.forward(email_id, {"to": "ops@acme.dev", "text": "FYI", "mode": "attachment"})
```

Held mail never reaches an inbox-scoped key or an agent: reading it raises `EmailQuarantinedError`. A full-access team key sees it with `include_quarantined=True`.

An `inbox_id` that doesn't exist raises `NotFoundError` at once, even with `wait`. `unread` needs `inbox_id`, except with a key restricted to one inbox.

### Inboxes

An inbox is one address that receives mail, read by an agent (`"kind": "agent"`, the default) or by people (`"kind": "human"`). Threads, labels, drafts and their paths mirror Resend's Inboxes beta; `Safety`, `Codes` and `Quarantine` are MillionSend extensions.

```python
inbox = millionsend.Inboxes.create({
    "name": "Signup bot",             # 1-320 characters
    "username": "signup-bot",         # no email_address: signup-bot@<team>.<shared domain>; omitted, a random one
    "expires_in": "24h",              # "1h" to "365d"; omitted or None, the inbox never expires
    "safety": {"accept_from": "anyone"},
})
millionsend.Inboxes.create({"email_address": "support@acme.dev", "name": "Support", "kind": "human"})
millionsend.Inboxes.create({"domain_id": domain.id, "username": "billing"})  # billing@ one of your domains
millionsend.Inboxes.list(kind="agent")
millionsend.Inboxes.get("support@acme.dev")                    # by id or address
millionsend.Inboxes.update(inbox.id, {"from_name": "Acme", "expires_in": "7d"})
millionsend.Inboxes.remove(inbox.id)                           # also revokes its inbox-scoped keys

# Codes and sign-in links, without parsing HTML (wait long-polls up to 50 s)
code = millionsend.Inboxes.Codes.latest(inbox.id, {"from": "example.com"}, wait=30)
code.status                           # "found" | "none" | "ambiguous" | "timeout"; code.code, code.url
# A second sign-in: only mail received after the first code counts
millionsend.Inboxes.Codes.latest(inbox.id, {"from": "example.com"}, wait=30, since=code.received_at)

# Safety rules: who can write in, what the inbox may send
millionsend.Inboxes.Safety.get(inbox.id)
millionsend.Inboxes.Safety.update(inbox.id, {"accept_from": "allowlist", "allowlist": ["*@acme.dev"]})

# Quarantine: held mail, kept until a person releases it
millionsend.Inboxes.Quarantine.list(inbox.id)
millionsend.Inboxes.Quarantine.release(inbox.id, email_id)

# Threads and their messages
millionsend.Inboxes.Threads.list(inbox.id, folders=["inbox", "archive"], read=False)
millionsend.Inboxes.Threads.search(inbox.id, {"query": "invoice", "from": ["example.com"]})
millionsend.Inboxes.Threads.get(inbox.id, thread_id)
millionsend.Inboxes.Threads.update(inbox.id, thread_id, {"read": True, "folder": "archive", "label_id": label_id})
millionsend.Inboxes.Threads.remove(inbox.id, thread_id)        # to trash, purged after 30 days
millionsend.Inboxes.Threads.Emails.list(inbox.id, thread_id)   # oldest first; include_quarantined=True adds held mail
millionsend.Inboxes.Threads.Emails.get(inbox.id, thread_id, email_id)
millionsend.Inboxes.Threads.Emails.reply(inbox.id, thread_id, email_id, {"text": "Done."}, idempotency_key=key)
millionsend.Inboxes.Threads.Emails.forward(inbox.id, thread_id, email_id, {"to": "ops@acme.dev"})

# Labels (up to 100 per inbox)
millionsend.Inboxes.Labels.create(inbox.id, {"name": "Billing", "color": "#FF8800"})
millionsend.Inboxes.Labels.list(inbox.id)
millionsend.Inboxes.Labels.update(inbox.id, label_id, {"name": "Invoices"})
millionsend.Inboxes.Labels.remove(inbox.id, label_id)

# Drafts, and the ones that wait for approval
millionsend.Inboxes.Drafts.create(inbox.id, {"to": "success@simulator.amazonses.com", "subject": "Hi", "text": "..."})
millionsend.Inboxes.Drafts.list(inbox.id)
millionsend.Inboxes.Drafts.get(inbox.id, draft_id)
millionsend.Inboxes.Drafts.update(inbox.id, draft_id, {"cc": None})   # None clears
millionsend.Inboxes.Drafts.send(inbox.id, draft_id, idempotency_key=key)  # {"kind": "sent" | "draft", ...}
millionsend.Inboxes.Drafts.reject(inbox.id, draft_id)
millionsend.Inboxes.Drafts.remove(inbox.id, draft_id)
```

Replies, forwards and `Drafts.send` return `{"kind": "sent", "email": ...}` or, when the inbox's rules hold the message for a person (HTTP 202), `{"kind": "draft", "draft": ...}`. A key restricted to the inbox cannot send a draft that waits for approval (`ApprovalRequiredError`); a person in the dashboard or a full-access team key approves it. An agent's reply to a `Reply-To` at another organization is held the same way, with `"reply_to_redirect"` among `approval_reasons`. Hosted agent settings (`/inboxes/{id}/agent`) are not exposed: MillionSend runs no agent of its own.

With `include_quarantined=True` (full-access team keys), the items of `Threads.list` and `Threads.search` carry `quarantined`: their held messages not yet released.

On an agent inbox with `screening` on, mail held before screening ran (`not_allowlisted`, `unauthenticated_sender`, `failed_auth`) is screened at release when screening can run: if it finds prompt injection or phishing, the email stays held as `injection` or `phishing` (409 `held_by_screening`). `trust_sender=True` also adds the sender to the allowlist, only for mail held as `not_allowlisted` from a sender that authenticated (`sender_trust` `"external"`); anything else is refused with 403 `trust_not_allowed`.

#### Inboxes on the shared domain

Without `email_address`, an inbox gets an address on the instance's shared domain, `<username>@<team>.<shared domain>`. `username` is trimmed and lowercased: 1-64 of `a-z 0-9 . _ -`, starting and ending with a letter or digit. Without it the address is random (`inbox-…`). `domain_id` takes a row of `Domains.list()` instead: the shared row works like omitting `email_address`, and one of your own domains needs `username`, the part before the @, and receiving on (or `"forwarding": True`). A shared inbox's `domain_id` is the shared row's id (see [Domains](#domains)).

- Names are reviewed: a reserved (`postmaster`, `admin`, `noreply`, …), `fwd-` or brand look-alike `username`, or a brand look-alike `from_name`, raises `ValidationError` (422; 409 when the address is taken). `NameReviewUnavailableError` (503) means the review can't run right now, and `RateLimitExceededError` (429) that the day's review budget is spent; both carry `retry_after`.
- An inbox there with no mail in or out and no API call for 90 days is deleted (`inbox.expired`, then `inbox.deleted`).
- Sending follows the shared row's `sending_mode`: `"reply_only"` lets through only in-thread replies to the thread's own correspondents, and `"receive_only"` nothing. A reply, forward or draft it forbids raises `InboxSendPolicyError` (403), `InboxSendCapReachedError` (429) means the team reached today's limit, and more than 10 recipients raise `ValidationError` (422). A person or a team key sending a draft skips the inbox's rules, not the shared domain's.
- In `Safety`, `send_policy` can't be `"allowlist"`, and is `"open"` only while `sending_mode` is `"open"`. `owner_addresses` don't make senders trusted there, and `forward_to` copies go only to team members' sign-in addresses.

### Contacts

Contacts are team-global — one record per email address, no audiences to manage.

```python
millionsend.Contacts.create({
    "email": "ada@acme.dev",
    "first_name": "Ada",
    "last_name": "Lovelace",
    "unsubscribed": False,
    "properties": {"plan": "pro", "seats": 3},
    "segments": [{"id": segment.id}],
    "topics": [{"id": topic.id, "subscription": "opt_in"}],
})
millionsend.Contacts.get(email="ada@acme.dev")  # by id or email (email wins)
millionsend.Contacts.get("contact-id")          # bare id works too, as does resend's id="contact-id"
millionsend.Contacts.update({"id": "contact-id", "unsubscribed": True, "first_name": None})  # None clears
millionsend.Contacts.update({"email": "ada@acme.dev", "properties": {"plan": None}})       # None removes the key
millionsend.Contacts.remove(email="ada@acme.dev")              # the contact's emails stay in the send log
millionsend.Contacts.remove(email="ada@acme.dev", erase=True)  # ?erase=true — also scrubs the address from email history, event payloads and API logs (GDPR/LGPD erasure)
millionsend.Contacts.preferences_link(email="ada@acme.dev").url  # hosted preference page (MillionSend extension); no expiry, hand it only to the contact
millionsend.Contacts.list(limit=50)
millionsend.Contacts.list(segment_id=segment.id)  # GET /segments/{id}/contacts
# Bulk read (MillionSend extension): attach properties and topic subscriptions to every item,
# so an audience reads in one request per 100 contacts instead of one per contact
millionsend.Contacts.list(limit=100, include=["properties", "topics"])  # ?include=properties,topics

# Bulk create (MillionSend extension) — up to 1000 per call
result = millionsend.Contacts.Batch.create(
    [{"email": "a@acme.dev"}, {"email": "b@acme.dev", "first_name": "B"}],
    on_conflict="upsert",            # error (default) | skip | upsert
    batch_validation="permissive",   # strict (default) | permissive
)
result.data[0].status  # created | updated | skipped
result.counts.failed
result.errors          # permissive mode: [{index, statusCode, name, message}]

# Bulk lookup (MillionSend extension) — up to 1000 contacts by id or email in one request, in request order;
# unknown entries are listed under `missing`, not errors — one request against the rate limit
result = millionsend.Contacts.Batch.get(["contact-id", {"email": "ada@acme.dev"}], include=["topics"])
result.data     # [{object: "contact", id, email, ..., topics}] — the contacts found
result.missing  # [{index, email}] — request entries that matched nobody

# Bulk delete (MillionSend extension) — {"ids": [...]} or {"emails": [...]}, up to 1000; data lists only the rows deleted.
# Emails stay in the send log; erase=True also scrubs each address from email history, event payloads and API logs
millionsend.Contacts.Batch.remove({"emails": ["a@acme.dev", "b@acme.dev"]})
millionsend.Contacts.Batch.remove({"emails": ["a@acme.dev"]}, erase=True)  # body {"emails": [...], "erase": true}

# Segment membership — mirrors resend's contacts.segments
millionsend.Contacts.Segments.add({"contact_id": "contact-id", "segment_id": segment.id})
millionsend.Contacts.Segments.remove({"email": "ada@acme.dev", "segment_id": segment.id})

# Topic subscriptions (granular unsubscribe) — mirrors resend's contacts.topics
millionsend.Contacts.Topics.update({
    "email": "ada@acme.dev",
    "topics": [{"id": "topic-id", "subscription": "opt_out"}],
})
topics = millionsend.Contacts.Topics.list(email="ada@acme.dev")  # GET /contacts/{idOrEmail}/topics
for t in topics.data:
    print(t.name, t.subscription, t.explicit, t.visibility)  # subscription is the effective choice; explicit=False means the topic default applies; the preference page lists public topics only
```

Creating a contact whose email already exists on the team (case-insensitive) answers 409 and raises `ValidationError`.

### Contact properties

Property definitions for the `properties` map on contacts.

```python
prop = millionsend.ContactProperties.create({"key": "plan", "type": "string", "fallback_value": "free"})
millionsend.ContactProperties.list()
millionsend.ContactProperties.get(prop.id)
millionsend.ContactProperties.update({"id": prop.id, "fallback_value": None})  # None clears
millionsend.ContactProperties.remove(prop.id)
```

### Topics

```python
millionsend.Topics.create({"name": "Product updates", "default_subscription": "opt_in"})
millionsend.Topics.get(topic_id)
millionsend.Topics.list()      # bare {"data": [...]} — topics are unpaginated
millionsend.Topics.update(topic_id, {"name": "Product news", "visibility": "public"})
millionsend.Topics.remove(topic_id)
```

### Broadcasts

Target a saved segment (`segment_id`) and/or a topic (`topic_id`); set neither to send to every contact.

```python
broadcast = millionsend.Broadcasts.create({
    "name": "September launch",   # internal, optional
    "segment_id": segment.id,     # optional
    "topic_id": topic.id,         # optional
    "from": "Acme <news@acme.dev>",
    "reply_to": "support@acme.dev",
    "subject": "Launch",
    "preview_text": "It's here",
    "html": "<p>Hi {{{FIRST_NAME|there}}}</p>",
    "text": "Hi there",
    "send": False,                # True sends (or schedules) instead of saving a draft
    "scheduled_at": "in 1 hour",  # with send: True
})
millionsend.Broadcasts.list()
millionsend.Broadcasts.get(broadcast.id)
millionsend.Broadcasts.update(broadcast.id, {"subject": "Launch 🚀", "topic_id": None})  # draft only; None clears
millionsend.Broadcasts.update({"broadcast_id": broadcast.id, "subject": "Launch"})        # resend-python shape
millionsend.Broadcasts.send(broadcast.id, scheduled_at="2026-09-01T09:00:00Z")  # omit to send now
millionsend.Broadcasts.send({"broadcast_id": broadcast.id})                      # resend-python shape
millionsend.Broadcasts.cancel(broadcast.id)  # scheduled only
millionsend.Broadcasts.remove(broadcast.id)  # draft only
```

### Segments (MillionSend extension)

Dynamic segments are a saved filter over the team's contacts — a MillionSend feature with **no Resend equivalent**.

```python
segment = millionsend.Segments.create({
    "name": "Pro plan",
    "filter": {"match": "all", "conditions": [   # optional; omit or None = every contact
        {"field": "property:plan", "op": "equals", "value": "pro"},
    ]},
})
millionsend.Segments.get(segment.id)   # includes a live contact_count
millionsend.Segments.list()
millionsend.Segments.update(segment.id, {"name": "Pro tier"})
millionsend.Segments.remove(segment.id)
```

### Suppressions

Addresses the API refuses to send to. Addressable by id or email.

```python
millionsend.Suppressions.add({"email": "bounced@acme.dev", "origin": "manual"})  # origin: bounce | complaint | manual | unsubscribe
millionsend.Suppressions.get("bounced@acme.dev")
millionsend.Suppressions.list(origin="bounce", limit=50)
millionsend.Suppressions.remove("bounced@acme.dev")

millionsend.Suppressions.Batch.add({"emails": ["a@acme.dev", "b@acme.dev"], "origin": "unsubscribe"})  # up to 1000
millionsend.Suppressions.Batch.remove({"emails": ["a@acme.dev"]})   # or {"ids": [...]}
```

`Suppressions.create` is an alias of `add`.

### Domains

```python
domain = millionsend.Domains.create({
    "name": "acme.dev",
    "region": "us-east-1",           # optional; must match the deployment's SES region
    "custom_return_path": "send",    # optional
    "open_tracking": True,           # optional
    "click_tracking": True,          # optional
    "tracking_subdomain": "links",   # optional; links.acme.dev
})
for record in domain.records:        # DNS records to publish
    print(record.type, record.name, record.value)

millionsend.Domains.list()
millionsend.Domains.get(domain.id)
millionsend.Domains.verify(domain.id)
millionsend.Domains.update({"id": domain.id, "open_tracking": False, "tracking_subdomain": None})
millionsend.Domains.update({"id": domain.id, "receiving_catch_all": True})  # accept mail for addresses without an inbox
millionsend.Domains.remove(domain.id)
```

`Domains.list()` ends with the team's subdomain of the shared domain, after all its own domains (alone on the next page when they fill a page exactly): the row with `shared: True`, whose id is the `domain_id` of the team's shared inboxes. It's read-only (`update`, `verify` and `remove` raise `ForbiddenError`) and only sends from an inbox's own address (see [Emails](#emails)). Only that row carries `sending_mode`: `"open"` starts conversations, `"reply_only"` replies inside threads, and `"receive_only"` sends nothing. `sending_mode_reason` says what holds it below `"open"`, `"plan"` or `"instance"` (`None` when open). The row is missing when the instance has no shared domain, the server predates v0.14.0, or a new team's subdomain still waits for its name review.

To pick a sender domain, skip the shared row. Servers before v0.14.0 send no `shared` key, so read it with `get`:

```python
sender_domains = [d for d in millionsend.Domains.list().data if d.status == "verified" and not d.get("shared")]
```

### Webhooks

```python
webhook = millionsend.Webhooks.create({
    "endpoint": "https://acme.dev/hooks/millionsend",
    "events": ["email.delivered", "email.bounced", "email.complained"],
    "signing_secret": "whsec_...",   # optional: reuse a secret instead of minting one
})
webhook.signing_secret               # also returned by get()

millionsend.Webhooks.list()
millionsend.Webhooks.get(webhook.id)
millionsend.Webhooks.update({"webhook_id": webhook.id, "status": "disabled"})  # endpoint, events, status
millionsend.Webhooks.remove(webhook.id)

# Rotate the signing secret (MillionSend extension). For overlap_hours (default 24, max 72) deliveries
# carry both signatures, so the receiver can switch without a gap; 0 drops the old secret at once.
rotated = millionsend.Webhooks.rotate(webhook.id, {"overlap_hours": 24})  # or {"signing_secret": "whsec_..."}
rotated.signing_secret
rotated.previous_secret_expires_at   # None once the old secret stops signing; also on get()
```

Events include `email.scheduled`, `email.failed`, `email.suppressed`, `email.prefetched`, `email.received` and the `inbox.*` events (`inbox.created`, `inbox.updated`, `inbox.deleted`, `inbox.expired`, `inbox.thread.created`, `inbox.thread.folder.updated`, `inbox.thread.labels.updated`, `inbox.email.received`, `inbox.email.sent`, `inbox.email.quarantined`, `inbox.draft.created`, `inbox.draft.updated`, `inbox.draft.sent`, `inbox.draft.deleted`). `email.prefetched` and inbox events reach only endpoints that list them by name. `inbox_ids` limits an endpoint's inbox events and `email.received` to those inboxes (`None` = every inbox). A shared-domain inbox deleted after 90 idle days fires `inbox.expired`, then `inbox.deleted`, and inbox events from a send in the dashboard carry `data.source: "dashboard"`.

`email.failed` says why in `data.failed.reason`, and `email.suppressed` in `data.suppressed` (`type`, `message` and `reason`); new values can appear, so don't treat them as a closed list. On servers before v0.15.1, a webhook that names `email.scheduled`, `email.failed` or `email.suppressed` raises `ValidationError` (422).

### API keys

```python
key = millionsend.ApiKeys.create({"name": "ci", "permission": "sending_access", "domain_id": domain.id})
key.token                            # shown once
millionsend.ApiKeys.create({"name": "signup-agent", "permission": "full_access", "inbox_id": inbox.id})
millionsend.ApiKeys.list()
millionsend.ApiKeys.remove(key.id)
```

`domain_id` must be one of the team's own domains: the shared row's id raises `ValidationError`.

### Templates

Addressable by id or alias.

```python
template = millionsend.Templates.create({
    "name": "Welcome",
    "alias": "welcome-v1",           # optional, unique per team
    "subject": "Welcome aboard",     # optional
    "html": "<p>Hi {{{FIRST_NAME}}}</p>",
    "text": "Hi",                    # optional
})
millionsend.Templates.get("welcome-v1")
millionsend.Templates.list()
millionsend.Templates.update({"id": "welcome-v1", "subject": None, "alias": None})  # None clears
millionsend.Templates.duplicate(template.id)
millionsend.Templates.publish(template.id)   # templates are always published; kept for resend compatibility
millionsend.Templates.remove(template.id)
```

Resend's `from`, `reply_to` and `variables` are forwarded as given; the server answers 422 for them until templates model them.

### Usage (MillionSend extension)

```python
usage = millionsend.Usage.get()
usage.plan                     # None when self-hosted
usage.limits.emails_per_day    # None = unlimited
usage.today.emails_sent
```

### Deliverability (MillionSend extension)

Per-email best-practice insights and an account-level deliverability score — no Resend equivalent.

```python
insights = millionsend.Emails.get_insights(email.id)  # raises NotFoundError until computed
print(insights.score, insights.band)                  # 8.5 "excellent"
for check in insights.checks:
    print(check.id, check.status, check.penalty)

account = millionsend.Deliverability.get()            # trailing-30-day account score
print(account.score, account.band, account.guardrail_status)  # scores are None until enough data
```

## Server versions

Self-hosting? Each feature needs at least this MillionSend version:

| Feature | Server |
|---|---|
| `Emails.Receiving` list, get and attachments | v0.8.0 |
| `Inboxes`; `Emails.Receiving` reply, forward, remove, `wait` and the quarantine filters; `inbox_ids` on webhooks, `inbox_id` on API keys, `receiving_catch_all` on domains | v0.10.0 |
| Recipients that can never receive mail refused; a batch `idempotency_key` replayed before validation | v0.11.0 |
| `username`; inboxes that never expire by default, `expires_in` `"1h"` to `"365d"`; sending from the shared domain; name reviews (`NameReviewUnavailableError`); `statusCode` and `name` on contacts-batch errors | v0.12.0 |
| Newest-first lists; a JSON 404 for unknown routes; `since` on `Codes.latest`; `quarantined` on thread items; inbox names up to 320 characters; `NotFoundError` at once for an unknown `inbox_id`; `unread` with an inbox-scoped key | v0.13.0 |
| The shared row in `Domains.list()` (`shared`, `sending_mode`, `sending_mode_reason`); `domain_id` on `Inboxes.create`; `subject` up to 998 characters | v0.14.0 |
| The `email.scheduled`, `email.failed` and `email.suppressed` webhook events; a `suppressed` email kept on `AllRecipientsSuppressedError` | v0.15.1 |
| Release rules: `trust_sender` only for a `not_allowlisted` hold from an authenticated sender (`trust_not_allowed`); screening at release (`held_by_screening`) | v0.16.0 |

Older servers ignore options they don't know: before v0.12.0 `username` is dropped and the address is random, before v0.14.0 `domain_id` is dropped and the inbox lands on the shared domain, and before v0.13.0 `since` is dropped, so a code you already used can come back. If you must support them, check the created inbox's `email_address`, and treat a code whose `received_at` isn't after `since` as none.

## Migrating from Resend

```diff
- import resend
- resend.api_key = "re_123"
+ import millionsend
+ millionsend.api_key = "ms_123"
+ millionsend.base_url = "https://mail.acme.dev"  # self-hosted only

- resend.Emails.send({...})
+ millionsend.Emails.send({...})
```

Method names and payloads match. Notes:

- **Same resources**: `Emails`, `Batch`, `Contacts` (with `.Topics`, `.Segments`), `ContactProperties`, `Topics`, `Broadcasts`, `Suppressions` (with `.Batch`), `Domains`, `Webhooks`, `ApiKeys`, `Templates`. Payloads are sent verbatim, so a resend-python payload works as-is.
- **No audiences**: contacts are team-global, so there is no `Audiences` resource and no `audience_id` params. The API's `/audiences/...` routes are a compatibility shim for raw HTTP callers and are deliberately not exposed here. Resend's `Segments` is an alias of audiences; MillionSend's `Segments` is the distinct dynamic-filter feature.
- **MillionSend extensions** (no Resend equivalent): `Segments`, `Contacts.Batch`, `Contacts.list(segment_id=...)`, `Contacts.preferences_link`, `Webhooks.rotate`, `Usage`, `Deliverability`, `Emails.get_insights`, `Emails.Receiving.reply` / `forward` / `remove`, and `Inboxes` (Resend's Inboxes are not in resend-python yet).
- **Not available**: Resend's `ApiKeys.update`, `Webhooks` event history/replay/`verify`, `Emails.share` / `Emails.metrics`, `Broadcasts.recipients` / `clicked_links`, `Contacts.Segments.list`, `DomainClaims`, `ContactImports`, `Automations`, `Events`, `Logs`, `OAuthGrants`, and the `*_async` variants.
- MillionSend raises on API errors just like `resend`; the exception carries `.code` / `.status_code` / `.message`.

## License

MIT
