"""Engineering blogs via RSS or Atom feeds.

A byline on a post about a ledger migration or an incident is strong evidence
of the exact signals interviews test. Only feeds that name their authors can
create leads; feeds without authors belong in the ecosystem as taxonomy.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Iterator

from ..http import Http
from ..models import Evidence, looks_like_person

ATOM = "{http://www.w3.org/2005/Atom}"
DC = "{http://purl.org/dc/elements/1.1/}"


def _text(el) -> str:
    return (el.text or "").strip() if el is not None else ""


def _clean(html: str) -> str:
    """Visible text only. Text hidden with CSS or HTML attributes is not scored; when it
    holds instructions or stuffed keywords, a note is kept so icsa.guard holds the item."""
    from .. import guard

    text, findings = guard.split_hidden_html(html or "")
    flagged = [f.excerpt for f in findings if f.severity == guard.HIGH and f.excerpt]
    if flagged:
        text = f"{text} [hidden page text: {' / '.join(flagged)}]"
    return text


def _authors_rss(item) -> list[str]:
    names = [_text(a) for a in item.findall(f"{DC}creator")]
    raw = _text(item.find("author"))
    if raw:
        # RSS <author> is often "email (Name)"
        m = re.search(r"\(([^)]+)\)", raw)
        names.append(m.group(1) if m else raw)
    return [n for n in names if n]


def parse_feed(xml_text: str, feed_url: str, org: str | None = None) -> Iterator[Evidence]:
    root = ET.fromstring(xml_text)
    if root.tag == f"{ATOM}feed":
        feed_title = _text(root.find(f"{ATOM}title"))
        items = [
            (
                _text(e.find(f"{ATOM}title")),
                next((l.get("href") for l in e.findall(f"{ATOM}link") if l.get("rel") in (None, "alternate")), ""),
                (_text(e.find(f"{ATOM}published")) or _text(e.find(f"{ATOM}updated")))[:10],
                [_text(a.find(f"{ATOM}name")) for a in e.findall(f"{ATOM}author")],
                _clean(_text(e.find(f"{ATOM}summary")) or _text(e.find(f"{ATOM}content")))[:1500],
            )
            for e in root.findall(f"{ATOM}entry")
        ]
    else:
        channel = root.find("channel")
        if channel is None:
            return
        feed_title = _text(channel.find("title"))
        items = []
        for it in channel.findall("item"):
            date = _text(it.find(f"{DC}date"))[:10] or _rss_date(_text(it.find("pubDate")))
            items.append((_text(it.find("title")), _text(it.find("link")), date, _authors_rss(it),
                          _clean(_text(it.find("description")))[:1500]))

    for title, link, date, authors, summary in items:
        if not link:
            continue
        for name in authors:
            for person in re.split(r",| and ", name):
                person = person.strip()
                if not looks_like_person(person):
                    continue
                yield Evidence(
                    person_name=person,
                    channel="blog",
                    title=f"Author: {title} ({feed_title})",
                    url=link,
                    source_key=f"blog:{feed_url}:{person.lower()}",
                    date=date or None,
                    org=org,
                    text=summary,
                )


_MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _rss_date(s: str) -> str:
    m = re.search(r"(\d{1,2}) (\w{3}) (\d{4})", s or "")
    if not m or m.group(2).lower() not in _MONTHS:
        return ""
    return f"{m.group(3)}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"


def harvest(cfg: dict, http: Http | None = None) -> Iterator[Evidence]:
    http = http or Http()
    for feed in cfg.get("feeds", []):
        url = feed["url"] if isinstance(feed, dict) else feed
        org = feed.get("org") if isinstance(feed, dict) else None
        yield from parse_feed(http.get_text(url), url, org)
