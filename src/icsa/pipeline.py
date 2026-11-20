"""Harvest, resolve identity, score, write. Each stage can run on its own."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from . import identity, output, scorer
from .harvesters import github, openalex, patents, talks
from .models import Evidence

HARVESTERS = {
    "github": github.harvest,
    "patents": patents.harvest,
    "openalex": openalex.harvest,
    "talks": talks.harvest,
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


def score(role: dict, evidence_path: Path, out_dir: Path) -> list:
    candidates = scorer.score_all(identity.resolve(load_evidence(evidence_path)), role)
    out_dir.mkdir(parents=True, exist_ok=True)
    output.write_csv(candidates, out_dir / "leads.csv")
    output.write_xlsx(candidates, out_dir / "leads.xlsx")
    write_signal_matrix(candidates, role, out_dir / "signal_matrix.csv")
    return candidates


def write_signal_matrix(candidates: list, role: dict, path: Path) -> None:
    ids = [s["id"] for s in role.get("interview_signals", [])]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Tier", *ids])
        for c in candidates:
            status = {s.id: s.status for s in c.signals}
            w.writerow([c.name, c.tier, *[status.get(i, "") for i in ids]])
