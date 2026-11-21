"""Ecosystem map, blog and package harvesters, and the taxonomy command. Fictional data."""

from icsa import ecosystem, taxonomy
from icsa.config import load_role
from icsa.harvesters import blogs, packages
from conftest import ROOT

ATOM = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Example Eng</title>
<entry><title>Reconciling ledgers after a timeout</title><link href="https://eng.example.com/recon"/>
<updated>2026-05-02T00:00:00Z</updated><author><name>Riya Patel</name></author>
<summary>&lt;p&gt;How we made payout retries idempotent.&lt;/p&gt;</summary></entry>
<entry><title>Team update</title><link href="https://eng.example.com/team"/><updated>2026-04-01T00:00:00Z</updated>
<author><name>Example Team</name></author></entry>
</feed>"""

RSS_DC = """<?xml version="1.0"?><rss xmlns:dc="http://purl.org/dc/elements/1.1/"><channel><title>Pay Blog</title>
<item><title>Settlement at scale</title><link>https://pay.example.com/settle</link><dc:creator>Tom Reyes</dc:creator>
<pubDate>Tue, 03 Mar 2026 10:00:00 GMT</pubDate><description>ACH settlement windows</description></item>
</channel></rss>"""

RSS_NO_AUTHOR = """<?xml version="1.0"?><rss><channel><title>Corp Blog</title>
<item><title>Launch</title><link>https://corp.example.com/launch</link></item></channel></rss>"""


def test_atom_feed_yields_named_authors_only():
    out = list(blogs.parse_feed(ATOM, "https://eng.example.com/feed.xml", org="ExamplePay"))
    assert [e.person_name for e in out] == ["Riya Patel"]  # "Example Team" is not a person
    e = out[0]
    assert e.channel == "blog" and e.date == "2026-05-02" and e.org == "ExamplePay"
    assert "idempotent" in e.text and "<p>" not in e.text


def test_rss_dc_creator_and_date():
    e = next(blogs.parse_feed(RSS_DC, "https://pay.example.com/rss"))
    assert e.person_name == "Tom Reyes" and e.date == "2026-03-03"


def test_feed_without_authors_creates_no_leads():
    assert list(blogs.parse_feed(RSS_NO_AUTHOR, "https://corp.example.com/rss")) == []


def test_pypi_person_kept_company_skipped():
    person = {"info": {"name": "ach-tools", "author": "Lee Chen", "maintainer": "ExamplePay Inc",
                       "project_urls": {"Source": "https://github.com/leechen/ach-tools"}, "summary": "ACH files"},
              "releases": {"1.0": [{"upload_time": "2026-02-01T00:00:00"}]}}
    out = list(packages.parse_pypi(person))
    assert [e.person_name for e in out] == ["Lee Chen"]
    assert "https://github.com/leechen/ach-tools" in out[0].links and out[0].date == "2026-02-01"


def test_npm_author_with_repo_link():
    e = next(packages.parse_npm({"name": "iso-msg", "author": {"name": "Mei Lindqvist"},
                                 "repository": {"url": "git+https://github.com/mlind/iso-msg.git"},
                                 "time": {"modified": "2026-06-10T00:00:00Z"}}))
    assert e.links == ["https://github.com/mlind/iso-msg"] and e.date == "2026-06-10"


def test_fintech_example_ecosystem_routes_to_harvesters():
    role = load_role(ROOT / "config/roles/example_fintech_staff_payments_engineer.toml", calibration=None)
    src = role["sources"]
    assert "moov-io/ach" in src["github"]["repos"]
    assert "Stripe, Inc." in src["patents"]["assignees"]
    assert src["blogs"]["feeds"][0]["url"] == "https://code.cash.app/feed.xml"
    assert "https://fintechdevcon.io" in src["talks"]["pages"]
    assert "https://www.nacha.org/rules" in role["taxonomy_pages"]
    assert ecosystem.check(role) == []
    missing = [c for c, n, _, _ in ecosystem.coverage(role) if n == 0]
    assert "meetups" in missing and "packages" in missing


def test_bad_entries_get_plain_language_errors():
    role = {"ecosystem": [
        {"category": "code", "name": "x", "use": "harvest", "source": "github_repo"},
        {"category": "meetups", "name": "y", "use": "verify", "url": "not a url"},
        {"category": "nope", "name": "z", "use": "maybe"},
    ], "sources": {}}
    text = " ".join(ecosystem.check(role))
    assert "need a value" in text and "need a full url" in text and "category must be" in text
    assert "use must be" in text and "nowhere to search" in text


def test_taxonomy_suggests_uncovered_recurring_phrases():
    texts = {
        "https://a.example": "Same Day ACH entries settle by settlement date. Same Day ACH return reason codes.",
        "https://b.example": "Return reason codes and Same Day ACH limits. Payee name verification for instant payments.",
    }
    out = taxonomy.suggest_terms(texts, existing_terms=["ach"])
    phrases = [p for p, _, _ in out]
    assert "return reason codes" in phrases
    assert not any("ach" == p for p in phrases)  # already covered
