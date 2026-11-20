"""Load a role file and apply learned calibration weights if present."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

DEFAULT_CALIBRATION = Path("data/calibration.json")

METROS = {
    "sf_bay": ["san francisco", "sf bay", "bay area", "oakland", "berkeley", "palo alto", "mountain view",
               "san jose", "sunnyvale", "menlo park", "redwood city", "south san francisco", "san mateo",
               "cupertino", "santa clara", "fremont", "burlingame", "emeryville", "alameda", "los altos"],
    "nyc": ["new york", "nyc", "brooklyn", "manhattan", "queens", "jersey city", "hoboken", "bronx",
            "long island city", "staten island"],
}


# Wording shown in results. Every key can be overridden in a role file's
# [labels] table, so nothing domain-specific is fixed in code.
DEFAULT_LABELS = {
    "domain_name": "domain",                # e.g. "payments", "healthcare data", "robotics"
    "tier1": "Strong Recommend",
    "tier2": "Recommend",
    "tier3": "Pipeline depth",
    "pending": "Pending research",          # no domain evidence yet; never a guessed tier
    "identity_review": "Identity review",   # same-name records not yet confirmed as one person
}


def load_role(path: str | Path, calibration: str | Path | None = DEFAULT_CALIBRATION) -> dict:
    with open(path, "rb") as f:
        role = tomllib.load(f)
    role["labels"] = {**DEFAULT_LABELS, **role.get("labels", {})}
    role.setdefault("role", {})
    role.setdefault("requirements", [])
    role.setdefault("interview_signals", [])
    role.setdefault("sources", {})
    for problem in check_role(role):
        print(f"[role file] {problem}", file=sys.stderr)
    if calibration and Path(calibration).exists():
        weights = json.loads(Path(calibration).read_text()).get("weights", {})
        for sig in role["interview_signals"]:
            if sig["id"] in weights:
                sig["weight"] = float(weights[sig["id"]])
                sig["calibrated"] = True
    return role


def check_role(role: dict) -> list[str]:
    """Plain-language warnings for template fields that were not filled in."""
    problems = []
    if not role["labels"].get("domain_name"):
        problems.append("labels.domain_name is empty; results will say 'domain' (see >>> CUSTOMIZE lines)")
    if not role["role"].get("title"):
        problems.append("role.title is empty")
    domain = [r for r in role["requirements"] if r.get("kind") == "domain"]
    if not domain or not any(r.get("terms") for r in domain):
        problems.append("no domain requirement terms; every lead will stay unscored until you add them")
    for r in role["requirements"] + role["interview_signals"]:
        if not r.get("label"):
            problems.append(f"'{r.get('id')}' has no label")
    return problems


def metro_of(location: str | None) -> str | None:
    if not location:
        return None
    loc = location.lower()
    for metro, places in METROS.items():
        if any(p in loc for p in places):
            return metro
    # Bare state codes used on patents.
    if loc.endswith(", ca") or loc == "ca":
        return "ca_other"
    if loc.endswith(", ny") or loc == "ny":
        return "ny_other"
    return "other"
