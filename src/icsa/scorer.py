"""Evidence scorer. Fail-closed: no evidence means no score, never a default tier.

Rules, each traceable to a lesson from tiered test candidates:
  * Evidence follows the person, not their current employer.
  * Domain evidence older than `recency_years` drops the lead one tier.
  * Talk-only evidence caps at Tier 3. Patent-only evidence caps at Tier 2.
  * Adjacent-domain work with no domain evidence is Tier 3 at most.

All wording shown to people (labels, the domain name) comes from the role
file's [labels] table, so the scorer itself is domain-neutral.
  * Unresolved namesakes get no tier until a person confirms identity.
"""

from __future__ import annotations

from .config import DEFAULT_LABELS, metro_of
from .models import STRONG_CHANNELS, Candidate, Check, Evidence, today_year

TIERS = ["Tier 1", "Tier 2", "Tier 3"]


def _labels(role: dict) -> dict:
    return {**DEFAULT_LABELS, **role.get("labels", {})}


def _recommendation(tier: str, labels: dict) -> str:
    return {"Tier 1": labels["tier1"], "Tier 2": labels["tier2"], "Tier 3": labels["tier3"]}.get(tier, "")


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


def _signal_summary(c: Candidate, role: dict) -> None:
    weights = {s["id"]: float(s.get("weight", 1.0)) for s in role.get("interview_signals", [])}
    total = sum(weights.values()) or 1.0
    c.signal_score = round(sum(weights[s.id] for s in c.signals if s.status == "met") / total, 3)
    c.screen_questions = [
        s["screen_question"] for s, chk in zip(role.get("interview_signals", []), c.signals)
        if chk.status != "met" and s.get("screen_question")
    ]


def apply_judge(c: Candidate, role: dict, judge) -> None:
    """Ask the AI judge to confirm each keyword-flagged signal. Fail-closed on 'no'/'unclear',
    fail-open (keep the keyword result, with a note) only when the judge itself is unavailable."""
    by_id = {s["id"]: s for s in role.get("interview_signals", [])}
    for chk in c.signals:
        if chk.status != "met":
            continue
        sig = by_id[chk.id]
        hits = [e for e in c.evidence if _matches(e, sig.get("terms", []))][: judge.max_evidence]
        verdicts = [(e, judge.judge(sig, e)) for e in hits]
        confirmed = [(e, v) for e, v in verdicts if v.verdict == "yes"]
        if confirmed:
            e, v = confirmed[0]
            chk.sources = [e.url for e, _ in confirmed][:5]
            chk.note = f'AI-confirmed: "{v.quote}"'
        elif verdicts and all(v.verdict == "error" for _, v in verdicts):
            chk.note = "AI judge unavailable; keyword match only"
        else:
            chk.status = "no evidence"
            chk.sources = []
            chk.note = "Keyword match not confirmed by AI judge"
    _signal_summary(c, role)


def _drop(tier: str) -> str:
    return TIERS[min(TIERS.index(tier) + 1, 2)]


def score(c: Candidate, role: dict, judge=None) -> Candidate:
    cfg = role.get("role", {})
    labels = _labels(role)
    domain_name = labels["domain_name"]
    recency = int(cfg.get("recency_years", 3))

    c.requirements = [_check(r, c.evidence, recency) for r in role.get("requirements", [])]
    c.signals = [_check(s, c.evidence, recency) for s in role.get("interview_signals", [])]
    _signal_summary(c, role)

    reasons: list[str] = []
    by_kind = {r["id"]: r.get("kind", "core") for r in role.get("requirements", [])}
    domain = [chk for chk in c.requirements if by_kind.get(chk.id) == "domain"]
    adjacent = [chk for chk in c.requirements if by_kind.get(chk.id) == "adjacent"]
    domain_terms = [t for r in role.get("requirements", []) if r.get("kind") == "domain" for t in r.get("terms", [])]
    domain_ev = [e for e in c.evidence if _matches(e, domain_terms)]

    if c.identity_status.startswith("review"):
        c.tier, c.recommendation = labels["identity_review"], ""
        c.tier_reasons = ["Same name as another record with no second matching signal; confirm before scoring"]
        return c

    if not domain_ev:
        if any(chk.status != "no evidence" for chk in adjacent):
            c.tier, c.recommendation = "Tier 3", labels["tier3"]
            c.tier_reasons = [f"Adjacent-domain work only; no {domain_name} evidence"]
        else:
            c.tier, c.recommendation = labels["pending"], ""
            c.tier_reasons = [f"No {domain_name} evidence found yet; not scored"]
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
        reasons.append(f"{domain_name.capitalize()} evidence across {', '.join(sorted(channels))}" + (f"; {commits} commits" if commits else ""))
    else:
        tier = "Tier 2"
        reasons.append(f"{domain_name.capitalize()} evidence from one channel ({', '.join(sorted(channels))})")

    if channels == {"patent"} and tier == "Tier 1":
        tier = "Tier 2"
        reasons.append("Patent only, little public code; caps at Tier 2")

    if any(chk.status == "not met (aged)" for chk in domain):
        last = max((chk.last_seen for chk in domain if chk.last_seen), default="unknown")
        tier = _drop(tier)
        reasons.append(f"{domain_name.capitalize()} evidence last seen {last[:4] if last else 'unknown'}; dropped one tier")

    metros = {metro_of(e.location) for e in c.evidence if e.location}
    wanted = set(cfg.get("metros", []))
    if wanted and not (metros & wanted):
        reasons.append("Location not found" if not metros else "Location outside target metros")

    if c.identity_status == "verified":
        reasons.append("Identity confirmed by two independent signals")

    c.tier, c.recommendation, c.tier_reasons = tier, _recommendation(tier, labels), reasons
    if judge is not None and tier in ("Tier 1", "Tier 2"):
        apply_judge(c, role, judge)
    return c


def score_all(candidates: list[Candidate], role: dict, judge=None) -> list[Candidate]:
    labels = _labels(role)
    order = {t: i for i, t in enumerate(TIERS + [labels["identity_review"], labels["pending"]])}
    scored = [score(c, role, judge) for c in candidates]
    return sorted(scored, key=lambda c: (order.get(c.tier, 9), -c.signal_score, c.name))
