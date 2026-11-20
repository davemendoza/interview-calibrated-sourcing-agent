"""Evidence scorer. Fail-closed: no evidence means no score, never a default tier.

Rules, each traceable to a lesson from tiered test candidates:
  * Evidence follows the person, not their current employer.
  * Domain evidence older than `recency_years` drops the lead one tier.
  * Talk-only evidence caps at Tier 3. Patent-only evidence caps at Tier 2.
  * Adjacent-domain work with no payments evidence is Tier 3 at most.
  * Unresolved namesakes get no tier until a person confirms identity.
"""

from __future__ import annotations

from .config import metro_of
from .models import STRONG_CHANNELS, Candidate, Check, Evidence, today_year

RECOMMENDATION = {
    "Tier 1": "Strong Recommend",
    "Tier 2": "Recommend",
    "Tier 3": "Pipeline depth",
}
TIERS = ["Tier 1", "Tier 2", "Tier 3"]


def _matches(e: Evidence, terms: list[str]) -> bool:
    text = e.searchable()
    return any(t.lower() in text for t in terms)


def _check(item: dict, evidence: list[Evidence], recency_years: int) -> Check:
    hits = [e for e in evidence if _matches(e, item.get("terms", []))]
    if not hits:
        return Check(item["id"], item["label"], "no evidence")
    last = max((e.date for e in hits if e.date), default=None)
    recent = last is None or int(last[:4]) >= today_year() - recency_years
    status = "met" if recent else "not met (aged)"
    return Check(item["id"], item["label"], status, [e.url for e in hits][:5], last)


def _drop(tier: str) -> str:
    return TIERS[min(TIERS.index(tier) + 1, 2)]


def score(c: Candidate, role: dict) -> Candidate:
    cfg = role.get("role", {})
    recency = int(cfg.get("recency_years", 3))

    c.requirements = [_check(r, c.evidence, recency) for r in role.get("requirements", [])]
    c.signals = [_check(s, c.evidence, recency) for s in role.get("interview_signals", [])]

    weights = {s["id"]: float(s.get("weight", 1.0)) for s in role.get("interview_signals", [])}
    total = sum(weights.values()) or 1.0
    c.signal_score = round(sum(weights[s.id] for s in c.signals if s.status == "met") / total, 3)
    c.screen_questions = [
        s["screen_question"] for s, chk in zip(role.get("interview_signals", []), c.signals)
        if chk.status != "met" and s.get("screen_question")
    ]

    reasons: list[str] = []
    by_kind = {r["id"]: r.get("kind", "core") for r in role.get("requirements", [])}
    domain = [chk for chk in c.requirements if by_kind.get(chk.id) == "domain"]
    adjacent = [chk for chk in c.requirements if by_kind.get(chk.id) == "adjacent"]
    domain_terms = [t for r in role.get("requirements", []) if r.get("kind") == "domain" for t in r.get("terms", [])]
    domain_ev = [e for e in c.evidence if _matches(e, domain_terms)]

    if c.identity_status.startswith("review"):
        c.tier, c.recommendation = "Identity review", ""
        c.tier_reasons = ["Same name as another record with no second matching signal; confirm before scoring"]
        return c

    if not domain_ev:
        if any(chk.status != "no evidence" for chk in adjacent):
            c.tier, c.recommendation = "Tier 3", RECOMMENDATION["Tier 3"]
            c.tier_reasons = ["Adjacent-domain work only; no payments evidence"]
        else:
            c.tier, c.recommendation = "Pending research", ""
            c.tier_reasons = ["No domain evidence found yet; not scored"]
        return c

    channels = {e.channel for e in domain_ev}
    strong = channels & STRONG_CHANNELS
    commits = sum(e.count for e in domain_ev if e.channel == "commit")
    min_channels = int(cfg.get("tier1_min_channels", 2))
    min_commits = int(cfg.get("tier1_min_commits", 75))

    if not strong:
        tier = "Tier 3"
        reasons.append("Talk evidence only; caps at Tier 3")
    elif len(channels) >= min_channels or commits >= min_commits:
        tier = "Tier 1"
        reasons.append(f"Domain evidence across {', '.join(sorted(channels))}" + (f"; {commits} commits" if commits else ""))
    else:
        tier = "Tier 2"
        reasons.append(f"Domain evidence from one channel ({', '.join(sorted(channels))})")

    if channels == {"patent"} and tier == "Tier 1":
        tier = "Tier 2"
        reasons.append("Patent only, little public code; caps at Tier 2")

    if any(chk.status == "not met (aged)" for chk in domain):
        last = max((chk.last_seen for chk in domain if chk.last_seen), default="unknown")
        tier = _drop(tier)
        reasons.append(f"Domain evidence last seen {last[:4] if last else 'unknown'}; dropped one tier")

    metros = {metro_of(e.location) for e in c.evidence if e.location}
    wanted = set(cfg.get("metros", []))
    if wanted and not (metros & wanted):
        reasons.append("Location not found" if not metros else "Location outside target metros")

    if c.identity_status == "verified":
        reasons.append("Identity confirmed by two independent signals")

    c.tier, c.recommendation, c.tier_reasons = tier, RECOMMENDATION[tier], reasons
    return c


def score_all(candidates: list[Candidate], role: dict) -> list[Candidate]:
    order = {t: i for i, t in enumerate(TIERS + ["Identity review", "Pending research"])}
    scored = [score(c, role) for c in candidates]
    return sorted(scored, key=lambda c: (order.get(c.tier, 9), -c.signal_score, c.name))
