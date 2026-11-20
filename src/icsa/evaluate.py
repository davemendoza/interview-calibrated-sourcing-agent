"""Score the agent against people you have already tiered.

The test set lives only on your machine (data/test_set.xlsx or .csv). It needs
the columns: Name, Your tier (Tier 1, Tier 2, Tier 3 or Trap), and optionally
Test challenge. The agent never sees your tiers before it runs.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from .models import normalize_name

TIERS = {"Tier 1", "Tier 2", "Tier 3"}

GATES = {
    "tier1_found": 0.70,
    "tier_agreement": 0.60,
    "sourced": 0.80,
    "over_ranked_max": 0,
    "wrong_person_max": 0.0,
}


def _read_rows(path: Path, sheet: str = "Test Set") -> list[dict]:
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        from openpyxl import load_workbook

        wb = load_workbook(path, read_only=True, data_only=True)
        ws = wb[sheet] if sheet in wb.sheetnames else wb.worksheets[0]
        rows = list(ws.iter_rows(values_only=True))
        header = [str(h).strip() if h is not None else "" for h in rows[0]]
        return [dict(zip(header, r)) for r in rows[1:]]
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_test_set(path: Path) -> list[dict]:
    out = []
    for r in _read_rows(path):
        name = str(r.get("Name") or "").strip()
        tier = str(r.get("Your tier") or "").strip()
        if name and tier and tier != "None":
            out.append({"name": name, "tier": tier, "challenge": str(r.get("Test challenge") or "").strip()})
    return out


def load_results(path: Path) -> dict[str, dict]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out: dict[str, dict] = {}
    for r in rows:
        key = normalize_name(r["Name"])
        # Keep the best-ranked record when a name appears more than once.
        if key not in out or _rank(r["Tier"]) < _rank(out[key]["Tier"]):
            out[key] = r
    return out


def _rank(tier: str) -> int:
    return {"Tier 1": 0, "Tier 2": 1, "Tier 3": 2}.get(tier, 3)


@dataclass
class Report:
    metrics: dict = field(default_factory=dict)
    rows: list[dict] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.failures


def evaluate(test_path: Path, results_path: Path, review_path: Path | None = None, gates: dict | None = None) -> Report:
    gates = {**GATES, **(gates or {})}
    test = load_test_set(test_path)
    results = load_results(results_path)
    rep = Report()

    judged = {}
    if review_path and review_path.exists():
        with review_path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r.get("Right person") or "").strip():
                    judged[normalize_name(r["Name"])] = r["Right person"].strip().lower()

    for t in test:
        hit = results.get(normalize_name(t["name"]))
        agent_tier = hit["Tier"] if hit else "Not ranked"
        rep.rows.append({
            "Name": t["name"], "Your tier": t["tier"], "Test challenge": t["challenge"],
            "Surfaced": "Yes" if hit else "No", "Agent tier": agent_tier,
            "Sources": hit["Sources"] if hit else "", "Identity": hit["Identity"] if hit else "",
            "Right person": judged.get(normalize_name(t["name"]), ""),
        })

    tier1 = [r for r in rep.rows if r["Your tier"] == "Tier 1"]
    tiered = [r for r in rep.rows if r["Your tier"] in TIERS]
    traps = [r for r in rep.rows if r["Your tier"] == "Trap"]
    surfaced = [r for r in rep.rows if r["Surfaced"] == "Yes"]
    scored = [r for r in results.values() if r["Tier"] in TIERS]
    checked = [r for r in surfaced if r["Right person"] in ("yes", "no")]

    m = rep.metrics
    m["test_set_size"] = len(rep.rows)
    m["tier1_found"] = _rate(sum(r["Surfaced"] == "Yes" for r in tier1), len(tier1))
    m["tier_agreement"] = _rate(sum(r["Agent tier"] == r["Your tier"] for r in tiered), len(tiered))
    m["over_ranked"] = sum(r["Agent tier"] == "Tier 1" and r["Your tier"] != "Tier 1" for r in rep.rows)
    m["traps_handled"] = _rate(sum(r["Agent tier"] != "Tier 1" for r in traps), len(traps))
    m["sourced"] = _rate(sum(bool(r["Sources"].strip()) for r in scored), len(scored))
    m["wrong_person_rate"] = _rate(sum(r["Right person"] == "no" for r in checked), len(checked))
    m["identity_checked"] = f"{len(checked)} of {len(surfaced)}"
    m["new_tier1_or_2_finds"] = sum(
        1 for k, r in results.items()
        if r["Tier"] in ("Tier 1", "Tier 2") and k not in {normalize_name(t["name"]) for t in test}
    )

    if m["tier1_found"] is not None and m["tier1_found"] < gates["tier1_found"]:
        rep.failures.append(f"Tier 1 found {m['tier1_found']:.0%} is below {gates['tier1_found']:.0%}")
    if m["tier_agreement"] is not None and m["tier_agreement"] < gates["tier_agreement"]:
        rep.failures.append(f"Tier agreement {m['tier_agreement']:.0%} is below {gates['tier_agreement']:.0%}")
    if m["over_ranked"] > gates["over_ranked_max"]:
        rep.failures.append(f"{m['over_ranked']} lead(s) called Tier 1 that you did not rate Tier 1")
    if m["sourced"] is not None and m["sourced"] < gates["sourced"]:
        rep.failures.append(f"Sourced claims {m['sourced']:.0%} is below {gates['sourced']:.0%}")
    if m["wrong_person_rate"] is not None and m["wrong_person_rate"] > gates["wrong_person_max"]:
        rep.failures.append(f"Wrong-person rate {m['wrong_person_rate']:.0%}; must be 0%")
    if len(checked) < len(surfaced):
        rep.failures.append(f"Identity not yet checked for {len(surfaced) - len(checked)} surfaced test-set lead(s); fill 'Right person' in the review file")
    return rep


def _rate(n: int, d: int) -> float | None:
    return round(n / d, 3) if d else None


def write_review(rep: Report, path: Path) -> None:
    """Review file: you fill 'Right person' (yes/no) once; it is reused on later runs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = ["Name", "Your tier", "Agent tier", "Surfaced", "Identity", "Right person", "Test challenge", "Sources"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rep.rows)
