from datetime import date

from icsa import identity, scorer
from icsa.models import Evidence

YEAR = date.today().year


def commit(name, login, count=120, year=YEAR, org="ExamplePay", loc="Oakland, CA", text="ledger settlement idempotency", links=()):
    return Evidence(name, "commit", f"{count} commits to example/ledger", f"https://github.com/example/ledger/commits?author={login}",
                    f"github:{login}", f"{year}-01-15", org, loc, login, list(links), None, text, count)


def patent(name, city="Oakland, CA", org="ExamplePay, Inc.", year=YEAR, pid="12000001"):
    return Evidence(name, "patent", f"Inventor, US {pid}: payment retries", f"https://patents.google.com/patent/US{pid}",
                    f"patent-inventor:{name.lower()}|{city.lower()}", f"{year}-03-01", org, city, text="ach payment reconciliation")


def talk(name, org=None, handle=None, links=(), text="payments platform"):
    return Evidence(name, "talk", "Speaker: payouts", "https://sessionize.com/api/v2/x/view/Speakers",
                    f"sessionize:x:{name.lower()}", None, org, None, handle, list(links), None, text)


def run(evidence, role):
    return {c.key: c for c in scorer.score_all(identity.resolve(evidence), role)}


def test_same_name_merges_only_with_a_second_signal(role):
    out = run([commit("Riya Patel", "rpatel"), patent("Riya Patel")], role)
    c = out["riya patel"]
    assert c.identity_status == "verified"
    assert {"commit", "patent"} <= c.channels
    assert c.tier == "Tier 1"
    assert c.recommendation == "Strong Recommend"


def test_namesakes_are_never_merged_or_scored(role):
    # Same name, different employers and metros: the trap that mis-mapped GitHub accounts.
    out = run([commit("Sam Lee", "samlee-ke", org="Kilimo Labs", loc="Nairobi, Kenya"),
               patent("Sam Lee", city="Brooklyn, NY", org="ExamplePay, Inc.")], role)
    assert len(out) == 2
    assert all(c.identity_status == "review: possible namesake" for c in out.values())
    assert all(c.tier == "Identity review" for c in out.values())


def test_crosslink_from_talk_to_github_confirms_identity(role):
    out = run([commit("Riya Patel", "rpatel"), talk("Riya Patel", links=["https://github.com/rpatel"])], role)
    assert out["riya patel"].identity_status == "verified"


def test_neutral_repo_with_no_domain_terms_is_pending(role):
    ev = Evidence("Ana Cruz", "commit", "40 commits to example/photo-app", "https://github.com/example/photo-app/commits?author=acruz",
                  "github:acruz", f"{YEAR}-01-01", "PixelCo", "Oakland, CA", "acruz", [], None, "photo editing", 40)
    c = run([ev], role)["ana cruz"]
    assert c.tier == "Pending research"
    assert c.recommendation == ""


def test_talk_only_caps_at_tier_3(role):
    c = run([talk("Lee Chen", text="open banking payments keynote")], role)["lee chen"]
    assert c.tier == "Tier 3"


def test_patent_only_caps_at_tier_2(role):
    c = run([patent("Tom Reyes", city="Brooklyn, NY")], role)["tom reyes"]
    assert c.tier == "Tier 2"


def test_aged_domain_evidence_drops_one_tier(role):
    c = run([commit("Old Timer", "oldt", count=200, year=YEAR - 6)], role)["old timer"]
    assert c.tier == "Tier 2"
    assert any("dropped one tier" in r for r in c.tier_reasons)


def test_missing_signals_become_screen_questions(role):
    c = run([commit("Riya Patel", "rpatel", text="ledger settlement")], role)["riya patel"]
    met = {s.id for s in c.signals if s.status == "met"}
    assert "money_state" in met
    assert len(c.screen_questions) == len(role["interview_signals"]) - len(met)


def test_every_scored_lead_has_a_source(role):
    out = run([commit("Riya Patel", "rpatel"), patent("Tom Reyes")], role)
    assert all(c.sources for c in out.values())
