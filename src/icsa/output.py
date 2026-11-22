"""Write results as CSV and a formatted workbook (Leads, Evidence, Screen Questions)."""

from __future__ import annotations

import csv
from pathlib import Path

from .config import metro_of
from .models import Candidate

LEAD_COLUMNS = [
    "Tier", "Recommendation", "Name", "Company", "Location", "Identity", "Interview signal score",
    "Matched requirements", "Signals with evidence", "AI judge notes", "Key evidence", "Latest evidence", "GitHub",
    "Self-published links", "Self-published email", "Sources", "Tier reasons", "Integrity",
]


def _row(c: Candidate) -> dict:
    met_req = [r.label for r in c.requirements if r.status == "met"]
    met_sig = [s.label.split(":")[0] for s in c.signals if s.status == "met"]
    key = sorted(c.evidence, key=lambda e: (e.channel != "commit", -(e.count or 0), e.date or ""))
    handle = c.best("handle")
    links = sorted({u for e in c.evidence for u in e.links if "github.com" not in u})
    location = c.best("location")
    return {
        "Tier": c.tier,
        "Recommendation": c.recommendation,
        "Name": c.name,
        "Company": c.best("org") or "Not found",
        "Location": location or "Not found",
        "Identity": c.identity_status,
        "Interview signal score": c.signal_score,
        "Matched requirements": "; ".join(met_req),
        "Signals with evidence": "; ".join(met_sig),
        "AI judge notes": " | ".join(f"{s.id}: {s.note}" for s in c.signals if s.note),
        "Key evidence": " | ".join(e.title for e in key[:3]),
        "Latest evidence": c.latest_date or "Not found",
        "GitHub": f"https://github.com/{handle}" if handle else "",
        "Self-published links": " ".join(links),
        "Self-published email": c.best("email") or "",
        "Sources": " ".join(c.sources),
        "Tier reasons": "; ".join(c.tier_reasons),
        "Integrity": " | ".join(c.integrity_flags) or "No hidden or instructing text found",
    }


def write_csv(candidates: list[Candidate], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEAD_COLUMNS)
        w.writeheader()
        for c in candidates:
            w.writerow(_row(c))


def write_xlsx(candidates: list[Candidate], path: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Leads"
    ws.append(LEAD_COLUMNS)
    tier_fill = {"Tier 1": "DDEBF7", "Tier 2": "E2EFDA"}
    review_fill = "FCE4D6"
    for c in candidates:
        row = _row(c)
        ws.append([row[k] for k in LEAD_COLUMNS])
        fill = tier_fill.get(c.tier) or (review_fill if c.identity_status.startswith("review") else None)
        if fill:
            for cell in ws[ws.max_row]:
                cell.fill = PatternFill("solid", fgColor=fill)
        for col in ("GitHub",):
            cell = ws.cell(ws.max_row, LEAD_COLUMNS.index(col) + 1)
            if cell.value:
                cell.hyperlink = cell.value
                cell.font = Font(color="0563C1", underline="single")

    ev = wb.create_sheet("Evidence")
    ev.append(["Name", "Channel", "Evidence", "Date", "Organization", "Location", "Metro", "Source"])
    for c in candidates:
        for e in c.evidence:
            ev.append([c.name, e.channel, e.title, e.date or "", e.org or "", e.location or "", metro_of(e.location) or "", e.url])
            cell = ev.cell(ev.max_row, 8)
            cell.hyperlink = e.url
            cell.font = Font(color="0563C1", underline="single")

    sq = wb.create_sheet("Screen Questions")
    sq.append(["Name", "Tier", "Question (signal with no public evidence)"])
    for c in candidates:
        if c.tier in ("Tier 1", "Tier 2"):
            for q in c.screen_questions:
                sq.append([c.name, c.tier, q])

    for sheet in wb.worksheets:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F3864")
        sheet.freeze_panes = "A2"
        for column in sheet.columns:
            width = min(max(len(str(c.value or "")) for c in column) + 2, 60)
            sheet.column_dimensions[column[0].column_letter].width = width
            for c in column[1:]:
                c.alignment = Alignment(vertical="top", wrap_text=width >= 60)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def write_integrity(held: list, path: Path) -> None:
    """One row per evidence item the guard held back, with the exact reason."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Name", "Channel", "Evidence", "Source", "Why it was held back"])
        for h in held:
            w.writerow([h.evidence.person_name, h.evidence.channel, h.evidence.title, h.evidence.url, " | ".join(h.reasons)])
