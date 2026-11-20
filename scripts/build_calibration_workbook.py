"""Build the calibration workbook template from a role file.

    python scripts/build_calibration_workbook.py [role.toml] [out.xlsx]

The workbook is where a talent team records what the agent learns from:
people already rated (Test Set) and post-interview results (Outcomes).
The Signal Summary tab shows, for every interview signal, how often it was
credited in candidates who advanced versus named in rejections.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROLE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("config/roles/example_fintech_staff_payments_engineer.toml")
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("templates/Calibration_Workbook_TEMPLATE.xlsx")
LAST = 500  # rows available for entries

F = "Arial"
NAVY, BLUE, GREY = "1F3864", "2F5FD0", "7A849A"
INPUT = PatternFill("solid", fgColor="FFF7CC")      # you fill these in
EXAMPLE = PatternFill("solid", fgColor="F2F2F2")    # example row, ignored by the agent
HEAD = PatternFill("solid", fgColor=NAVY)
thin = Side(style="thin", color="D9DEE8")
BOX = Border(left=thin, right=thin, top=thin, bottom=thin)


def header(ws, row, cols, widths):
    for i, (c, w) in enumerate(zip(cols, widths), start=1):
        cell = ws.cell(row, i, c)
        cell.font = Font(name=F, bold=True, color="FFFFFF", size=10)
        cell.fill = HEAD
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = BOX
        ws.column_dimensions[cell.column_letter].width = w
    ws.row_dimensions[row].height = 30
    ws.freeze_panes = ws.cell(row + 1, 1)


def example_row(ws, row, values):
    for i, v in enumerate(values, start=1):
        cell = ws.cell(row, i, v)
        cell.font = Font(name=F, italic=True, color=GREY, size=10)
        cell.fill = EXAMPLE
        cell.border = BOX


def input_area(ws, first_row, ncols):
    for r in range(first_row, first_row + 40):
        for c in range(1, ncols + 1):
            cell = ws.cell(r, c)
            cell.fill = INPUT
            cell.border = BOX
            cell.font = Font(name=F, size=10)


def main() -> None:
    role = tomllib.loads(ROLE.read_text())
    signals = role.get("interview_signals", [])
    ids = [s["id"] for s in signals]

    wb = Workbook()

    # ---------------------------------------------------------------- How to Use
    ws = wb.active
    ws.title = "How to Use"
    ws.column_dimensions["A"].width = 4
    ws.column_dimensions["B"].width = 110
    lines = [
        ("Calibration Workbook", "title"),
        ("Interview-Calibrated Sourcing Agent", "sub"),
        ("", None),
        ("What this workbook is for", "h"),
        ("The agent learns from two things you record here: people you have already rated, and what happened in your interviews.", None),
        ("It uses them to answer one question: which interview signals separate candidates who advance from candidates who do not?", None),
        ("", None),
        ("Legend", "h"),
        ("Yellow cells: you fill these in.", "input"),
        ("Grey italic row: an example showing the format. The agent ignores any row whose name starts with \"Example\".", "example"),
        ("White cells with numbers: formulas. Do not type over them.", None),
        ("", None),
        ("Step 1. Signals tab", "h"),
        ("List the follow-ups that decided your past interviews. The ids must match the interview_signals ids in your role file.", None),
        ("", None),
        ("Step 2. Test Set tab (before the agent runs)", "h"),
        ("Add 10 to 50 people you have already rated: Tier 1, Tier 2, Tier 3, or Trap (a case a tool could easily get wrong, such as a namesake).", None),
        ("Rate everyone before running the agent so it cannot sway your judgment. After the first run, mark Right person yes or no for anyone it surfaced.", None),
        ("", None),
        ("Step 3. Outcomes tab (after every interview round)", "h"),
        ("One row per candidate per stage. Result is advanced or not advanced.", None),
        ("Passed signals: signal ids the interviewer credited. Failed signals: signal ids that cost the candidate the round. Separate several ids with a semicolon.", None),
        ("", None),
        ("Step 4. Signal Summary tab", "h"),
        ("Shows, for each signal, how often it was credited in candidates who advanced and how often it was named in rejections.", None),
        ("A signal that keeps deciding outcomes is one the agent should look for before outreach. A signal that never decides anything may be noise.", None),
        ("", None),
        ("Step 5. Run the agent", "h"),
        ("Save this file as data/calibration_workbook.xlsx (that folder is never uploaded), then run:", None),
        ("icsa eval          checks the agent against your Test Set", "code"),
        ("icsa recalibrate   learns signal weights from your Outcomes (needs at least 5 rows)", "code"),
        ("", None),
        ("Privacy", "h"),
        ("Real names belong only in your local copy. Never commit a filled-in workbook to a public repository.", None),
    ]
    for r, (text, kind) in enumerate(lines, start=1):
        c = ws.cell(r, 2, text)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        c.font = {
            "title": Font(name=F, size=18, bold=True, color=NAVY),
            "sub": Font(name=F, size=11, color=GREY),
            "h": Font(name=F, size=11, bold=True, color=BLUE),
            "code": Font(name="Courier New", size=10, color=NAVY),
            "example": Font(name=F, size=10, italic=True, color=GREY),
        }.get(kind, Font(name=F, size=10))
        if kind == "input":
            c.fill = INPUT
        if kind == "example":
            c.fill = EXAMPLE

    # ---------------------------------------------------------------- Signals
    sg = wb.create_sheet("Signals")
    header(sg, 1, ["Signal id", "What interviewers listened for", "Screen question when there is no public evidence", "Starting weight"], [26, 60, 80, 14])
    for r, s in enumerate(signals, start=2):
        vals = [s["id"], s["label"], s.get("screen_question", ""), float(s.get("weight", 1.0))]
        for c, v in enumerate(vals, start=1):
            cell = sg.cell(r, c, v)
            cell.font = Font(name=F, size=10)
            cell.fill = INPUT
            cell.border = BOX
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        sg.cell(r, 4).number_format = "0.0"
    note = sg.cell(len(signals) + 3, 1, f"Signals copied from {ROLE.name}. Edit to match your role file; ids must match exactly.")
    note.font = Font(name=F, size=9, italic=True, color=GREY)

    # ---------------------------------------------------------------- Test Set
    ts = wb.create_sheet("Test Set")
    header(ts, 1, ["Name", "Your tier", "Test challenge", "Right person"], [30, 14, 60, 14])
    example_row(ts, 2, ["Example: Riya Patel (fictional)", "Tier 1", "Payments evidence is in a former employer's repos", "yes"])
    input_area(ts, 3, 4)
    dv_tier = DataValidation(type="list", formula1='"Tier 1,Tier 2,Tier 3,Trap"', allow_blank=True)
    dv_yes = DataValidation(type="list", formula1='"yes,no"', allow_blank=True)
    ts.add_data_validation(dv_tier)
    ts.add_data_validation(dv_yes)
    dv_tier.add(f"B3:B{LAST}")
    dv_yes.add(f"D3:D{LAST}")
    ts["D1"].comment = Comment("After the agent's first run: yes if it matched the right person, no if it attached someone else's work.", "icsa")

    # ---------------------------------------------------------------- Outcomes
    oc = wb.create_sheet("Outcomes")
    header(oc, 1, ["name", "stage", "result", "passed_signals", "failed_signals", "notes"], [30, 24, 16, 40, 40, 40])
    example_row(oc, 2, ["Example: Tom Reyes (fictional)", "System design", "not advanced", "cross_team_influence", "money_state", "Could not say what the caller gets on a timeout"])
    input_area(oc, 3, 6)
    dv_res = DataValidation(type="list", formula1='"advanced,not advanced"', allow_blank=True)
    oc.add_data_validation(dv_res)
    dv_res.add(f"C3:C{LAST}")
    oc["D1"].comment = Comment("Signal ids from the Signals tab, separated by semicolons: " + "; ".join(ids), "icsa")
    oc["E1"].comment = Comment("Signal ids that cost the candidate this round, separated by semicolons.", "icsa")

    # ---------------------------------------------------------------- Signal Summary
    sm = wb.create_sheet("Signal Summary")
    sm["A1"] = "Which signals separate candidates who advance from those who do not"
    sm["A1"].font = Font(name=F, size=14, bold=True, color=NAVY)
    sm["A2"] = "All figures are formulas over the Outcomes tab (rows 3 onward; the example row is excluded)."
    sm["A2"].font = Font(name=F, size=9, italic=True, color=GREY)

    rng = lambda col: f"Outcomes!${col}$3:${col}${LAST}"
    stats = [
        ("Outcomes recorded", f'=COUNTA({rng("A")})', "0"),
        ("Advanced", f'=COUNTIF({rng("C")},"advanced")', "0"),
        ("Not advanced", f'=COUNTIF({rng("C")},"not advanced")', "0"),
        ("Advance rate", '=IF(B4=0,"",B5/B4)', "0%"),
        ("Ready to recalibrate (needs 5)", '=IF(B4>=5,"Yes","Need "&(5-B4)&" more")', "@"),
    ]
    for r, (label, formula, fmt) in enumerate(stats, start=4):
        a = sm.cell(r, 1, label)
        a.font = Font(name=F, size=10, bold=True)
        b = sm.cell(r, 2, formula)
        b.font = Font(name=F, size=10)
        b.number_format = fmt
        a.border = b.border = BOX

    top = 11
    cols = ["Signal id", "What interviewers listened for", "Credited in passes", "Named in rejections",
            "Times it decided a round", "Share of rounds decided", "Read"]
    header(sm, top, cols, [26, 52, 16, 16, 16, 16, 44])
    sm.freeze_panes = None
    for i in range(len(signals)):
        r = top + 1 + i
        sm.cell(r, 1, f"=Signals!A{i + 2}")
        sm.cell(r, 2, f"=Signals!B{i + 2}")
        sm.cell(r, 3, f'=IF(A{r}="","",COUNTIF({rng("D")},"*"&A{r}&"*"))')
        sm.cell(r, 4, f'=IF(A{r}="","",COUNTIF({rng("E")},"*"&A{r}&"*"))')
        sm.cell(r, 5, f'=IF(A{r}="","",C{r}+D{r})')
        sm.cell(r, 6, f'=IF(OR(A{r}="",$B$4=0),"",E{r}/$B$4)')
        sm.cell(r, 7, f'=IF(OR(A{r}="",$B$4=0),"",IF(D{r}>=2,"Often decides rejections: source for it",IF(E{r}=0,"Has not decided any round yet","Credited when present")))')
        for c in range(1, 8):
            cell = sm.cell(r, c)
            cell.font = Font(name=F, size=10)
            cell.border = BOX
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        sm.cell(r, 6).number_format = "0%"
    end = top + len(signals)
    sm.conditional_formatting.add(
        f"A{top + 1}:G{end}",
        FormulaRule(formula=[f'AND(ISNUMBER($D{top + 1}),$D{top + 1}>=2)'], fill=PatternFill("solid", fgColor="FDEEDD")),
    )
    foot = sm.cell(end + 2, 1, "The agent's recalibrate command goes one step further: it also checks whether public evidence for each signal, found before outreach, went with candidates who advanced.")
    foot.font = Font(name=F, size=9, italic=True, color=GREY)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT)
    print(f"Saved {OUT}")


if __name__ == "__main__":
    main()
