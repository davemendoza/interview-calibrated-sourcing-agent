"""Command line: icsa harvest | score | run | eval | recalibrate"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

from . import evaluate as ev
from . import pipeline, recalibrate
from .config import load_role


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            if v.strip():
                os.environ.setdefault(k.strip(), v.strip())


def main(argv: list[str] | None = None) -> int:
    _load_dotenv()
    p = argparse.ArgumentParser(prog="icsa", description="Interview-Calibrated Sourcing Agent")
    sub = p.add_subparsers(dest="cmd", required=True)

    def role_arg(sp):
        sp.add_argument("--role", default="config/roles/staff_payments_engineer.toml")

    h = sub.add_parser("harvest", help="collect public evidence")
    role_arg(h)
    h.add_argument("--evidence", default="data/evidence.jsonl")
    h.add_argument("--only", nargs="*", choices=list(pipeline.HARVESTERS))

    s = sub.add_parser("score", help="resolve identity and score evidence")
    role_arg(s)
    s.add_argument("--evidence", default="data/evidence.jsonl")
    s.add_argument("--out", default="out")

    r = sub.add_parser("run", help="harvest, score, then evaluate if a test set exists")
    role_arg(r)
    r.add_argument("--evidence", default="data/evidence.jsonl")
    r.add_argument("--out", default="out")
    r.add_argument("--test-set", default="data/test_set.xlsx")
    r.add_argument("--only", nargs="*", choices=list(pipeline.HARVESTERS))

    e = sub.add_parser("eval", help="score the agent against your tiered test set")
    e.add_argument("--test-set", default="data/test_set.xlsx")
    e.add_argument("--results", default="out/leads.csv")
    e.add_argument("--review", default="data/identity_review.csv")

    c = sub.add_parser("recalibrate", help="learn signal weights from interview outcomes")
    role_arg(c)
    c.add_argument("--outcomes", default="data/outcomes.csv")
    c.add_argument("--matrix", default="out/signal_matrix.csv")
    c.add_argument("--save", default="data/calibration.json")

    a = p.parse_args(argv)

    if a.cmd == "harvest":
        n = pipeline.harvest(load_role(a.role), Path(a.evidence), a.only)
        print(f"Saved {n} evidence items to {a.evidence}")
        return 0

    if a.cmd in ("score", "run"):
        role = load_role(a.role)
        if a.cmd == "run":
            pipeline.harvest(role, Path(a.evidence), a.only)
        cands = pipeline.score(role, Path(a.evidence), Path(a.out))
        counts = Counter(c.tier for c in cands)
        print("Results: " + ", ".join(f"{t}: {n}" for t, n in sorted(counts.items())))
        print(f"Wrote {a.out}/leads.xlsx, leads.csv and signal_matrix.csv")
        if a.cmd == "run" and Path(a.test_set).exists():
            return _eval(Path(a.test_set), Path(a.out) / "leads.csv", Path("data/identity_review.csv"))
        return 0

    if a.cmd == "eval":
        return _eval(Path(a.test_set), Path(a.results), Path(a.review))

    if a.cmd == "recalibrate":
        role = load_role(a.role, calibration=None)  # always learn from the role file's base weights
        rep = recalibrate.recalibrate(role, Path(a.outcomes), Path(a.matrix))
        if "note" in rep:
            print(rep["note"])
            return 0
        recalibrate.save(rep, Path(a.save))
        for sid, info in rep["signals"].items():
            print(f"{sid}: {info['old_weight']} -> {info['new_weight']} "
                  f"(rejections {info['named_in_rejections']}, passes {info['named_in_passes']}, lift {info['evidence_lift']})")
        print(f"Saved {a.save}; the next score run uses these weights")
        return 0
    return 1


def _eval(test: Path, results: Path, review: Path) -> int:
    rep = ev.evaluate(test, results, review)
    ev.write_review(rep, review if not review.exists() else review.with_name("identity_review_latest.csv"))
    for k, v in rep.metrics.items():
        print(f"  {k}: {v:.0%}" if isinstance(v, float) else f"  {k}: {v}")
    if rep.passed:
        print("GATE PASSED: the agent may source this role.")
        return 0
    print("GATE FAILED: fix these before sourcing live:")
    for f in rep.failures:
        print(f"  - {f}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
