"""M21: every backdoor as one dot, change size against how many of seven monitors caught it."""
import zlib

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M21",
    "title": "Edit size separates the never-caught row, and nothing else",
    "section": "results",
    "order": 105,
    "caption": ("One dot per backdoor, all {n:d}. Across is lines changed, up is how many of seven "
                "monitors caught it at a 2% budget, spread vertically so dots do not stack. The bottom "
                "row, caught by nobody, has a median of {m0:d} changed lines against {m7:d} for the "
                "top row."),
    "notes": [
        "The relationship is not a gradient. Median edit size by row runs {med_run}, so only the bottom "
        "row stands apart. Backdoors are close to all or nothing: {n0} are caught by none and {n7} by "
        "all seven, leaving {nmid} split across the six rows in between.",
        "Read as an attacker's guide this says the small edit is the one worth making: {p_small}% of "
        "edits of five lines or fewer got past all seven monitors, against {p_big}% of edits of fifty "
        "lines or more.",
        "The x-axis is capped at {cap:d} lines. {n_over} backdoors change more than that and are drawn "
        "on the cap line, so the right edge is a pile rather than a position.",
        "This row count is the seven-monitor panel at a 2% budget. {n0} backdoors scored no catches "
        "here, while the hard-backdoor set counts {n_hard} as never caught, because that set also asks "
        "the wider 0 to 100 scale monitors, which find eight of these.",
        "Rows are integers and the vertical spread is cosmetic jitter, seeded from the problem id so "
        "it is identical on every rebuild. Height within a row carries no meaning.",
    ],
    "height": 480,
}

CAP = 100
# Red, amber, green: the outcome runs bad to good for the defender, so the status tokens
# carry the meaning directly and every dot is at full strength.
BUCKETS = [("caught by none", "@s7", lambda k: k == 0),
           ("caught by some", "@warning", lambda k: 0 < k < 7),
           ("caught by all seven", "@good", lambda k: k == 7)]


def jitter(sample_id: str, row: int) -> float:
    """A stable offset in [-0.3, 0.3], seeded from the problem id rather than from hash().

    The end rows are offset inward only, so every dot stays inside an axis whose ticks are the
    integers 0 to 7 and nothing is half-clipped against the frame.
    """
    f = (zlib.crc32(str(sample_id).encode()) % 1000) / 1000
    if row == 0:
        return 0.02 + 0.30 * f
    if row == 7:
        return -0.02 - 0.30 * f
    return 0.6 * f - 0.3


def build() -> Figure:
    c = S.cases().copy()
    c["cb"] = c.caught_by.astype(int)
    c["cl"] = c.changed_lines.astype(int)

    rows, series = [], []
    for name, colour, keep in BUCKETS:
        g = c[c.cb.map(keep)]
        series.append({
            "name": name, "type": "scatter", "symbolSize": 7,
            "itemStyle": {"color": colour, "opacity": 0.95,
                          "borderColor": "@ink-surface", "borderWidth": 0.5},
            "data": [{"value": [min(int(r.cl), CAP), r.cb + jitter(r.sample_id, r.cb)],
                      "tip": (f"<b>problem {r.sample_id}</b><br>{int(r.cl)} lines changed"
                              f"<br>caught by {r.cb} of 7 monitors"
                              f"<br>{r.source}, written by {r.model}")}
                     for r in g.itertuples()],
        })
        rows += [{"sample_id": r.sample_id, "changed_lines": int(r.cl), "code_lines": int(r.code_lines),
                  "monitors_caught_of_7": r.cb, "bucket": name, "model": r.model, "source": r.source}
                 for r in g.itertuples()]

    med = {k: int(c[c.cb == k].cl.median()) for k in range(8)}
    small, big = c[c.cl <= 5], c[c.cl >= 50]
    facts = {
        "n": len(c), "m0": med[0], "m7": med[7],
        "med_run": ", ".join(str(med[k]) for k in range(8)),
        "n0": int((c.cb == 0).sum()), "n7": int((c.cb == 7).sum()),
        "nmid": int(((c.cb > 0) & (c.cb < 7)).sum()),
        "p_small": round(100 * (small.cb == 0).mean()), "p_big": round(100 * (big.cb == 0).mean(), 1),
        "cap": CAP, "n_over": int((c.cl > CAP).sum()), "n_hard": 41,
    }
    option = C.base(
        grid={"left": 76, "right": 30, "top": 42, "bottom": 56},
        xAxis=C.axis(f"Lines changed, honest to backdoor (capped at {CAP})", type="value",
                     min=0, max=CAP + 5, interval=20),
        yAxis=C.axis("Monitors that caught it, of seven", gap=52, type="value",
                     min=0, max=7, interval=1),
        legend={"top": 0, "left": 70, "data": [b[0] for b in BUCKETS]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
