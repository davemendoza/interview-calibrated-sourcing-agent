# Build Your Ecosystem Map

The agent only searches where you point it. The **ecosystem map** in your role file is that list: every place where people in your job family leave public evidence of their work. A thin map gives thin results. A complete one is what makes the agent work.

This page gives you two ways to build it:

* **A. Have Claude draft it** with the prompt below (about 15 minutes, plus your review).
* **B. Fill in the template by hand** in `config/roles/TEMPLATE_role.toml`. Every category has a commented example you copy and complete.

Either way, run `icsa ecosystem` afterwards. It shows how many entries you have in each category and which categories are still empty.

---

## How the map is organized

Work in two steps. Skipping the first is the most common reason a search comes back thin.

**Step 1. Map the company landscape.** List the companies where people in this job family work today, grouped into talent markets. For Staff payments engineers that means groups like open banking and data aggregation, pay-by-bank, processors and acquirers, payment orchestration, ledgers and payment operations, fraud and risk, identity and KYC, bot defense and API security, neobanks, and big-tech payments teams. Include adjacent markets where the same skills live, not just direct competitors.

**Step 2. Find each market's public footprint.** For the companies and communities in each market, find where their engineers leave evidence:

| Category | What to look for | How the agent uses it |
|---|---|---|
| **code** | Open-source repos central to the field: libraries, SDKs, frameworks, databases | **harvest**: contributors become leads |
| **patents** | Companies that file patents in the field, spelled exactly as on USPTO filings | **harvest**: inventors become leads, with their city |
| **research** | Institutions that publish papers in the field | **harvest**: authors become leads |
| **blogs** | Engineering blog feeds | **harvest** if posts name their authors; otherwise **taxonomy** |
| **conferences** | Engineering conferences, especially ones on Sessionize | **harvest** for Sessionize events; **verify** for other speaker pages |
| **meetups** | Local meetups for the field and its infrastructure | **verify**: past-event speaker pages |
| **associations** | Industry bodies and standards groups | **taxonomy** and **verify** only: member lists are rarely public |
| **standards** | Rule books, specifications, regulator pages | **taxonomy**: the vocabulary the field actually uses |
| **packages** | Independently maintained libraries on PyPI or npm | **harvest**: maintainers become leads |

The three uses:

* **harvest** finds new people. It needs a `source` and a `value`.
* **verify** confirms people the agent already found elsewhere. A name on a web page never creates a lead on its own.
* **taxonomy** teaches the agent the field's language. Run `icsa taxonomy` to see recurring phrases from these pages that your role file doesn't cover yet, then copy the useful ones into your domain requirement's terms.

## Rules that keep the map trustworthy

1. **Open every URL yourself before adding it.** Never add a guessed address. If you used Claude to draft the map, check its links too.
2. **Be honest about what a source can support.** A blog feed without author names cannot create leads. An association member list behind a login is not a lead list.
3. **Prefer places where individual contributors show up.** Large industry shows skew toward executives. Engineering conferences, infrastructure meetups and open-source projects surface more of the people who do the work.
4. **Cover adjacent markets.** The strongest candidates often sit one market over: a ledger engineer at a brokerage, a bot-defense engineer at a security company.
5. **Re-check quarterly.** Feeds move, events change platforms, and new repos become central.

---

## Prompt: have Claude draft your ecosystem map

Use this with Claude (with web search turned on). Paste it, then paste your job description underneath. Claude drafts the entries; you review every one before using them.

```text
You are helping me configure an open-web sourcing agent. Build the [[ecosystem]] section
of its role file for the job below. The agent finds people by their public work, so the
map must list real places where people in this job family leave checkable evidence.

Job family and level: [e.g. Staff Software Engineer, payments infrastructure]
Target locations: [e.g. San Francisco Bay Area, New York City]
Job description: [paste below]

Work in two steps.

STEP 1. Company landscape.
Group the companies where people in this job family work into 8 to 15 talent markets,
including adjacent markets where the same skills live. For each market, list 5 to 10
companies. Show this as a table before moving on.

STEP 2. Public footprint, as [[ecosystem]] entries.
For each market, find where its engineers leave public evidence, covering every category:
code, patents, research, blogs, conferences, meetups, associations, standards, packages.

Format every entry exactly like this (TOML):
[[ecosystem]]
category = "code"            # code | patents | research | blogs | conferences | meetups | associations | standards | packages | other
name = "..."
use = "harvest"              # harvest | verify | taxonomy
source = "github_repo"       # harvest only: github_repo | patent_assignee | openalex_institution | sessionize | rss | pypi | npm
value = "owner/repo"         # harvest only
url = "https://..."          # verify and taxonomy only
org = "..."                  # optional: employer behind a blog feed
notes = "..."                # why this source matters and anything to check

Rules:
- Only include URLs, repos, feeds, packages and event ids you have confirmed exist by
  searching or opening them. If you cannot confirm something, list it separately under
  "To check" instead of writing an entry. Never guess an address.
- A blog feed is "harvest" only if its posts name their authors. Otherwise use "taxonomy".
- Associations and standards bodies are "taxonomy" or "verify", never "harvest".
- Patent assignee names must match how the company appears on USPTO filings.
- Favor sources where individual contributors appear (open-source projects, engineering
  conferences, infrastructure meetups) over executive-heavy industry shows.
- Aim for at least 25 entries, with every category represented where the field supports it.

Finish with:
1. A coverage table: category, number of entries, uses.
2. A "To check" list of promising sources you could not confirm.
3. 15 to 30 domain terms (lowercase) the agent should search for: the vocabulary that marks
   real work in this field, including team names and problems that titles hide.
```

## After Claude drafts the map

1. Open every link. Delete anything that doesn't load or isn't what it claims to be.
2. Paste the entries into your role file, replacing the ecosystem section.
3. Run `icsa ecosystem` and fill any empty categories by hand.
4. Run `icsa taxonomy` and add the useful suggested terms to your domain requirement.
5. Run `icsa run`, then `icsa eval` against your test set. If the agent misses people you know are strong, look at where they leave evidence and add that place to the map.

That last step is how the map gets better over time: every strong person the agent misses shows you a part of the ecosystem you haven't mapped yet.
