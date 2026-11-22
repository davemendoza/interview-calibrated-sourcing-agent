"""Harvest, resolve identity, score, write. Each stage can run on its own."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from . import guard, identity, output, scorer
from .harvesters import blogs, github, openalex, packages, patents, talks
from .models import Candidate, Evidence, normalize_name

HARVESTERS = {
    "github": github.harvest,
    "patents": patents.harvest,
    "openalex": openalex.harvest,
    "talks": talks.harvest,
    "blogs": blogs.harvest,
    "packages": packages.harvest,
}


def harvest(role: dict, evidence_path: Path, only: list[str] | None = None) -> int:
    sources = role.get("sources", {})
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    collected: list[Evidence] = []
    for name, fn in HARVESTERS.items():
        if only and name not in only:
            continue
        cfg = sources.get(name)
        if not cfg:
            continue
        before = len(collected)
        try:
            collected.extend(fn(cfg))
        except Exception as exc:  # one source failing must not stop the others
            print(f"[{name}] skipped: {exc}", file=sys.stderr)
        print(f"[{name}] {len(collected) - before} evidence items", file=sys.stderr)

    pages = sources.get("talks", {}).get("pages") or []
    if pages and (not only or "talks" in only):
        known = sorted({e.person_name for e in collected})
        try:
            found = list(talks.verify_on_pages(pages, known))
            collected.extend(found)
            print(f"[talk pages] {len(found)} talks verified for known people", file=sys.stderr)
        except Exception as exc:
            print(f"[talk pages] skipped: {exc}", file=sys.stderr)

    with evidence_path.open("w", encoding="utf-8") as f:
        for e in collected:
            f.write(e.to_json() + "\n")
    return len(collected)


def load_evidence(path: Path) -> list[Evidence]:
    with path.open(encoding="utf-8") as f:
        return [Evidence.from_json(line) for line in f if line.strip()]


def score(role: dict, evidence_path: Path, out_dir: Path, judge=None) -> list:
    kept, held, notes = guard.screen(load_evidence(evidence_path))
    candidates = scorer.score_all(identity.resolve(kept), role, judge)
    candidates = apply_integrity(candidates, held, notes, role)
    if held:
        print(f"[guard] {len(held)} evidence item(s) held back for review; see {out_dir}/integrity.csv", file=sys.stderr)
    if judge is not None:
        print(f"[judge] {judge.calls} AI judgments ({judge.model})", file=sys.stderr)
    out_dir.mkdir(parents=True, exist_ok=True)
    output.write_csv(candidates, out_dir / "leads.csv")
    output.write_xlsx(candidates, out_dir / "leads.xlsx")
    write_signal_matrix(candidates, role, out_dir / "signal_matrix.csv")
    output.write_integrity(held, out_dir / "integrity.csv")
    return candidates


def apply_integrity(candidates: list[Candidate], held: list, notes: dict[str, list[str]], role: dict) -> list[Candidate]:
    """Attach guard findings to people. A person with held-back evidence cannot stay
    Tier 1 without a human looking, and a person whose only evidence was held back
    still appears, labelled for review, instead of silently vanishing."""
    labels = scorer._labels(role)
    by_name = {normalize_name(c.name): c for c in candidates}
    for name, lines in notes.items():
        if name in by_name:
            by_name[name].integrity_flags += lines
    for h in held:
        name = normalize_name(h.evidence.person_name)
        c = by_name.get(name)
        if c is None:
            c = Candidate(key=name, name=h.evidence.person_name, tier=labels["integrity_review"],
                          recommendation="Review evidence before any outreach",
                          tier_reasons=["All evidence found for this person was held back by the integrity guard"])
            by_name[name] = c
            candidates.append(c)
        c.integrity_flags += [f"held back ({h.evidence.channel}): {r}" for r in h.reasons]
        if c.tier == "Tier 1":
            c.tier = "Tier 2"
            c.recommendation = scorer._recommendation(c.tier, labels)
            c.tier_reasons.append("Held below Tier 1: some evidence was held back by the integrity guard; review it first")
    order = {t: i for i, t in enumerate(scorer.TIERS + [labels["identity_review"], labels["integrity_review"], labels["pending"]])}
    return sorted(candidates, key=lambda c: (order.get(c.tier, 9), -c.signal_score, c.name))


def write_signal_matrix(candidates: list, role: dict, path: Path) -> None:
    ids = [s["id"] for s in role.get("interview_signals", [])]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Tier", *ids])
        for c in candidates:
            status = {s.id: s.status for s in c.signals}
            w.writerow([c.name, c.tier, *[status.get(i, "") for i in ids]])
