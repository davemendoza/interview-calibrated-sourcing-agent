# Run a Pilot on a Real Role

A step-by-step guide for a talent leader who wants to test the agent on one critical software engineering role and collect numbers for a case study. Plan on about half a day of setup, then about 30 minutes per interview round to log outcomes.

## What you need

* A laptop with Python 3.11 or newer and Git
* One open Staff or Senior software engineering role
* Five to eight people you already know are strong, a few you know are not, and one or two with common names (the traps). They can be past hires, past finalists, or people on the team
* The interview feedback from your last few rounds for this kind of role
* Optional: an Anthropic API key for the AI judge (`--judge`). Skip it if your policy does not allow sending public evidence to a third party
* Counsel's agreement on lawful basis and candidate notice before you contact anyone found (see [Known limits](KNOWN_LIMITS_AND_ROADMAP.md))

## 1. Install

```
git clone https://github.com/davemendoza/interview-calibrated-sourcing-agent
cd interview-calibrated-sourcing-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,pdf]"
pytest -q                      # every test should pass before you start
```

Optional judge: copy your key into a file named `.env` as `ANTHROPIC_API_KEY=...`. That file is never uploaded.

## 2. Write down what decided your interviews

1. Copy `templates/Calibration_Workbook_TEMPLATE.xlsx` to `data/calibration_workbook.xlsx`.
2. **Signals tab:** list four to six things that separated people who advanced from people who did not in past rounds, each with a screen question. Use your own words, for example "explains what happens when a request times out and the outcome is unknown".
3. **Test Set tab:** list 10 to 30 people with a tier (1, 2, 3 or Trap). Rate them before the agent runs. Do not change ratings after seeing its output.
4. **Outcomes tab:** add rows from past rounds if you have them. Each row is one person at one stage: advanced or not, signals credited, signals that cost the round.

## 3. Make a role file for the role

```
cp config/roles/TEMPLATE_role.toml config/roles/my_role.toml
```

Open it and fill every line marked `>>> CUSTOMIZE`: role title, domain name, target metros, the domain terms a person in this work would use, and your signals with their search terms. Check it:

```
icsa ecosystem --role config/roles/my_role.toml
```

The command warns about any field left empty. Add the public places this kind of engineer leaves evidence (code orgs, conferences, blogs, standards bodies). [Build your ecosystem map](BUILD_YOUR_ECOSYSTEM.md) has a prompt that drafts this for you.

## 4. Run and read the test gate

```
icsa run --role config/roles/my_role.toml
```

This harvests public evidence, checks identity, scores, and compares the result with your Test Set. Files land in `out/`:

* `leads.xlsx` and `leads.csv`: tiered leads with evidence, identity status, screen questions and an Integrity column
* `integrity.csv`: evidence held back by the hidden-text guard, with reasons
* `signal_matrix.csv`: which signals each person showed
* `data/identity_review.csv`: open it and mark **Right person** yes or no for every surfaced test-set person, then run `icsa eval`

The gate passes when at least 70% of your Tier 1 people are found, at least 60% of tiers match yours, nobody is wrongly called Tier 1, at least 80% of claims carry a link, and the wrong-person rate is 0%. If it fails, fix the role file or sources and run again before sourcing live. `icsa eval` ends with a one-sentence, name-free summary you can quote.

## 5. Screen the resumes you already hold

```
icsa guard path/to/finalist_resumes/
```

Any file marked HOLD has hidden or instructing text. Read it yourself before anything scores it. See [Hidden-text guard](HIDDEN_TEXT_GUARD.md).

## 6. Source for the real role

Open `out/leads.xlsx`. Work Tier 1 first. For each lead, open the evidence links and read the actual work before any outreach. Use the Screen Questions tab for signals with no public evidence. Do not contact anyone marked Integrity review until you have read why.

Add `--judge` to `icsa run` or `icsa score` to have an AI confirm each Tier 1 and Tier 2 signal. It must quote the exact words from the evidence or the signal is rejected.

## 7. Log outcomes and let it learn

After each interview round, add one row per candidate to the Outcomes tab (or `data/outcomes.csv`). Then:

```
icsa recalibrate --role config/roles/my_role.toml
icsa score --role config/roles/my_role.toml
```

Nothing changes until there are at least five outcomes. Note that learning reorders leads inside a tier; it does not move people across tiers (see known limits).

## 8. Metrics to collect for a case study

Record these in a plain sheet, one row per run or per week. All can be shared without naming anyone.

| Metric | Where it comes from |
|---|---|
| Test gate result (Tier 1 found, tier agreement, over-ranked, wrong-person rate) | `icsa eval` output |
| Leads surfaced, by tier | End of `icsa run` |
| New Tier 1 or 2 leads you had not found yourself | `icsa eval` summary |
| Leads contacted, replied, screened, advanced, by tier | Your ATS, by hand |
| Hours spent per advanced candidate, compared with your usual sourcing | Your own log |
| Items held by the guard, and how many were real | `out/integrity.csv` |
| Whether the Tier 1 list stays stable when you re-run it | Run twice, compare |

Compare against a baseline: the same role sourced the usual way for the same number of weeks. Say plainly how many roles and runs the numbers come from. One role is a pilot, not proof.

## 9. Clean up

Evidence and outputs live in `data/` and `out/` on your machine only. Delete both folders when the pilot ends, and delete any person's rows on request.
