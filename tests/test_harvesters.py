from icsa.harvesters import github, openalex, patents, talks


def test_github_contributor_parses_profile_and_last_commit():
    ev = github.parse_contributor(
        "example/ledger",
        {"login": "rpatel", "contributions": 120, "type": "User"},
        {"name": "Riya Patel", "company": "@ExamplePay", "location": "Oakland, CA",
         "blog": "riyapatel.dev", "html_url": "https://github.com/rpatel", "bio": "ledger and settlement"},
        {"commit": {"author": {"date": "2025-06-01T10:00:00Z"}}},
    )
    assert ev.channel == "commit"
    assert ev.count == 120
    assert ev.date == "2025-06-01"
    assert "https://riyapatel.dev" in ev.links
    assert ev.url == "https://github.com/example/ledger/commits?author=rpatel"


def test_github_skips_bots_and_logins_without_a_real_name():
    assert github.parse_contributor("a/b", {"login": "dependabot[bot]", "type": "Bot"}, {"name": "Dependabot"}, None) is None
    assert github.parse_contributor("a/b", {"login": "xyz", "contributions": 50}, {"name": "xyz"}, None) is None


def test_patents_one_evidence_per_inventor_with_city():
    payload = {"patents": [{
        "patent_id": "12000001", "patent_title": "Idempotent payment retries", "patent_date": "2024-03-05",
        "patent_abstract": "Retry handling for ACH transfers",
        "inventors": [
            {"inventor_name_first": "Riya", "inventor_name_last": "Patel", "inventor_city": "Oakland", "inventor_state": "CA"},
            {"inventor_name_first": "Tom", "inventor_name_last": "Reyes", "inventor_city": "Brooklyn", "inventor_state": "NY"},
        ],
        "assignees": [{"assignee_organization": "ExamplePay, Inc."}],
    }]}
    out = list(patents.parse_patents(payload))
    assert [e.person_name for e in out] == ["Riya Patel", "Tom Reyes"]
    assert out[0].url == "https://patents.google.com/patent/US12000001"
    assert out[0].location == "Oakland, CA"
    assert out[0].org == "ExamplePay, Inc."


def test_openalex_keeps_only_authors_at_the_institution():
    inst = "https://openalex.org/I1"
    payload = {"results": [{
        "id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/x", "display_name": "Ledger at scale",
        "publication_date": "2023-05-01",
        "authorships": [
            {"author": {"id": "A1", "display_name": "Riya Patel"}, "institutions": [{"id": inst, "display_name": "ExamplePay"}]},
            {"author": {"id": "A2", "display_name": "Sam Ortiz"}, "institutions": [{"id": "https://openalex.org/I9"}]},
        ],
    }]}
    out = list(openalex.parse_works(payload, inst))
    assert [e.person_name for e in out] == ["Riya Patel"]
    assert out[0].org == "ExamplePay"


def test_sessionize_extracts_github_handle_and_org():
    out = list(talks.parse_sessionize("abc123", [{
        "id": "s1", "fullName": "Riya Patel", "tagLine": "Staff Engineer at ExamplePay",
        "links": [{"url": "https://github.com/rpatel"}], "sessions": [{"name": "Exactly-once payouts"}],
    }]))
    assert out[0].handle == "rpatel"
    assert out[0].org == "ExamplePay"
    assert out[0].channel == "talk"


def test_page_verification_needs_a_known_name():
    hits = list(talks.match_names_in_text("https://example.org/speakers", "Speakers: Riya Patel, Lee Chen", {"riya patel": "Riya Patel"}))
    assert len(hits) == 1 and hits[0].person_name == "Riya Patel"
