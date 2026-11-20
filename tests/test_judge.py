"""The AI judge, tested with a simulated model. No network calls."""

import json
from datetime import date

from icsa import evaluate, identity, scorer
from icsa.judge import Judge
from icsa.models import Evidence

Y = date.today().year


def fake_model(reply: dict | Exception):
    calls = []

    def transport(payload):
        calls.append(payload)
        if isinstance(reply, Exception):
            raise reply
        return {"content": [{"type": "text", "text": json.dumps(reply)}]}

    transport.calls = calls
    return transport


def lead(text):
    return Evidence("Riya Patel", "commit", "142 commits to example/ledger-core", "https://github.com/example/ledger-core",
                    "github:rpatel", f"{Y}-03-01", "ExamplePay", "Oakland, CA", "rpatel", [], None, text, 142)


def money_state(c):
    return next(s for s in c.signals if s.id == "money_state")


def run(role, text, transport):
    judge = Judge(transport=transport, cache_dir=None)
    return scorer.score_all(identity.resolve([lead(text)]), role, judge)[0], judge


TEXT = "Built idempotency keys so retried ACH payouts settle exactly once after a timeout."


def test_confirmed_signal_keeps_its_quote(role):
    t = fake_model({"verdict": "yes", "quote": "retried ACH payouts settle exactly once", "reason": "clear"})
    c, _ = run(role, TEXT, t)
    assert money_state(c).status == "met"
    assert "AI-confirmed" in money_state(c).note
    assert t.calls[0]["model"] == "claude-haiku-5-5"


def test_invented_quote_is_rejected(role):
    t = fake_model({"verdict": "yes", "quote": "designed the bank's global ledger", "reason": "made up"})
    c, _ = run(role, TEXT, t)
    assert money_state(c).status == "no evidence"
    assert "not confirmed" in money_state(c).note
    assert any("exactly once" in q for q in c.screen_questions)


def test_model_saying_no_removes_a_keyword_match(role):
    c, _ = run(role, "Fixed a typo in the ledger README.", fake_model({"verdict": "no", "quote": "", "reason": "trivial"}))
    assert money_state(c).status == "no evidence"


def test_judge_outage_keeps_keyword_result_with_a_note(role):
    c, _ = run(role, TEXT, fake_model(RuntimeError("network down")))
    assert money_state(c).status == "met"
    assert "unavailable" in money_state(c).note


def test_only_tier_1_and_2_are_judged(role):
    talk = Evidence("Lee Chen", "talk", "Speaker: open banking payments", "https://example.org/s", "page:x", text="ledger idempotency")
    t = fake_model({"verdict": "yes", "quote": "ledger idempotency", "reason": ""})
    c = scorer.score_all(identity.resolve([talk]), role, Judge(transport=t, cache_dir=None))[0]
    assert c.tier == "Tier 3" and t.calls == []


def test_pilot_summary_has_no_names():
    rep = evaluate.Report(
        metrics={"wrong_person_rate": 0.0, "tier_agreement": 0.75, "new_tier1_or_2_finds": 4},
        rows=[
            {"Name": "Riya Patel", "Your tier": "Tier 1", "Surfaced": "Yes", "Agent tier": "Tier 1"},
            {"Name": "Tom Reyes", "Your tier": "Tier 1", "Surfaced": "No", "Agent tier": "Not ranked"},
            {"Name": "Sam Lee", "Your tier": "Trap", "Surfaced": "Yes", "Agent tier": "Identity review"},
        ],
    )
    s = evaluate.pilot_summary(rep)
    assert s.startswith("Found 1 of my 2 known Tier 1 engineers")
    assert "kept 1 of 1 traps out of Tier 1" in s and "surfaced 4 new" in s
    assert not any(n in s for n in ("Riya", "Tom", "Sam"))
