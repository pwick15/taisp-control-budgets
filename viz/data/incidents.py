"""The rogue AI incident log, read from the A01 page so the page and the figures share one copy.

The log lives as JSON inside viz/figures/A01-rogue-ai-incidents/figure.html
(<script type="application/json" id="dash-data">). To add or correct an incident, edit it there,
then run `uv run python -m viz build A01 A02 A03 A05`: the page and every figure drawn from it update.
The calculations below match the page's own (dash.calc 'lag', 'loss' and the timeline's stack()).

It sits in viz/data rather than viz/lib because every figure's code hash covers viz/lib, so a module
there would mark all figures stale; only the A figures use this one.
"""
from __future__ import annotations

import json
import re
from datetime import date

from viz.kit import core

PAGE = core.FIGURES / "A01-rogue-ai-incidents" / "figure.html"
LAB = "Labs and evaluators"
LANES = ["Labs and evaluators", "Companies in production", "Individual developers and users"]
LANE_SHORT = ["Labs and evaluators", "Companies", "Individuals"]
FIRST_MONTH, LAST_MONTH = (2025, 6), (2026, 11)


@core.memo
def log() -> dict:
    text = PAGE.read_text(encoding="utf-8")
    m = re.search(r'<script type="application/json" id="dash-data">(.*?)</script>', text, re.S)
    if not m:
        raise core.BuildError(f"{PAGE} has no dash-data block")
    return json.loads(m.group(1))


def incidents() -> list[dict]:
    return log()["incidents"]


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def lag() -> list[dict]:
    """Lab incidents with a usable date: days from the incident to the first public report, longest first."""
    rows = [{"id": r["id"], "short": r["short"], "when": r["when"], "approx": r["occ_precision"] == "month",
             "days": _days(r["occurred"], r["public"])}
            for r in incidents() if r.get("lag_ok") is True]
    return sorted(rows, key=lambda r: (-r["days"], r["short"]))


def loss() -> list[dict]:
    """First-person reports that state a size of data lost, largest first."""
    rows = [{"id": r["id"], "short": r["short"], "actor": r["actor"], "when": r["when"], "gb": float(r["gb"]),
             "recovery": r.get("recovery")}
            for r in incidents() if r.get("gb") and float(r["gb"]) > 0]
    return sorted(rows, key=lambda r: -r["gb"])


def months() -> list[str]:
    out, (y, m) = [], FIRST_MONTH
    while (y, m) <= LAST_MONTH:
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def stack(key: str) -> dict[str, tuple[int, int, int]]:
    """Each incident's (lane, month index, height in its stack) when dated by `key` ('occurred' or 'public')."""
    ms, counts, pos = months(), {}, {}
    for r in sorted((r for r in incidents() if r.get(key)), key=lambda r: (r[key], r["id"])):
        mi = ms.index(r[key][:7]) if r[key][:7] in ms else -1
        li = LANES.index(r["lane"]) if r["lane"] in LANES else -1
        if mi < 0 or li < 0:
            continue
        k = counts.get((li, mi), 0)
        counts[(li, mi)] = k + 1
        pos[r["id"]] = (li, mi, k)
    return pos
