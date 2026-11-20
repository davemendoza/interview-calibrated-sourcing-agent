"""GitHub: contributors to seed repos, with their own public profile fields.

Commits are bound to an account, so commit evidence and the profile it came
from are the same entity. Cross-source matching happens later in identity.py.
"""

from __future__ import annotations

import os
from typing import Iterator

from ..http import Http
from ..models import Evidence

API = "https://api.github.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def parse_contributor(repo: str, contributor: dict, profile: dict, last_commit: dict | None) -> Evidence | None:
    """Build one commit Evidence from API payloads. Returns None for bots or nameless accounts."""
    login = contributor.get("login") or ""
    if contributor.get("type") == "Bot" or login.endswith("[bot]") or "bot" == login.lower()[-3:]:
        return None
    name = (profile.get("name") or "").strip()
    if not name or " " not in name:
        # A login alone is not a person's name; skip rather than guess.
        return None
    commits = int(contributor.get("contributions") or 0)
    date = None
    if last_commit:
        date = ((last_commit.get("commit") or {}).get("author") or {}).get("date", "")[:10] or None
    links = [u for u in [profile.get("blog"), profile.get("html_url")] if u]
    links = [u if u.startswith("http") else f"https://{u}" for u in links]
    return Evidence(
        person_name=name,
        channel="commit",
        title=f"{commits} commits to {repo}",
        url=f"https://github.com/{repo}/commits?author={login}",
        source_key=f"github:{login.lower()}",
        date=date,
        org=(profile.get("company") or "").strip() or None,
        location=(profile.get("location") or "").strip() or None,
        handle=login,
        links=links,
        email=profile.get("email") or None,  # public profile email only
        text=f"{repo} {profile.get('bio') or ''}",
        count=commits,
    )


def harvest(cfg: dict, http: Http | None = None) -> Iterator[Evidence]:
    http = http or Http()
    h = _headers()
    min_c = int(cfg.get("min_contributions", 10))
    cap = int(cfg.get("max_contributors_per_repo", 60))
    for repo in cfg.get("repos", []):
        contributors = http.get_json(f"{API}/repos/{repo}/contributors", {"per_page": 100}, h) or []
        for c in contributors[:cap]:
            if int(c.get("contributions") or 0) < min_c:
                continue
            login = c.get("login")
            if not login:
                continue
            profile = http.get_json(f"{API}/users/{login}", None, h)
            commits = http.get_json(f"{API}/repos/{repo}/commits", {"author": login, "per_page": 1}, h)
            ev = parse_contributor(repo, c, profile, commits[0] if commits else None)
            if ev:
                yield ev
