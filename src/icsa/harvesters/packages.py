"""Package registries: maintainers of libraries the job family depends on.

Company SDKs usually list the company as author, which creates no lead.
Independently maintained libraries name a person, and their repository link
lets the identity gate connect the package to a GitHub account.
"""

from __future__ import annotations

from typing import Iterator

from ..http import Http
from ..models import Evidence, looks_like_person


def _person(name: str | None) -> str | None:
    name = (name or "").strip()
    return name if looks_like_person(name) else None


def parse_pypi(payload: dict) -> Iterator[Evidence]:
    info = payload.get("info") or {}
    pkg = info.get("name") or ""
    urls = [u for u in (info.get("project_urls") or {}).values() if u] + [info.get("home_page") or ""]
    links = [u for u in urls if u.startswith("http")]
    releases = payload.get("releases") or {}
    dates = [f.get("upload_time", "")[:10] for files in releases.values() for f in files or [] if f.get("upload_time")]
    for raw in {info.get("author"), info.get("maintainer")}:
        person = _person(raw)
        if person:
            yield Evidence(
                person_name=person, channel="package",
                title=f"Maintainer of PyPI package {pkg}",
                url=f"https://pypi.org/project/{pkg}/",
                source_key=f"pypi:{pkg}:{person.lower()}",
                date=max(dates) if dates else None,
                links=links, text=f"{pkg} {info.get('summary') or ''}",
            )


def parse_npm(payload: dict) -> Iterator[Evidence]:
    pkg = payload.get("name") or ""
    author = payload.get("author") or {}
    person = _person(author.get("name") if isinstance(author, dict) else str(author).split("<")[0])
    if not person:
        return
    repo = payload.get("repository") or {}
    repo_url = repo.get("url", "") if isinstance(repo, dict) else str(repo)
    repo_url = repo_url.replace("git+", "").replace(".git", "").replace("git://", "https://")
    links = [u for u in [repo_url, author.get("url") if isinstance(author, dict) else None] if u and u.startswith("http")]
    modified = (payload.get("time") or {}).get("modified", "")[:10] or None
    yield Evidence(
        person_name=person, channel="package",
        title=f"Author of npm package {pkg}",
        url=f"https://www.npmjs.com/package/{pkg}",
        source_key=f"npm:{pkg}:{person.lower()}",
        date=modified, links=links, text=f"{pkg} {payload.get('description') or ''}",
    )


def harvest(cfg: dict, http: Http | None = None) -> Iterator[Evidence]:
    http = http or Http()
    for pkg in cfg.get("pypi", []):
        yield from parse_pypi(http.get_json(f"https://pypi.org/pypi/{pkg}/json"))
    for pkg in cfg.get("npm", []):
        yield from parse_npm(http.get_json(f"https://registry.npmjs.org/{pkg}"))
