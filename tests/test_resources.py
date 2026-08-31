"""Method + path + body + query mapping for every resource, over the mock layer."""

from urllib.parse import quote

import pytest

import millionsend


def test_emails_get_and_cancel(http):
    millionsend.Emails.get("e1")
    assert http.calls[0]["method"] == "GET"
    assert http.calls[0]["path"] == "/emails/e1"

    millionsend.Emails.cancel("e1")
    assert http.calls[1]["method"] == "POST"
    assert http.calls[1]["path"] == "/emails/e1/cancel"


def test_emails_get_score_present_and_null(http):
    http.body = {"object": "email", "id": "e1", "score": 8.5}
    assert millionsend.Emails.get("e1").score == 8.5

    http.body = {"object": "email", "id": "e1", "score": None}
    assert millionsend.Emails.get("e1").score is None


def test_emails_get_insights_full_shape(http):
    http.body = {
        "object": "email_insights",
        "email_id": "e1",
        "score": 8.5,
        "score_version": 1,
        "band": "excellent",
        "marketing": True,
        "html_size_bytes": 12345,
        "computed_at": "2026-08-31T00:00:00Z",
        "checks": [
            {
                "id": "list_unsubscribe",
                "severity": "major",
                "status": "fail",
                "penalty": 1.25,
                "detail": {"reason": "missing header"},
            },
            {"id": "plain_text_part", "severity": "minor", "status": "pass", "penalty": 0},
        ],
    }
    res = millionsend.Emails.get_insights("e1")
    assert http.calls[0]["method"] == "GET"
    assert http.calls[0]["path"] == "/emails/e1/insights"
    assert res.object == "email_insights"
    assert res.email_id == "e1"
    assert res.score == 8.5
    assert res.score_version == 1
    assert res.band == "excellent"
    assert res.marketing is True
    assert res.html_size_bytes == 12345
    assert res.computed_at == "2026-08-31T00:00:00Z"
    assert res.checks[0].id == "list_unsubscribe"
    assert res.checks[0].severity == "major"
    assert res.checks[0].status == "fail"
    assert res.checks[0].penalty == 1.25
    assert res.checks[0].detail.reason == "missing header"
    assert "detail" not in res.checks[1]
    # open enums: unknown future band/status values pass through untouched
    http.body = {
        "object": "email_insights",
        "band": "stellar",
        "checks": [{"id": "new_check_v9", "severity": "info", "status": "deferred", "penalty": 0}],
    }
    res = millionsend.Emails.get_insights("e1")
    assert res.band == "stellar"
    assert res.checks[0].status == "deferred"


def test_emails_get_insights_404(http):
    http.status = 404
    http.body = {"statusCode": 404, "name": "not_found", "message": "no insights"}
    with pytest.raises(millionsend.NotFoundError):
        millionsend.Emails.get_insights("e1")


def test_deliverability_get(http):
    http.body = {
        "object": "deliverability",
        "score": 8.7,
        "band": "good",
        "content_score": 8.2,
        "outcome_score": 9.1,
        "complaint_rate": 0.0002,
        "hard_bounce_rate": 0.001,
        "emails_sent": 12345,
        "scored_recipients": 23456,
        "window_days": 30,
        "insufficient_outcome_data": False,
        "guardrail_status": "ok",
        "score_version": 1,
    }
    res = millionsend.Deliverability.get()
    assert http.calls[0]["method"] == "GET"
    assert http.calls[0]["path"] == "/deliverability"
    assert res.score == 8.7
    assert res.band == "good"
    assert res.content_score == 8.2
    assert res.outcome_score == 9.1
    assert res.complaint_rate == 0.0002
    assert res.hard_bounce_rate == 0.001
    assert res.emails_sent == 12345
    assert res.scored_recipients == 23456
    assert res.window_days == 30
    assert res.insufficient_outcome_data is False
    assert res.guardrail_status == "ok"
    assert res.score_version == 1

    http.body = {"object": "deliverability", "score": None, "band": None, "guardrail_status": "paused"}
    res = millionsend.Deliverability.get()
    assert res.score is None
    assert res.band is None
    assert res.guardrail_status == "paused"


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
