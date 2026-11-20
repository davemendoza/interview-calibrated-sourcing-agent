"""Core data shapes: one Evidence item per public fact, one Candidate per person."""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date

STRONG_CHANNELS = {"commit", "patent", "paper", "blog", "package"}
CHANNELS = STRONG_CHANNELS | {"talk"}


def normalize_name(name: str) -> str:
    """Lowercase, strip accents, drop middle initials and punctuation."""
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^a-z\s-]", " ", text)
    parts = [p for p in text.replace("-", " ").split() if len(p) > 1]
    if len(parts) > 2:
        parts = [parts[0], parts[-1]]
    return " ".join(parts)


def normalize_org(org: str | None) -> str:
    if not org:
        return ""
    text = org.lower().strip().lstrip("@")
    text = re.sub(r"[,.]|\b(inc|llc|ltd|corp|corporation|co|the|united states)\b", " ", text)
    text = re.sub(r"\(.*?\)", " ", text)
    return " ".join(text.split())


@dataclass
class Evidence:
    """One public, linkable fact about a person."""

    person_name: str
    channel: str  # commit, patent, paper, talk, blog, package
    title: str
    url: str
    source_key: str  # stable id of the account or record this came from
    date: str | None = None  # YYYY-MM-DD of the most recent activity
    org: str | None = None
    location: str | None = None
    handle: str | None = None  # GitHub login when known
    links: list[str] = field(default_factory=list)  # self-published links (site, GitHub)
    email: str | None = None  # only when the person published it themselves
    text: str = ""  # searchable text used for requirement and signal matching
    count: int = 0  # commits, for commit evidence

    def __post_init__(self) -> None:
        if self.channel not in CHANNELS:
            raise ValueError(f"unknown channel: {self.channel}")
        if not self.url:
            raise ValueError("evidence must carry a source URL (no source, no score)")

    @property
    def year(self) -> int | None:
        if self.date and re.match(r"^\d{4}", self.date):
            return int(self.date[:4])
        return None

    def searchable(self) -> str:
        return f" {self.title} {self.text} {self.org or ''} ".lower()

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, line: str) -> "Evidence":
        return cls(**json.loads(line))


@dataclass
class Check:
    """Result of checking one requirement or interview signal."""

    id: str
    label: str
    status: str  # "met", "not met (aged)", "no evidence"
    sources: list[str] = field(default_factory=list)
    last_seen: str | None = None


@dataclass
class Candidate:
    key: str
    name: str
    evidence: list[Evidence] = field(default_factory=list)
    identity_status: str = "single source"
    identity_notes: list[str] = field(default_factory=list)
    tier: str = ""
    recommendation: str = ""
    tier_reasons: list[str] = field(default_factory=list)
    requirements: list[Check] = field(default_factory=list)
    signals: list[Check] = field(default_factory=list)
    signal_score: float = 0.0
    screen_questions: list[str] = field(default_factory=list)

    @property
    def channels(self) -> set[str]:
        return {e.channel for e in self.evidence}

    @property
    def sources(self) -> list[str]:
        seen: list[str] = []
        for e in self.evidence:
            if e.url not in seen:
                seen.append(e.url)
        return seen

    def best(self, attr: str) -> str | None:
        """Most recent non-empty value of an Evidence attribute."""
        ranked = sorted(self.evidence, key=lambda e: e.date or "", reverse=True)
        for e in ranked:
            value = getattr(e, attr)
            if value:
                return value
        return None

    @property
    def latest_date(self) -> str | None:
        dates = [e.date for e in self.evidence if e.date]
        return max(dates) if dates else None


def today_year() -> int:
    return date.today().year
