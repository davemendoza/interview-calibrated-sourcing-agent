"""Identity gate: never merge on name alone.

Evidence starts grouped by its source account or record (a GitHub login, a
patent inventor in one city, an OpenAlex author id, a speaker entry). Two
groups with the same normalized name merge only when a second independent
signal agrees:

  * employer: the same organization appears in both groups
  * crosslink: one group links to the other's GitHub handle or website
  * email: the same self-published email
  * metro: the same metro area, and no conflicting employer

Same-name groups that cannot be corroborated stay separate and are marked
"review: possible namesake", so a recruiter never inherits someone else's work.
"""

from __future__ import annotations

from collections import defaultdict

from .config import metro_of
from .models import Candidate, Evidence, normalize_name, normalize_org


class _Group:
    def __init__(self, key: str) -> None:
        self.key = key
        self.evidence: list[Evidence] = []

    @property
    def name(self) -> str:
        return self.evidence[0].person_name

    def orgs(self) -> set[str]:
        out = set()
        for e in self.evidence:
            org = normalize_org(e.org)
            if org:
                out.add(org)
        return out

    def handles(self) -> set[str]:
        return {e.handle.lower() for e in self.evidence if e.handle}

    def links(self) -> set[str]:
        return {_clean_link(u) for e in self.evidence for u in e.links if u}

    def emails(self) -> set[str]:
        return {e.email.lower() for e in self.evidence if e.email}

    def metros(self) -> set[str]:
        return {m for e in self.evidence if (m := metro_of(e.location)) and m != "other"}


def _clean_link(url: str) -> str:
    u = url.lower().strip().rstrip("/")
    for prefix in ("https://", "http://", "www."):
        if u.startswith(prefix):
            u = u[len(prefix):]
    return u


def _orgs_match(a: set[str], b: set[str]) -> bool:
    return any(x == y or (len(x) > 3 and len(y) > 3 and (x in y or y in x)) for x in a for y in b)


def corroboration(a: _Group, b: _Group) -> str | None:
    """Return the independent signal that links two same-name groups, or None."""
    a_links, b_links = a.links(), b.links()
    for h in a.handles():
        if f"github.com/{h}" in b_links:
            return "crosslink"
    for h in b.handles():
        if f"github.com/{h}" in a_links:
            return "crosslink"
    if a.handles() & b.handles():
        return "crosslink"
    if a_links & b_links:
        return "crosslink"
    if a.emails() & b.emails():
        return "email"
    a_orgs, b_orgs = a.orgs(), b.orgs()
    if a_orgs and b_orgs and _orgs_match(a_orgs, b_orgs):
        return "employer"
    if a.metros() & b.metros() and not (a_orgs and b_orgs):
        return "metro"
    return None


def resolve(evidence: list[Evidence]) -> list[Candidate]:
    groups: dict[str, _Group] = {}
    for e in evidence:
        groups.setdefault(e.source_key, _Group(e.source_key)).evidence.append(e)

    by_name: dict[str, list[_Group]] = defaultdict(list)
    for g in groups.values():
        norm = normalize_name(g.name)
        if norm:
            by_name[norm].append(g)

    candidates: list[Candidate] = []
    for norm, glist in by_name.items():
        parent = list(range(len(glist)))
        reasons: dict[int, list[str]] = defaultdict(list)

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(len(glist)):
            for j in range(i + 1, len(glist)):
                why = corroboration(glist[i], glist[j])
                if why:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[rj] = ri
                    reasons[find(i)].append(f"{why}: {glist[i].key} + {glist[j].key}")

        clusters: dict[int, list[_Group]] = defaultdict(list)
        for i, g in enumerate(glist):
            clusters[find(i)].append(g)

        namesakes = len(clusters) > 1
        for n, (root, members) in enumerate(clusters.items()):
            ev = [e for g in members for e in g.evidence]
            c = Candidate(key=f"{norm}#{n}" if namesakes else norm, name=members[0].name, evidence=ev)
            if len(members) > 1:
                c.identity_status = "verified"
                c.identity_notes = reasons[root]
            elif namesakes:
                c.identity_status = "review: possible namesake"
                c.identity_notes = [f"{len(clusters)} uncorroborated records share this name"]
            else:
                c.identity_status = "single source"
            candidates.append(c)
    return candidates
