"""Papers via OpenAlex (free, no key). Finds authors affiliated with seed institutions."""

from __future__ import annotations

import os
from typing import Iterator

from ..http import Http
from ..models import Evidence

API = "https://api.openalex.org"


def _base_params() -> dict:
    mailto = os.environ.get("OPENALEX_MAILTO")
    return {"mailto": mailto} if mailto else {}


def parse_works(payload: dict, institution_id: str) -> Iterator[Evidence]:
    for w in payload.get("results") or []:
        url = w.get("doi") or w.get("id")
        if not url:
            continue
        venue = ((w.get("primary_location") or {}).get("source") or {}).get("display_name") or ""
        for a in w.get("authorships") or []:
            inst_ids = {i.get("id") for i in a.get("institutions") or []}
            if institution_id not in inst_ids:
                continue
            author = a.get("author") or {}
            name = (author.get("display_name") or "").strip()
            if not name or " " not in name:
                continue
            inst_name = next((i.get("display_name") for i in a.get("institutions") or [] if i.get("id") == institution_id), None)
            yield Evidence(
                person_name=name,
                channel="paper",
                title=f"Author: {w.get('display_name') or w.get('title') or ''} ({venue})".strip(),
                url=url,
                source_key=f"openalex:{author.get('id') or name.lower()}",
                date=(w.get("publication_date") or "")[:10] or None,
                org=inst_name,
                text=" ".join(c.get("display_name", "") for c in w.get("concepts") or [])[:500],
            )


def harvest(cfg: dict, http: Http | None = None) -> Iterator[Evidence]:
    http = http or Http()
    for inst in cfg.get("institutions", []):
        found = http.get_json(f"{API}/institutions", {**_base_params(), "search": inst, "per-page": 1})
        results = found.get("results") or []
        if not results:
            continue
        inst_id = results[0]["id"]
        short_id = inst_id.rsplit("/", 1)[-1]
        for topic in cfg.get("topics", []):
            params = {
                **_base_params(),
                "filter": f"authorships.institutions.id:{short_id},from_publication_date:{cfg.get('since', '2019-01-01')}",
                "search": topic,
                "per-page": int(cfg.get("max_per_query", 50)),
            }
            yield from parse_works(http.get_json(f"{API}/works", params), inst_id)
