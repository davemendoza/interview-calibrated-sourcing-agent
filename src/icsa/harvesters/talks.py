"""Conference and meetup talks.

Sessionize events expose a public JSON speaker list, so they can create leads.
Plain speaker pages are only used to verify people already found elsewhere:
a name on a web page is not enough to create a lead.
"""

from __future__ import annotations

import re
from typing import Iterable, Iterator

from bs4 import BeautifulSoup

from ..http import Http
from ..models import Evidence, normalize_name

SESSIONIZE = "https://sessionize.com/api/v2/{id}/view/Speakers"


def _org_from_tagline(tagline: str) -> str | None:
    m = re.search(r"(?:\bat\b|@|,)\s*([A-Z][\w&.\- ]{1,40})\s*$", tagline or "")
    return m.group(1).strip() if m else None


def parse_sessionize(event_id: str, speakers: list[dict]) -> Iterator[Evidence]:
    page = f"https://sessionize.com/api/v2/{event_id}/view/Speakers"
    for s in speakers or []:
        name = (s.get("fullName") or "").strip()
        if not name or " " not in name:
            continue
        sessions = [x.get("name", "") for x in s.get("sessions") or []]
        links = [l.get("url") for l in s.get("links") or [] if l.get("url")]
        handle = None
        for u in links:
            m = re.match(r"https?://(?:www\.)?github\.com/([A-Za-z0-9-]+)/?$", u)
            if m:
                handle = m.group(1)
        tagline = s.get("tagLine") or ""
        yield Evidence(
            person_name=name,
            channel="talk",
            title=f"Speaker: {'; '.join(sessions) or 'session'}",
            url=page,
            source_key=f"sessionize:{event_id}:{s.get('id') or name.lower()}",
            org=_org_from_tagline(tagline),
            handle=handle,
            links=links,
            text=f"{tagline} {s.get('bio') or ''} {' '.join(sessions)}",
        )


def verify_on_pages(pages: Iterable[str], known_names: Iterable[str], http: Http | None = None) -> Iterator[Evidence]:
    """Add talk evidence for already-known people named on agenda pages."""
    http = http or Http()
    wanted = {normalize_name(n): n for n in known_names if n}
    for url in pages:
        text = BeautifulSoup(http.get_text(url), "html.parser").get_text(" ")
        yield from match_names_in_text(url, text, wanted)


def match_names_in_text(url: str, text: str, wanted: dict[str, str]) -> Iterator[Evidence]:
    flat = normalize_name_text(text)
    for norm, original in wanted.items():
        if norm and f" {norm} " in flat:
            yield Evidence(
                person_name=original,
                channel="talk",
                title=f"Named on speaker page: {url}",
                url=url,
                source_key=f"page:{url}:{norm}",
            )


def normalize_name_text(text: str) -> str:
    words = [normalize_name(w) for w in re.split(r"\s+", text)]
    return " " + " ".join(w for w in words if w) + " "


def harvest(cfg: dict, http: Http | None = None) -> Iterator[Evidence]:
    http = http or Http()
    for event_id in cfg.get("sessionize_ids", []):
        speakers = http.get_json(SESSIONIZE.format(id=event_id))
        yield from parse_sessionize(event_id, speakers)
