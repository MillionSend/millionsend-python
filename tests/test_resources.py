"""Method + path + body + query mapping for every resource, over the mock layer."""

from urllib.parse import quote

import millionsend


def test_emails_get_and_cancel(http):
    millionsend.Emails.get("e1")
    assert http.calls[0]["method"] == "GET"
    assert http.calls[0]["path"] == "/emails/e1"

    millionsend.Emails.cancel("e1")
    assert http.calls[1]["method"] == "POST"
    assert http.calls[1]["path"] == "/emails/e1/cancel"


def test_emails_send_body_passthrough(http):
    millionsend.Emails.send(
        {
            "from": "a@x.dev",
            "to": ["b@x.dev"],
            "subject": "s",
            "html": "<p>h</p>",
            "reply_to": "r@x.dev",
            "scheduled_at": "2999-01-01T00:00:00Z",
        }
    )
    assert http.calls[0]["method"] == "POST"
    assert http.calls[0]["path"] == "/emails"
    assert http.calls[0]["body"] == {
        "from": "a@x.dev",
        "to": ["b@x.dev"],
        "subject": "s",
        "html": "<p>h</p>",
        "reply_to": "r@x.dev",
        "scheduled_at": "2999-01-01T00:00:00Z",
    }


def test_batch_sends_bare_array_with_idempotency(http):
    http.body = {"data": [{"id": "1"}, {"id": "2"}]}
    res = millionsend.Batch.send(
        [
            {"from": "a@x.dev", "to": "b@x.dev", "subject": "1", "text": "one"},
            {"from": "a@x.dev", "to": "c@x.dev", "subject": "2", "text": "two"},
        ],
        idempotency_key="batch-1",
    )
    assert http.calls[0]["path"] == "/emails/batch"
    assert isinstance(http.calls[0]["body"], list)
    assert len(http.calls[0]["body"]) == 2
    assert http.calls[0]["headers"]["Idempotency-Key"] == "batch-1"
    assert len(res.data) == 2


def test_contacts_create(http):
    millionsend.Contacts.create({"email": "c@x.dev", "first_name": "Ada"})
    assert http.calls[0]["method"] == "POST"
    assert http.calls[0]["path"] == "/contacts"
    assert http.calls[0]["body"] == {"email": "c@x.dev", "first_name": "Ada"}


def test_contacts_addressing(http):
    millionsend.Contacts.get("c1")
    assert http.calls[0]["path"] == "/contacts/c1"

    millionsend.Contacts.get(email="c@x.dev")
    assert http.calls[1]["path"] == "/contacts/" + quote("c@x.dev", safe="")


def test_contacts_email_wins_over_id(http):
    millionsend.Contacts.get(contact_id="c1", email="c@x.dev")
    assert http.calls[0]["path"] == "/contacts/" + quote("c@x.dev", safe="")


def test_contacts_update_sends_only_provided_keys(http):
    millionsend.Contacts.update({"id": "c1", "first_name": None, "unsubscribed": True})
    assert http.calls[0]["method"] == "PATCH"
    assert http.calls[0]["path"] == "/contacts/c1"
    assert http.calls[0]["body"] == {"first_name": None, "unsubscribed": True}


def test_contacts_remove_and_list(http):
    millionsend.Contacts.remove(email="c@x.dev")
    assert http.calls[0]["method"] == "DELETE"

    millionsend.Contacts.list(after="cur")
    assert http.calls[1]["path"] == "/contacts"
    assert http.calls[1]["params"] == {"after": "cur"}


def test_contacts_topics_update_bare_array(http):
    http.body = {"id": "c1"}
    millionsend.Contacts.Topics.update(
        {"id": "c1", "topics": [{"id": "t1", "subscription": "opt_out"}]}
    )
    assert http.calls[0]["method"] == "PATCH"
    assert http.calls[0]["path"] == "/contacts/c1/topics"
    assert http.calls[0]["body"] == [{"id": "t1", "subscription": "opt_out"}]


def test_broadcasts_lifecycle(http):
    millionsend.Broadcasts.create(
        {"segment_id": "s1", "from": "a@x.dev", "subject": "News", "html": "<p>hi</p>"}
    )
    assert http.calls[0]["path"] == "/broadcasts"
    assert http.calls[0]["body"] == {
        "segment_id": "s1",
        "from": "a@x.dev",
        "subject": "News",
        "html": "<p>hi</p>",
    }

    millionsend.Broadcasts.get("b1")
    assert http.calls[1]["path"] == "/broadcasts/b1"

    millionsend.Broadcasts.list()
    assert http.calls[2]["path"] == "/broadcasts"

    millionsend.Broadcasts.update("b1", {"subject": "New"})
    assert http.calls[3]["method"] == "PATCH"
    assert http.calls[3]["path"] == "/broadcasts/b1"

    millionsend.Broadcasts.send("b1", scheduled_at="2999-01-01T00:00:00Z")
    assert http.calls[4]["path"] == "/broadcasts/b1/send"
    assert http.calls[4]["body"] == {"scheduled_at": "2999-01-01T00:00:00Z"}

    millionsend.Broadcasts.send("b1")
    assert http.calls[5]["body"] == {}

    millionsend.Broadcasts.cancel("b1")
    assert http.calls[6]["path"] == "/broadcasts/b1/cancel"

    millionsend.Broadcasts.remove("b1")
    assert http.calls[7]["method"] == "DELETE"


def test_topics_crud(http):
    millionsend.Topics.create({"name": "Product", "default_subscription": "opt_in"})
    assert http.calls[0]["body"] == {"name": "Product", "default_subscription": "opt_in"}

    millionsend.Topics.get("t1")
    assert http.calls[1]["path"] == "/topics/t1"

    millionsend.Topics.list()
    assert http.calls[2]["path"] == "/topics"
    assert http.calls[2]["params"] is None

    millionsend.Topics.remove("t1")
    assert http.calls[3]["method"] == "DELETE"


def test_segments_crud(http):
    flt = {"match": "all", "conditions": [{"field": "email", "op": "is_set"}]}
    millionsend.Segments.create({"name": "Active", "filter": flt})
    assert http.calls[0]["path"] == "/segments"
    assert http.calls[0]["body"] == {"name": "Active", "filter": flt}

    millionsend.Segments.get("s1")
    assert http.calls[1]["path"] == "/segments/s1"

    millionsend.Segments.list(before="cur")
    assert http.calls[2]["path"] == "/segments"
    assert http.calls[2]["params"] == {"before": "cur"}

    millionsend.Segments.update("s1", {"name": "Renamed"})
    assert http.calls[3]["method"] == "PATCH"
    assert http.calls[3]["path"] == "/segments/s1"
    assert http.calls[3]["body"] == {"name": "Renamed"}

    millionsend.Segments.remove("s1")
    assert http.calls[4]["method"] == "DELETE"
