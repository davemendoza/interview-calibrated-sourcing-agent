"""USPTO patents via the free PatentsView PatentSearch API.

Inventors on payments patents are pre-qualified by their own filed work, and
the filing records the inventor's city.
"""

from __future__ import annotations

import json
import os
from typing import Iterator

from ..http import Http
from ..models import Evidence

FIELDS = [
    "patent_id",
    "patent_title",
    "patent_date",
    "patent_abstract",
    "inventors.inventor_name_first",
    "inventors.inventor_name_last",
    "inventors.inventor_city",
    "inventors.inventor_state",
    "assignees.assignee_organization",
]


def parse_patents(payload: dict) -> Iterator[Evidence]:
    for p in payload.get("patents") or []:
        pid = str(p.get("patent_id") or "").strip()
        if not pid:
            continue
        assignees = [a.get("assignee_organization") for a in p.get("assignees") or [] if a.get("assignee_organization")]
        org = assignees[0] if assignees else None
        for inv in p.get("inventors") or []:
            first = (inv.get("inventor_name_first") or "").strip()
            last = (inv.get("inventor_name_last") or "").strip()
            if not first or not last:
                continue
            city = (inv.get("inventor_city") or "").strip()
            state = (inv.get("inventor_state") or "").strip()
            location = ", ".join(x for x in [city, state] if x) or None
            yield Evidence(
                person_name=f"{first} {last}",
                channel="patent",
                title=f"Inventor, US {pid}: {p.get('patent_title') or ''}".strip(),
                url=f"https://patents.google.com/patent/US{pid}",
                source_key=f"patent-inventor:{first.lower()} {last.lower()}|{city.lower()}",
                date=(p.get("patent_date") or "")[:10] or None,
                org=org,
                location=location,
                text=p.get("patent_abstract") or "",
            )


def harvest(cfg: dict, http: Http | None = None) -> Iterator[Evidence]:
    key = os.environ.get("PATENTSVIEW_API_KEY")
    if not key:
        raise RuntimeError("PATENTSVIEW_API_KEY is not set; get a free key at patentsview.org")
    http = http or Http(min_interval=1.5)  # PatentsView allows 45 requests per minute
    endpoint = cfg.get("endpoint", "https://search.patentsview.org/api/v1/patent/")
    for assignee in cfg.get("assignees", []):
        query = {"_and": [
            {"assignees.assignee_organization": assignee},
            {"_gte": {"patent_date": cfg.get("since", "2021-01-01")}},
        ]}
        params = {
            "q": json.dumps(query),
            "f": json.dumps(FIELDS),
            "o": json.dumps({"size": min(int(cfg.get("max_per_assignee", 300)), 1000)}),
            "s": json.dumps([{"patent_date": "desc"}]),
        }
        payload = http.get_json(endpoint, params, {"X-Api-Key": key})
        yield from parse_patents(payload)
