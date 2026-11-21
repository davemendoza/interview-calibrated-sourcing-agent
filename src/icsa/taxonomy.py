"""Crawl for language before crawling for people.

`icsa taxonomy` reads the ecosystem's taxonomy pages (rule books, standards,
engineering blogs, job postings) and suggests recurring phrases that the role
file's terms do not cover yet. A person reviews the list and copies the useful
ones into the domain requirement. Nothing is added automatically.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

STOP = set("""
a about above after again all also an and any are as at be because been before being below between both but by can
could did do does doing down during each few for from further had has have having here how if in into is it its
just more most no nor not now of off on once only or other our out over own same she should so some such than that
the their them then there these they this those through to too under until up very was we were what when where
which while who whom why will with would you your new our us may must per via use used using one two three get
learn more read click see page home contact privacy policy terms cookies menu search sign login subscribe news
events blog resources support company careers about team inc llc all rights reserved copyright
""".split())


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z][a-z0-9\-]{2,}", text.lower())


def suggest_terms(texts: dict[str, str], existing_terms: list[str], top: int = 40) -> list[tuple[str, int, list[str]]]:
    """Return (phrase, count, urls) for recurring 1 to 3 word phrases not already covered."""
    existing = [t.strip().lower() for t in existing_terms if t.strip()]
    counts: Counter = Counter()
    where: dict[str, set] = defaultdict(set)
    for url, text in texts.items():
        toks = _tokens(text)
        for n in (1, 2, 3):
            for i in range(len(toks) - n + 1):
                gram = toks[i:i + n]
                if gram[0] in STOP or gram[-1] in STOP or all(g in STOP for g in gram):
                    continue
                phrase = " ".join(gram)
                counts[phrase] += 1
                where[phrase].add(url)

    def covered(p: str) -> bool:
        return any(t in p or p in t for t in existing)

    ranked = sorted(
        ((p, c) for p, c in counts.items() if c >= 2 and not covered(p)),
        key=lambda pc: (-(pc[1] * len(pc[0].split())), pc[0]),
    )
    out, seen = [], []
    for p, c in ranked:
        if any(p in s for s in seen):  # skip fragments of a longer phrase already listed
            continue
        seen.append(p)
        out.append((p, c, sorted(where[p])))
        if len(out) >= top:
            break
    return out


def role_terms(role: dict) -> list[str]:
    return [t for r in role.get("requirements", []) for t in r.get("terms", [])] + \
           [t for s in role.get("interview_signals", []) for t in s.get("terms", [])]
