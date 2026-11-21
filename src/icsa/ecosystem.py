"""The talent ecosystem map: one list in the role file, read by every harvester.

Each [[ecosystem]] entry is one place where people in the target job family
leave evidence, tagged with how the agent may use it:

  use = "harvest"   the agent finds new leads there (needs `source` and `value`)
  use = "verify"    a page that confirms people already found elsewhere
                    (speaker, meetup, working-group pages); never creates leads
  use = "taxonomy"  a page the agent reads to learn the field's vocabulary
                    (`icsa taxonomy` suggests terms from it)

Harvest sources:
  github_repo           value = "owner/repo"
  patent_assignee       value = company name exactly as on USPTO filings
  openalex_institution  value = institution name
  sessionize            value = Sessionize event id (public speaker API)
  rss                   value = RSS or Atom feed URL whose posts name their authors
  pypi / npm            value = package name

Run `icsa ecosystem` to see coverage by category and what is missing.
"""

from __future__ import annotations

from collections import Counter, defaultdict

CATEGORIES = [
    "code", "patents", "research", "blogs", "conferences",
    "meetups", "associations", "standards", "packages", "other",
]
USES = {"harvest", "verify", "taxonomy"}
HARVEST_SOURCES = {"github_repo", "patent_assignee", "openalex_institution", "sessionize", "rss", "pypi", "npm"}

# What each category can honestly support. Shown in `icsa ecosystem` so users
# don't expect lead lists from places that cannot provide them.
CATEGORY_GUIDANCE = {
    "code": "harvest: contributors to repos central to the job family",
    "patents": "harvest: inventors on filings from companies in the field",
    "research": "harvest: authors from institutions that publish in the field",
    "blogs": "harvest if the feed names authors; otherwise taxonomy",
    "conferences": "harvest via Sessionize when available; otherwise verify",
    "meetups": "verify: past-event speaker pages; repeat speakers and organizers",
    "associations": "taxonomy and verify only: member lists are rarely public",
    "standards": "taxonomy: rule books and specs that define the field's vocabulary",
    "packages": "harvest: maintainers of libraries the field depends on",
    "other": "any source that fits none of the above",
}


def entries(role: dict) -> list[dict]:
    return list(role.get("ecosystem", []))


def check(role: dict) -> list[str]:
    problems = []
    for i, e in enumerate(entries(role), start=1):
        tag = f"ecosystem entry {i} ({e.get('name') or 'unnamed'})"
        if not e.get("name"):
            problems.append(f"{tag}: add a name")
        if e.get("category") not in CATEGORIES:
            problems.append(f"{tag}: category must be one of {', '.join(CATEGORIES)}")
        use = e.get("use")
        if use not in USES:
            problems.append(f"{tag}: use must be harvest, verify or taxonomy")
        elif use == "harvest":
            if e.get("source") not in HARVEST_SOURCES:
                problems.append(f"{tag}: harvest entries need source = one of {', '.join(sorted(HARVEST_SOURCES))}")
            if not e.get("value"):
                problems.append(f"{tag}: harvest entries need a value (repo, company, event id, feed URL or package)")
        elif not str(e.get("url", "")).startswith("http"):
            problems.append(f"{tag}: {use} entries need a full url")
    src = role.get("sources", {})
    seeds = [src.get("github", {}).get("repos"), src.get("patents", {}).get("assignees"),
             src.get("openalex", {}).get("institutions"), src.get("talks", {}).get("sessionize_ids"),
             src.get("blogs", {}).get("feeds"), src.get("packages", {}).get("pypi"), src.get("packages", {}).get("npm")]
    if not any(seeds):
        problems.append("no harvest sources yet: add [[ecosystem]] entries (see docs/BUILD_YOUR_ECOSYSTEM.md); the agent has nowhere to search")
    return problems


def apply(role: dict) -> dict:
    """Merge ecosystem entries into the harvester settings in role['sources']."""
    src = role.setdefault("sources", {})
    taxonomy_pages: list[str] = role.setdefault("taxonomy_pages", [])

    def add(section: str, key: str, value, defaults: dict | None = None) -> None:
        cfg = src.setdefault(section, dict(defaults or {}))
        items = cfg.setdefault(key, [])
        if value not in items:
            items.append(value)

    for e in entries(role):
        use, source, value, url = e.get("use"), e.get("source"), e.get("value"), e.get("url")
        if use == "verify" and url:
            add("talks", "pages", url)
        elif use == "taxonomy" and url and url not in taxonomy_pages:
            taxonomy_pages.append(url)
        elif use == "harvest" and value:
            if source == "github_repo":
                add("github", "repos", value, {"min_contributions": 10, "max_contributors_per_repo": 60})
            elif source == "patent_assignee":
                add("patents", "assignees", value, {"endpoint": "https://search.patentsview.org/api/v1/patent/",
                                                    "since": "2021-01-01", "max_per_assignee": 300})
            elif source == "openalex_institution":
                add("openalex", "institutions", value, {"since": "2019-01-01", "max_per_query": 50})
            elif source == "sessionize":
                add("talks", "sessionize_ids", value)
            elif source == "rss":
                add("blogs", "feeds", {"url": value, "org": e.get("org"), "name": e.get("name")})
            elif source in ("pypi", "npm"):
                add("packages", source, value)
    return role


def coverage(role: dict) -> list[tuple[str, int, str, str]]:
    """Rows of (category, entries, uses, guidance) for every category."""
    by_cat: dict[str, Counter] = defaultdict(Counter)
    for e in entries(role):
        by_cat[e.get("category", "other")][e.get("use", "?")] += 1
    rows = []
    for cat in CATEGORIES:
        uses = by_cat.get(cat, Counter())
        rows.append((cat, sum(uses.values()), ", ".join(f"{u} {n}" for u, n in sorted(uses.items())), CATEGORY_GUIDANCE[cat]))
    return rows
