"""M16: how much of each program the backdoor's diff touches, by the model that wrote it."""
import numpy as np

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M16",
    "title": "Most backdoors are rewrites, not small edits",
    "section": "appendix",
    "order": 130,
    "caption": ("One mark per backdoored program: how many lines the diff changes divided by how many "
                "lines the program has. Rows are the model that wrote the backdoor, ordered by median. "
                "The diamond is that model's median and the dashed line is a diff as large as the whole "
                "program."),
    "notes": [
        "{n_big} of {n} diffs are past the line, meaning they touch more lines than the finished program "
        "has. These are restructured solutions rather than a planted bug, which is worth knowing before "
        "reading any result about how subtle these backdoors are.",
        "Sample counts per model are very uneven, from {n_min} to {n_max}. The medians for the smallest "
        "generators rest on a handful of programs and should not be compared with o3-mini's as if they "
        "were equally well measured.",
        "{n_unknown} programs have no recorded generator and sit in the 'unknown' row rather than being "
        "dropped.",
        "A ratio above one does not mean the backdoor itself is large. It means the submitted solution "
        "differs from the reference over more lines than the solution contains, which is what a rewrite "
        "looks like to a line differ.",
        "Ported from the data explorer's track-diff-size view, reading the committed case-features table.",
    ],
    "height": 560,
}


def build() -> Figure:
    c = S.cases().copy()
    c["ratio"] = c.changed_lines / c.code_lines
    order = c.groupby("model").ratio.median().sort_values(ascending=False).index.tolist()
    idx = {m: i for i, m in enumerate(order)}
    rng = np.random.default_rng(7)          # fixed, so a rebuild puts every mark back
    jit = rng.uniform(-0.28, 0.28, len(c))
    pts = [{"value": [round(float(r.ratio), 3), round(idx[r.model] + float(j), 3)],
            "tip": (f"<b>{r.model}</b><br>problem {r.sample_id}"
                    f"<br>{int(r.changed_lines)} changed / {int(r.code_lines)} lines"
                    f"<br>ratio {r.ratio:.2f}")}
           for j, r in zip(jit, c.itertuples())]
    med = [{"value": [round(float(c[c.model == m].ratio.median()), 3), idx[m]],
            "tip": (f"<b>{m}</b><br>median {c[c.model == m].ratio.median():.2f}"
                    f"<br>{int((c.model == m).sum())} programs")}
           for m in order]
    option = C.base(
        grid={"left": 250, "right": 28, "top": 44, "bottom": 56},
        xAxis=C.axis("Lines changed, as a share of the program", type="value", min=0, max=6.6),
        yAxis=C.axis("", type="category", data=order, gap=10, inverse=True,
                     axisLabel={"fontSize": 11}, splitLine={"show": False}),
        legend={"top": 0, "left": 244, "data": ["one backdoor", "median for that model"]},
        series=[
            {"name": "one backdoor", "type": "scatter", "symbolSize": 7, "data": pts,
             "itemStyle": {"color": "@context-strong", "opacity": 0.5}},
            {"name": "median for that model", "type": "scatter", "symbol": "diamond",
             "symbolSize": 15, "data": med,
             "itemStyle": {"color": "@s0", "borderColor": "@ink-surface", "borderWidth": 2},
             "markLine": {"silent": True, "symbol": "none",
                          "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1.5},
                          "label": {"show": False}, "data": [{"xAxis": 1}]}},
        ],
    )
    rows = [{"sample_id": r.sample_id, "model": r.model, "changed_lines": int(r.changed_lines),
             "code_lines": int(r.code_lines), "ratio": round(float(r.ratio), 4)}
            for r in c.itertuples()]
    n_by = c.model.value_counts()
    facts = {"n": len(c), "n_big": int((c.ratio > 1).sum()),
             "n_min": int(n_by.min()), "n_max": int(n_by.max()),
             "n_unknown": int((c.model == "unknown").sum())}
    return Figure(option=option, data=rows, facts=facts)
