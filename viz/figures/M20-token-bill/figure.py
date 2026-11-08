"""M20: what a monitor run's token bill is made of, priced per million samples."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M20",
    "title": "Hidden reasoning you never read is most of some bills",
    "section": "appendix",
    "order": 136,
    "caption": ("The {n_shown} most expensive runs, priced per million samples at the same rates "
                "src/analyze.py uses. Each bar splits into what you pay for: fresh input, cache writes, "
                "cache reads, the output you can read, and the reasoning you cannot."),
    "notes": [
        "Hidden reasoning reaches {max_share}% of one run's bill. It never reaches the caller: the "
        "monitor returns a score and a sentence, and the rest is thinking you paid for and cannot read.",
        "The clearest pair is GLM-5.3. Its default and its effort=none arm cost within a couple of "
        "percent of each other, but one books {glm_max}% of that as hidden reasoning and the other {glm_none}%. "
        "The thinking did not stop, it moved into the visible channel, which is what GLM-THINKING-TOGGLE.md "
        "argues from the token counts.",
        "Data quality: this is drawn from eval logs, which are gitignored, so it reads a committed CSV "
        "derived by viz/data/derive_token_bill.py. Rerun that script when a run is added or its usage "
        "recovered, or these bars go stale without the check noticing.",
        "Only the {n_shown} dearest of {n_total} priced runs are drawn, to keep the labels readable. The "
        "CSV button carries all {n_total}, and the n=100 pilots are left out because their three runs "
        "share one recorded generation pass and so report an identical bill.",
        "Ministral 8B has no price in the table, so it has no bar. That absence is deliberate and "
        "src/analyze.py explains it.",
    ],
    "height": 580,
}

PARTS = [("usd_input", "fresh input", "@seq:0.25"), ("usd_cache_write", "cache write", "@seq:0.45"),
         ("usd_cache_read", "cache read", "@seq:0.68"),
         ("usd_visible_output", "output you read", "@s2"),
         ("usd_hidden_reasoning", "hidden reasoning", "@s1")]
SHOW = 14


def build() -> Figure:
    d = pd.read_csv("viz/data/token-bill.csv")
    d = d[d.n_samples >= 1000].copy()            # the n=100 pilots share one generation pass
    d["total"] = d[[c for c, _, _ in PARTS]].sum(axis=1)
    d["label"] = [S.run_label(r) for r in d.run]
    top = d.sort_values("total", ascending=False).head(SHOW).sort_values("total")
    series = [{
        "name": name, "type": "bar", "stack": "bill", "barWidth": "62%",
        "itemStyle": {"color": color},
        "data": [{"value": round(float(r[col]), 2),
                  "tip": (f"<b>{r.label}</b><br>{name}: ${r[col]:,.0f}"
                          f"<br>{100 * r[col] / r.total:.0f}% of ${r.total:,.0f}")}
                 for _, r in top.iterrows()],
    } for col, name, color in PARTS]
    glm_max = d[d.run == "dataset-glm53-tm-n500-strip"]
    glm_none = d[d.run.str.contains("glm53-effortnone")]
    facts = {
        "n_shown": len(top), "n_total": len(d),
        "max_share": round(100 * float((d.usd_hidden_reasoning / d.total).max())),
        "glm_max": round(100 * float(glm_max.usd_hidden_reasoning.iloc[0] / glm_max.total.iloc[0])),
        "glm_none": round(100 * float(glm_none.usd_hidden_reasoning.iloc[0] / glm_none.total.iloc[0])),
    }
    option = C.base(
        grid={"left": 230, "right": 40, "top": 40, "bottom": 56},
        xAxis=C.axis("US dollars per million samples", type="value"),
        yAxis=C.axis("", type="category", data=list(top.label), gap=10,
                     axisLabel={"fontSize": 11}, splitLine={"show": False}),
        legend={"top": 0, "left": 224, "data": [n for _, n, _ in PARTS]},
        series=series,
    )
    rows = [{"run": r.run, "monitor": r.label, "model": r.model,
             **{c: float(r[c]) for c, _, _ in PARTS}, "usd_total": round(float(r.total), 2)}
            for _, r in d.sort_values("total", ascending=False).iterrows()]
    return Figure(option=option, data=rows, facts=facts)
