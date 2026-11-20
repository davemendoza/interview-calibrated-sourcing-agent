"""Load a role file and apply learned calibration weights if present."""

from __future__ import annotations

import json
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


def load_role(path: str | Path, calibration: str | Path | None = DEFAULT_CALIBRATION) -> dict:
    with open(path, "rb") as f:
        role = tomllib.load(f)
    role.setdefault("role", {})
    role.setdefault("requirements", [])
    role.setdefault("interview_signals", [])
    role.setdefault("sources", {})
    if calibration and Path(calibration).exists():
        weights = json.loads(Path(calibration).read_text()).get("weights", {})
        for sig in role["interview_signals"]:
            if sig["id"] in weights:
                sig["weight"] = float(weights[sig["id"]])
                sig["calibrated"] = True
    return role


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
