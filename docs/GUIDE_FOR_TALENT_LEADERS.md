# Start Here: A Plain-English Guide for Talent Leaders

You do not need to code to use this. If you can fill in a spreadsheet and copy and paste, you can run your own version.

---

## What this does, in one paragraph

You tell the agent what your best interviewers listen for. It then searches public places where engineers leave proof of their work (code they wrote, patents, research papers, conference talks) and finds people who show those strengths. Every person it suggests comes with links you can click to check the proof yourself. After your interviews, you tell it who passed and why, and it gets better at spotting those people next time.

---

## What you need before you start

| You need | How long it takes | Why |
|---|---|---|
| Notes on why candidates passed or failed your interviews | 20 minutes | This is what the agent learns to look for |
| A list of 10 to 50 people you have already rated | 30 minutes | This is how you check the agent before trusting it |
| A computer (Mac or Windows) | | It runs on your own computer, so your data stays with you |
| A free GitHub account | 5 minutes | GitHub is where the code lives and where many engineers share their work |

---

## Two ways to set it up

### Option A (easiest): ask Claude to do the technical part for you

If you use Claude (the Claude desktop app with a folder connected, or Claude Code), copy the message below, paste it in, and attach your notes and your list. Claude will do the setup and ask you questions in plain language.

> Please set up the Interview-Calibrated Sourcing Agent for me from https://github.com/davemendoza/interview-calibrated-sourcing-agent on my computer. I am not technical, so explain each step in one plain sentence and do the commands for me.
>
> 1. Download it into a folder called "sourcing-agent" in my Documents.
> 2. Make my own role file from config/roles/TEMPLATE_role.toml using my attached interview notes. The role I am hiring for is: [write the job title here].
> 3. Put my attached list of people I have already rated into the data folder as the test set.
> 4. Help me get a free GitHub token and add it to the .env file.
> 5. Run it, check it against my test set, and tell me in plain words whether it passed and what to fix.
>
> Never put real people's names into anything that gets uploaded to GitHub.

Then skip to **Step 5: Read your results** below.

### Option B: do it yourself, step by step

Follow Steps 1 to 6. Each step says what to do and what you should see.

---

## Step 1: Write down what decides your interviews (no computer needed)

Think about your last 10 or so interviews for this role. For each thing below, write one or two sentences.

| Question | Example answer |
|---|---|
| What follow-up question do strong candidates answer well and weak ones fumble? | "What happens when the call times out? Strong people explain how they stop the customer being charged twice." |
| What did your best hires have that others did not? | "They could name one decision they made, who disagreed, and how it turned out." |
| What looked good on paper but fell apart in the interview? | "Big titles but they could not explain anything they built themselves." |
| What words would show up in someone's public work if they had this strength? | "reconciliation, retries, ledger, postmortem" |

These become the agent's **interview signals**. You will put them in the role file in Step 3.

## Step 2: Make your check list (a spreadsheet)

The easiest way: download the ready-made workbook, [`templates/Calibration_Workbook_TEMPLATE.xlsx`](../templates/Calibration_Workbook_TEMPLATE.xlsx). It has a tab for this list, a tab for interview outcomes (Step 6), and a summary tab that shows which signals separate people who advance from people who do not. Yellow cells are yours to fill in. Save your copy in the `data` folder as `calibration_workbook.xlsx`.

If you prefer your own spreadsheet, use three columns with exactly these names:

| Name | Your tier | Test challenge |
|---|---|---|
| Full name of someone you already know | Tier 1, Tier 2, Tier 3 or Trap | Anything tricky about this person (optional) |

* **Tier 1** = you would call them today. **Tier 2** = worth a call. **Tier 3** = maybe later.
* **Trap** = someone a tool could easily get wrong. Examples: two people with the same name, someone whose best work is old, or a big title with nothing you can check.
* Aim for about 20 Tier 1, 15 Tier 2, 10 Tier 3 and 5 Traps. Fewer is fine to start.
* Rate everyone **before** you run the agent, so the agent cannot sway your judgment.

Save it as `test_set.xlsx` (or use the workbook's **Test Set** tab).

## Step 3: Install and fill in your role file (about 20 minutes, one time)

On a Mac, open the **Terminal** app (press Command and Space, type Terminal, press Return). Copy and paste each line below, one at a time, and press Return after each.

```bash
cd ~/Documents
git clone https://github.com/davemendoza/interview-calibrated-sourcing-agent sourcing-agent
cd sourcing-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
cp config/roles/TEMPLATE_role.toml config/roles/my_role.toml
open config/roles/my_role.toml
```

The last line opens your role file. Every line marked **>>> CUSTOMIZE** is something you fill in. Use your notes from Step 1. Type text between the quote marks, and lists of words like this: `["ledger", "retries", "postmortem"]`.

**Your GitHub key:** sign in at github.com, open Settings, then Developer settings, then Personal access tokens, then Tokens (classic). Choose **Generate new token**, tick nothing, and create it. Copy the token, run `open .env`, and paste it after `GITHUB_TOKEN=`. Save the file.

Move your Step 2 spreadsheet into the `data` folder inside `sourcing-agent`.

## Step 4: Run it

In Terminal (from the `sourcing-agent` folder), paste:

```bash
source .venv/bin/activate
icsa run --role config/roles/my_role.toml
```

It takes a few minutes. When it finishes you will see a short summary and either **GATE PASSED** or **GATE FAILED**.

## Step 5: Read your results

Open `out/leads.xlsx`. It has three tabs:

* **Leads:** one row per person, best first.
* **Evidence:** every piece of proof, with a link you can click.
* **Screen Questions:** for each strong lead, the questions to ask on the first call about things the agent could not find proof of.

What the labels mean:

| You see | It means | What to do |
|---|---|---|
| Tier 1, Strong Recommend | Proof from more than one place | Check the links, then reach out |
| Tier 2, Recommend | Real proof from one place | Check the links; worth a call |
| Tier 3, Pipeline depth | Light proof (for example, one talk) | Keep for later |
| Pending research | No proof found yet | Not a rating. Do not treat it as a "no" |
| Identity review | Two different people may share this name | Check by hand before using anything about them |
| Location not found | No public proof of where they live | Confirm before outreach |

**If you see GATE FAILED,** the agent missed people you know are strong, rated someone too high, or mixed up two people. The message says which. The usual fix is to add more words to your role file (Step 3) and run again.

**The first time,** it will ask you to confirm identities. Open `data/identity_review.csv`, and in the **Right person** column type `yes` or `no` for each person. You only do this once per person.

## Step 6: After interviews, tell it what happened

Use the **Outcomes** tab of your calibration workbook (or a spreadsheet called `outcomes.csv` in the `data` folder) with these columns:

| name | stage | result | passed_signals | failed_signals |
|---|---|---|---|---|
| Candidate's full name | e.g. System design | advanced or not advanced | signal names they did well on | signal names that cost them the round |

Signal names are the `id` values in your role file (for example `owned_decision`). Separate more than one with a semicolon.

Once you have at least 5 outcomes, run:

```bash
icsa recalibrate --role config/roles/my_role.toml
```

The agent will tell you which signals mattered most, and it will weigh them more heavily from then on. The workbook's **Signal Summary** tab shows the same story at a glance, and [How the agent learns](HOW_THE_AGENT_LEARNS.md) explains the numbers in plain terms.

---

## If something goes wrong

| What you see | What it means | Fix |
|---|---|---|
| `command not found: icsa` | Terminal forgot the setup | Run `source .venv/bin/activate` first |
| `[github] skipped: ... rate limit` | GitHub needs a short rest | Wait an hour, or check your token in `.env` |
| `[patents] skipped: PATENTSVIEW_API_KEY is not set` | Patent search is off | Optional. Request a free key on patentsview.org and add it to `.env` |
| `[role file] ... is empty` | A **>>> CUSTOMIZE** line is not filled in | Open your role file and fill it in |
| Everyone shows Pending research | The agent does not know your field's words yet | Add more words to the `domain` requirement in your role file |

## Ground rules that keep you safe

* Real names stay in the `data` and `out` folders on your computer. Those folders are never uploaded.
* The agent only uses emails people published themselves.
* Always click at least one evidence link before contacting someone.
* The agent suggests; you decide. It never contacts anyone.
