"""A01: the interactive rogue AI incident log (custom HTML page).

The page holds the incident data that A02, A03 and A05 also draw from (see viz/data/incidents.py).
"""
from viz.kit import Figure
from viz.data import incidents as I

META = {
    "id": "A01",
    "kind": "html",
    "title": "{n} rogue AI incidents, from frontier labs to personal laptops",
    "section": "intro",
    "order": 90,
    "caption": ("The full incident log as an interactive page: a timeline of when each incident happened and "
                "became public, disclosure delays, reported data loss and the missing control behind each one."),
    "notes": [
        "To add or correct an incident, edit the dash-data JSON inside figure.html, then rebuild A01, A02, A03 and A05.",
        "Sizes of data lost are the reporters' own and unverified.",
    ],
    "height": 1100,
}


def build() -> Figure:
    rows = I.incidents()
    data = [{k: r.get(k) for k in ("id", "short", "when", "occurred", "public", "lane", "actor", "evidence",
                                   "surfaced_by", "gap", "gb", "source_name", "source_url")} for r in rows]
    return Figure(data=data, facts={"n": len(rows)})
