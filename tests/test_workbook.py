"""The calibration workbook template is read directly by eval and recalibrate."""

import shutil

from openpyxl import load_workbook

from icsa import evaluate, recalibrate
from conftest import ROOT

TEMPLATE = ROOT / "templates/Calibration_Workbook_TEMPLATE.xlsx"


def filled_copy(tmp_path):
    path = tmp_path / "calibration_workbook.xlsx"
    shutil.copy(TEMPLATE, path)
    wb = load_workbook(path)
    ts, oc = wb["Test Set"], wb["Outcomes"]
    for i, row in enumerate([("Riya Patel", "Tier 1", "", "yes"), ("Sam Lee", "Trap", "namesake", "")], start=3):
        for j, v in enumerate(row, start=1):
            ts.cell(i, j, v)
    for i in range(6):
        adv = i < 3
        row = (f"Person {chr(65 + i)}x", "System design", "advanced" if adv else "not advanced",
               "money_state" if adv else "", "" if adv else "money_state", "")
        for j, v in enumerate(row, start=1):
            oc.cell(3 + i, j, v)
    wb.save(path)
    return path


def test_example_rows_are_ignored(tmp_path):
    rows = evaluate.load_test_set(filled_copy(tmp_path))
    assert [r["name"] for r in rows] == ["Riya Patel", "Sam Lee"]


def test_recalibrate_reads_the_outcomes_tab(tmp_path, role):
    rep = recalibrate.recalibrate(role, filled_copy(tmp_path), tmp_path / "no_matrix.csv")
    assert rep["outcomes"] == 6
    sig = rep["signals"]["money_state"]
    assert sig["named_in_rejections"] == 3 and sig["named_in_passes"] == 3
    assert sig["new_weight"] > sig["old_weight"]
