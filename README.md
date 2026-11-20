# Interview-Calibrated Sourcing Agent

**Open-web sourcing that learns from post-interview evaluations.**

> **New to this, or not technical?** Start with the [plain-English guide for talent leaders](docs/GUIDE_FOR_TALENT_LEADERS.md). It walks you through running your own version in six steps, or having Claude set it up for you.
>
> **[Download the calibration workbook (Excel)](https://github.com/davemendoza/interview-calibrated-sourcing-agent/raw/main/templates/Calibration_Workbook_TEMPLATE.xlsx)** to record your own interview signals, the people you have already rated, and interview outcomes. Fill in the yellow cells; the How to Use tab explains each step.

Most sourcing tools re-rank the same LinkedIn profiles every other recruiter sees. This agent finds engineers by the work they have done in public, then calibrates what it looks for using the signals that actually decided interview outcomes.

It started from a simple finding: when post-interview feedback for a Staff engineering loop was analyzed, candidates rarely failed the first question. They failed the follow-up. "What did you personally decide?" "What does the caller get when that payment call times out?" "How would you prove the AI output is correct?" Those deciding signals should be the first thing a sourcer looks for, and interview results should flow back into how leads are scored.

![Leads tab with fictional demo data: tiered leads, identity checks, interview signals and screen questions](docs/images/leads-demo.png)

*What the agent returns, using fictional demo data scored by the agent's real rules. [Close-up: tiered leads](docs/images/leads-demo-closeup-tiers.png) · [Close-up: namesakes and screen questions](docs/images/leads-demo-closeup-identity-questions.png)*

## How it works

Two pages explain the parts most people ask about:
* [How the agent learns who succeeds](docs/HOW_THE_AGENT_LEARNS.md): the calibration workbook, the test gate, and how interview outcomes reweight signals.
* [Plain-English guide for talent leaders](docs/GUIDE_FOR_TALENT_LEADERS.md)

![How the agent learns who succeeds](docs/images/learning-loop.png)

```
 Stage 0  Interview calibration    signals that decided past interviews, with weights
    |
 Stage 1  Harvest open web         GitHub commits, USPTO patents, OpenAlex papers, conference talks
    |
 Stage 2  Identity gate            never merge on name alone; two independent signals required
    |
 Stage 3  Score evidence           met / not met / no evidence per requirement, each with a link
    |
 Stage 4  Output                   tiered leads, evidence sheet, screen questions for every gap
    |
 Stage 5  Test gate                must find your known Tier 1s and never mix up people
    |
 Stage 6  Recalibrate              interview outcomes adjust signal weights for the next run
    '------------------------------> back to Stage 0
```

### Stage 0: interview calibration
Each role file lists the interview signals that decide outcomes, with search terms, a weight and a screen question. The fintech example role uses five (the template keeps the four generic ones and leaves room for your own):

| Signal | What the interviewers listened for |
|---|---|
| `money_state` | Idempotency, unknown outcomes, timeouts, reconciliation |
| `owned_decision` | One decision the person made and defended, with alternatives and a result |
| `incident_to_prevention` | An incident told from detection through to process change |
| `cross_team_influence` | Influence through a mechanism: contracts, reviews, shared libraries |
| `ai_with_verification` | AI use with a concrete story of catching a wrong output |

A signal with public evidence raises the lead's signal score. A signal with no evidence becomes a specific screen question for that lead, so the recruiter screen closes gaps instead of repeating the resume.

### Stage 2: the identity gate
Evidence is first grouped by its own source (a GitHub account, a patent inventor in one city, an OpenAlex author, a conference speaker). Two groups with the same name merge only when a second signal agrees: the same employer, a link from one to the other's GitHub or website, the same self-published email, or the same metro with no conflicting employer. Same-name records that cannot be corroborated are marked **Identity review** and are never scored. This rule exists because name-only matching attaches one person's work to a namesake.

### Stage 3: scoring rules
Fail-closed: no evidence means no score.

| Rule | Why |
|---|---|
| No payments-domain evidence → **Pending research**, not a guessed tier | A missing signal is unknown, not zero |
| Domain evidence across 2+ channels, or 75+ seed-repo commits → **Tier 1** (Strong Recommend) | Proof from more than one place |
| One strong channel → **Tier 2** (Recommend) | Real, but thinner |
| Talk-only → capped at **Tier 3** | A talk alone is not checkable work |
| Patent-only → capped at **Tier 2** | Strong signal, little public code |
| Domain evidence older than `recency_years` → drop one tier | Old payments work is not current fit |
| Evidence follows the person | Payments work done at a former employer still counts |

### Stage 5: the test gate
Before sourcing a role live, run the agent against people you have already tiered (20 Tier 1, 15 Tier 2, 10 Tier 3 and 5 traps is a good size). Traps are cases you have caught before: namesakes, people whose best evidence is old, strong titles with no checkable work. The gate fails if:

* fewer than 70% of your Tier 1s are found
* tier agreement is below 60%
* anyone is called Tier 1 that you did not rate Tier 1
* fewer than 80% of scored claims carry a source
* any wrong-person match is found, or identity has not been checked

### Stage 6: recalibrate from outcomes
After each interview round, add rows to the **Outcomes** tab of your calibration workbook ([template](templates/Calibration_Workbook_TEMPLATE.xlsx), saved as `data/calibration_workbook.xlsx`), or to `data/outcomes.csv` with the same columns:

```
name,stage,result,passed_signals,failed_signals
```

`result` is `advanced` or `not advanced`. Signal lists use the signal ids, separated by semicolons. `icsa recalibrate` then:

* raises the weight of signals interviewers named as the reason for a pass or a rejection
* raises signals whose public evidence (found before outreach) went with candidates who advanced, and lowers those that did not
* changes nothing until there are at least 5 outcomes

## Quick start

```bash
git clone https://github.com/davemendoza/interview-calibrated-sourcing-agent
cd interview-calibrated-sourcing-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # add GITHUB_TOKEN, PATENTSVIEW_API_KEY, OPENALEX_MAILTO
pytest                        # all tests use fictional people

icsa run                      # harvest, score, and evaluate if data/test_set.xlsx exists
icsa eval                     # re-run the test gate
icsa recalibrate              # after adding interview outcomes
```

Results land in `out/leads.xlsx` with three tabs: **Leads**, **Evidence** (every claim with its link) and **Screen Questions** (one per missing signal, Tier 1 and 2 only).

Run a single source with `icsa harvest --only github patents`.

### Nightly run (macOS or Linux)
```bash
crontab -e
# 2:17 AM every night
17 2 * * * cd $HOME/interview-calibrated-sourcing-agent && ./scripts/nightly.sh >> out/nightly.log 2>&1
```

## Adapt it to your domain

The engine is domain-neutral. Everything specific to a field lives in a role file, and every line you are expected to change is marked `>>> CUSTOMIZE`.

| File | Use it for |
|---|---|
| `config/roles/TEMPLATE_role.toml` | Starting a new domain. Blank, with generic interview signals and every field to fill marked |
| `config/roles/example_fintech_staff_payments_engineer.toml` | A complete worked example from fintech (payments vocabulary, seed repos, patent assignees) |

What you can change without touching code:

* **Labels people see**, in the `[labels]` table: the domain name used in messages ("No payments evidence found yet"), the tier words (Strong Recommend, Recommend, Pipeline depth), and the status words (Pending research, Identity review).
* **Interview signals**: the follow-ups that decided your interviews, with search terms and a screen question.
* **Requirements**: your domain vocabulary. The `domain` requirement decides whether a lead is scored at all.
* **Sources**: seed repos, patent assignees, research institutions, conference events.

If a `>>> CUSTOMIZE` field is left empty, the agent prints a plain-language warning and scores nobody rather than guessing.

```bash
cp config/roles/TEMPLATE_role.toml config/roles/my_role.toml
icsa run --role config/roles/my_role.toml
```

## Sources

| Channel | Source | Key needed |
|---|---|---|
| Commits | GitHub REST API, contributors to seed repos | Personal token (free) |
| Patents | PatentsView PatentSearch API (USPTO) | Free key |
| Papers | OpenAlex | None (email recommended) |
| Talks | Sessionize public speaker JSON; agenda pages for verification only | None |

Edit seed repos, patent assignees, institutions and events in your role file.

## Data and privacy

* Everything about real people stays in `data/` and `out/`, which git ignores.
* Emails are recorded only when the person published them on their own profile or site.
* A name on a web page never creates a lead by itself.
* Every claim keeps its source URL so it can be checked, corrected or removed.

## Project layout

```
config/roles/          TEMPLATE_role.toml plus a fintech example; one file per role
docs/                  talent leader guide, how the agent learns, demo images
templates/             calibration workbook (Signals, Test Set, Outcomes, Signal Summary)
examples/              fictional outcomes that reproduce the learning-loop image
src/icsa/harvesters/   github, patents, openalex, talks (parse functions are pure and tested)
src/icsa/identity.py   identity gate
src/icsa/scorer.py     fail-closed tiering
src/icsa/evaluate.py   test gate against your tiered test set
src/icsa/recalibrate.py  learning from interview outcomes
tests/                 fictional fixtures only
```

## Roadmap

* Engineering blog bylines and package-registry maintainers as harvesters
* A skeptic pass that tries to disprove each Tier 1 before a person sees it
* Job-change monitoring for Tier 1 leads
* Trajectory scoring: how fast someone's scope is rising, not only where it is today

Built by Dave Mendoza, Talent Engine.
