import csv

from icsa import evaluate, recalibrate


def write_csv(path, cols, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def test_gate_reports_recall_overranking_and_traps(tmp_path):
    test = tmp_path / "test_set.csv"
    write_csv(test, ["Name", "Your tier", "Test challenge"], [
        {"Name": "Riya Patel", "Your tier": "Tier 1", "Test challenge": ""},
        {"Name": "Tom Reyes", "Your tier": "Tier 1", "Test challenge": "patent only"},
        {"Name": "Sam Lee", "Your tier": "Trap", "Test challenge": "namesake"},
        {"Name": "Lee Chen", "Your tier": "Tier 3", "Test challenge": ""},
    ])
    results = tmp_path / "leads.csv"
    write_csv(results, ["Name", "Tier", "Sources", "Identity"], [
        {"Name": "Riya Patel", "Tier": "Tier 1", "Sources": "https://x", "Identity": "verified"},
        {"Name": "Sam Lee", "Tier": "Tier 1", "Sources": "https://y", "Identity": "single source"},
        {"Name": "Lee Chen", "Tier": "Tier 3", "Sources": "https://z", "Identity": "single source"},
        {"Name": "New Person", "Tier": "Tier 2", "Sources": "https://n", "Identity": "single source"},
    ])
    rep = evaluate.evaluate(test, results)
    assert rep.metrics["tier1_found"] == 0.5
    assert rep.metrics["over_ranked"] == 1
    assert rep.metrics["traps_handled"] == 0.0
    assert rep.metrics["new_tier1_or_2_finds"] == 1
    assert not rep.passed


def test_recalibrate_waits_for_enough_outcomes(tmp_path, role):
    out = tmp_path / "outcomes.csv"
    write_csv(out, ["name", "stage", "result", "passed_signals", "failed_signals"],
              [{"name": "A B", "stage": "System design", "result": "not advanced", "passed_signals": "", "failed_signals": "money_state"}])
    rep = recalibrate.recalibrate(role, out, tmp_path / "none.csv")
    assert "note" in rep


def test_recalibrate_raises_decisive_predictive_signals(tmp_path, role):
    outcomes = tmp_path / "outcomes.csv"
    rows = []
    for i in range(6):
        adv = i < 3
        rows.append({"name": f"Person {chr(65 + i)}x", "stage": "System design",
                     "result": "advanced" if adv else "not advanced",
                     "passed_signals": "money_state" if adv else "", "failed_signals": "" if adv else "money_state"})
    write_csv(outcomes, ["name", "stage", "result", "passed_signals", "failed_signals"], rows)
    matrix = tmp_path / "signal_matrix.csv"
    ids = [s["id"] for s in role["interview_signals"]]
    write_csv(matrix, ["Name", "Tier", *ids], [
        {"Name": r["name"], "Tier": "Tier 1", **{i: ("met" if (i == "money_state" and r["result"] == "advanced") else "no evidence") for i in ids}}
        for r in rows
    ])
    rep = recalibrate.recalibrate(role, outcomes, matrix)
    sig = rep["signals"]["money_state"]
    assert sig["evidence_lift"] == 1.0
    assert sig["new_weight"] > sig["old_weight"]
    assert rep["signals"]["ai_with_verification"]["new_weight"] <= rep["signals"]["ai_with_verification"]["old_weight"] * 1.01
