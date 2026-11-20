"""Close the loop: learn signal weights from post-interview outcomes.

data/outcomes.csv columns:
  name            candidate name (matched to the latest scored results)
  stage           e.g. Recruiter screen, Hiring manager, System design, AI fluency
  result          advanced | not advanced
  passed_signals  semicolon list of signal ids the interviewer credited
  failed_signals  semicolon list of signal ids that decided a rejection

Two things move a weight:
  1. Decisiveness: how often interviewers named the signal as the reason for
     a pass or a rejection.
  2. Predictive lift: whether public evidence for the signal (found before
     outreach) went with candidates who advanced.
Nothing changes until there are at least MIN_OUTCOMES outcomes.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path

from .evaluate import _read_rows, is_example
from .models import normalize_name

MIN_OUTCOMES = 5
FLOOR, CEILING = 0.2, 3.0


def _split(v: str | None) -> set[str]:
    return {x.strip() for x in (v or "").replace(",", ";").split(";") if x.strip()}


def recalibrate(role: dict, outcomes_path: Path, matrix_path: Path) -> dict:
    rows = _read_rows(outcomes_path, sheet="Outcomes")
    outcomes = [
        {k: ("" if v is None else str(v)) for k, v in r.items() if k}
        for r in rows
        if str(r.get("name") or "").strip() and not is_example(r.get("name"))
    ]
    matrix: dict[str, dict] = {}
    if matrix_path.exists():
        with matrix_path.open(newline="", encoding="utf-8") as f:
            matrix = {normalize_name(r["Name"]): r for r in csv.DictReader(f)}

    signals = role.get("interview_signals", [])
    report: dict = {"date": date.today().isoformat(), "outcomes": len(outcomes), "weights": {}, "signals": {}}
    if len(outcomes) < MIN_OUTCOMES:
        report["note"] = f"Only {len(outcomes)} outcome(s); need {MIN_OUTCOMES} before weights change."
        report["weights"] = {s["id"]: float(s.get("weight", 1.0)) for s in signals}
        return report

    for s in signals:
        sid, base = s["id"], float(s.get("weight", 1.0))
        failed = sum(sid in _split(o.get("failed_signals")) for o in outcomes)
        passed = sum(sid in _split(o.get("passed_signals")) for o in outcomes)
        decisive = (failed + passed) / len(outcomes)

        with_ev, without_ev = [], []
        for o in outcomes:
            row = matrix.get(normalize_name(o["name"]))
            if not row:
                continue
            adv = (o.get("result") or "").strip().lower() == "advanced"
            (with_ev if row.get(sid) == "met" else without_ev).append(adv)
        lift = None
        if with_ev and without_ev:
            lift = sum(with_ev) / len(with_ev) - sum(without_ev) / len(without_ev)

        new = base * (1 + 0.5 * decisive) * (1 + (lift or 0.0))
        new = round(min(max(new, FLOOR), CEILING), 3)
        report["weights"][sid] = new
        report["signals"][sid] = {
            "label": s["label"], "old_weight": base, "new_weight": new,
            "named_in_rejections": failed, "named_in_passes": passed,
            "evidence_lift": None if lift is None else round(lift, 3),
            "sample_with_evidence": len(with_ev), "sample_without_evidence": len(without_ev),
        }
    return report


def save(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
