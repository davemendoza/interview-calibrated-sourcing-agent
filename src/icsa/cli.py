"""Command line: icsa harvest | score | run | eval | recalibrate"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from pathlib import Path

from . import evaluate as ev
from . import judge as judge_mod
from . import ecosystem as eco
from . import pipeline, recalibrate, taxonomy
from .config import load_role

WORKBOOK = Path("data/calibration_workbook.xlsx")


def _default(path: str | None, fallback: str) -> str:
    """Use the calibration workbook when present, else the older separate file."""
    if path:
        return path
    return str(WORKBOOK) if WORKBOOK.exists() else fallback


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
        sp.add_argument("--role", default="config/roles/example_fintech_staff_payments_engineer.toml")

    h = sub.add_parser("harvest", help="collect public evidence")
    role_arg(h)
    h.add_argument("--evidence", default="data/evidence.jsonl")
    h.add_argument("--only", nargs="*", choices=list(pipeline.HARVESTERS))

    s = sub.add_parser("score", help="resolve identity and score evidence")
    role_arg(s)
    s.add_argument("--evidence", default="data/evidence.jsonl")
    s.add_argument("--out", default="out")
    s.add_argument("--judge", action="store_true", help="AI-confirm signals for Tier 1 and 2 leads (needs ANTHROPIC_API_KEY)")

    r = sub.add_parser("run", help="harvest, score, then evaluate if a test set exists")
    role_arg(r)
    r.add_argument("--evidence", default="data/evidence.jsonl")
    r.add_argument("--out", default="out")
    r.add_argument("--test-set", default=None, help="default: data/calibration_workbook.xlsx, else data/test_set.xlsx")
    r.add_argument("--only", nargs="*", choices=list(pipeline.HARVESTERS))
    r.add_argument("--judge", action="store_true", help="AI-confirm signals for Tier 1 and 2 leads (needs ANTHROPIC_API_KEY)")

    e = sub.add_parser("eval", help="score the agent against your tiered test set")
    e.add_argument("--test-set", default=None, help="default: data/calibration_workbook.xlsx, else data/test_set.xlsx")
    e.add_argument("--results", default="out/leads.csv")
    e.add_argument("--review", default="data/identity_review.csv")

    c = sub.add_parser("recalibrate", help="learn signal weights from interview outcomes")
    role_arg(c)
    c.add_argument("--outcomes", default=None, help="default: data/calibration_workbook.xlsx (Outcomes tab), else data/outcomes.csv")
    c.add_argument("--matrix", default="out/signal_matrix.csv")
    c.add_argument("--save", default="data/calibration.json")

    m = sub.add_parser("ecosystem", help="show ecosystem coverage by category and what is missing")
    role_arg(m)

    t = sub.add_parser("taxonomy", help="read taxonomy pages and suggest domain terms you are missing")
    role_arg(t)
    t.add_argument("--top", type=int, default=40)

    g = sub.add_parser("guard", help="scan resumes, PDFs, Word and HTML files for hidden or instructing text")
    g.add_argument("paths", nargs="+", help="files or folders (.pdf .docx .html .txt)")
    g.add_argument("--strict", action="store_true", help="also fail on medium findings")

    a = p.parse_args(argv)

    if a.cmd == "guard":
        from . import guard
        files = []
        for raw in a.paths:
            path = Path(raw)
            files += sorted(f for f in path.rglob("*") if f.suffix.lower() in (".pdf", ".docx", ".html", ".htm", ".txt")) if path.is_dir() else [path]
        worst = 0
        for f in files:
            rep = guard.scan_file(f)
            status = "HOLD" if rep.blocked else ("REVIEW" if rep.findings else "clean")
            print(f"{status:<7}{f}")
            for finding in rep.findings:
                print(f"        {finding.line()}")
            if rep.blocked or (a.strict and rep.worst == guard.MEDIUM):
                worst = 1
        print(f"\nScanned {len(files)} file(s). HOLD means do not feed it to any scorer or AI until a person has looked.")
        return worst

    if a.cmd == "ecosystem":
        role = load_role(a.role, calibration=None)
        rows = eco.coverage(role)
        print(f"Ecosystem coverage for: {role['role'].get('title') or a.role}\n")
        print(f"{'Category':<13}{'Entries':<9}{'Uses':<28}What it can support")
        for cat, n, uses, guide in rows:
            print(f"{cat:<13}{n:<9}{(uses or '-'):<28}{guide}")
        missing = [cat for cat, n, _, _ in rows if n == 0 and cat != "other"]
        if missing:
            print("\nNo entries yet for: " + ", ".join(missing))
            print("See docs/BUILD_YOUR_ECOSYSTEM.md for a prompt that fills these in for your job family.")
        return 0

    if a.cmd == "taxonomy":
        from bs4 import BeautifulSoup
        from .http import Http
        role = load_role(a.role, calibration=None)
        pages = role.get("taxonomy_pages", [])
        if not pages:
            print("No taxonomy pages yet. Add [[ecosystem]] entries with use = \"taxonomy\" to your role file.")
            return 1
        http, texts = Http(), {}
        for url in pages:
            try:
                texts[url] = BeautifulSoup(http.get_text(url), "html.parser").get_text(" ")
            except Exception as exc:
                print(f"[taxonomy] skipped {url}: {exc}", file=sys.stderr)
        suggestions = taxonomy.suggest_terms(texts, taxonomy.role_terms(role), a.top)
        print(f"Read {len(texts)} of {len(pages)} pages. Phrases your role file does not cover yet:\n")
        for phrase, count, urls in suggestions:
            print(f"  {phrase:<40} seen {count}x on {len(urls)} page(s)")
        print("\nReview these, then copy the ones that mark real work in your field into the domain requirement's terms.")
        return 0

    if a.cmd == "harvest":
        n = pipeline.harvest(load_role(a.role), Path(a.evidence), a.only)
        print(f"Saved {n} evidence items to {a.evidence}")
        return 0

    if a.cmd in ("score", "run"):
        role = load_role(a.role)
        if a.cmd == "run":
            pipeline.harvest(role, Path(a.evidence), a.only)
        cands = pipeline.score(role, Path(a.evidence), Path(a.out), judge_mod.from_role(role, force=a.judge))
        counts = Counter(c.tier for c in cands)
        print("Results: " + ", ".join(f"{t}: {n}" for t, n in sorted(counts.items())))
        print(f"Wrote {a.out}/leads.xlsx, leads.csv and signal_matrix.csv")
        test_set = Path(_default(a.test_set, "data/test_set.xlsx"))
        if a.cmd == "run" and test_set.exists():
            return _eval(test_set, Path(a.out) / "leads.csv", Path("data/identity_review.csv"))
        return 0

    if a.cmd == "eval":
        return _eval(Path(_default(a.test_set, "data/test_set.xlsx")), Path(a.results), Path(a.review))

    if a.cmd == "recalibrate":
        role = load_role(a.role, calibration=None)  # always learn from the role file's base weights
        rep = recalibrate.recalibrate(role, Path(_default(a.outcomes, "data/outcomes.csv")), Path(a.matrix))
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
    print("\nShareable summary (no names):\n  " + ev.pilot_summary(rep))
    if rep.passed:
        print("GATE PASSED: the agent may source this role.")
        return 0
    print("GATE FAILED: fix these before sourcing live:")
    for f in rep.failures:
        print(f"  - {f}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
