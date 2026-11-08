"""P22: does a newer model write backdoors that get past our monitors more often?"""
import pandas as pd

from viz.kit import ROOT, Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P22",
    "title": "Newer models didn't write harder-to-catch backdoors",
    "section": "results",
    "order": 112,
    "caption": ("Each dot is one model that wrote backdoors for this dataset, placed at its public release date. "
                "Up is the share of its backdoors missed by all seven of our monitors at a 2% budget; the bar is "
                "the 95% range and the number is how many it wrote. The dashed line is all of them together."),
    "notes": [
        "The two hardest sets came from mid-2024 models, o1-mini and GPT-4o mini. The newest models in the "
        "dataset, o3-mini and Claude 3.7 Sonnet, sit near or below the overall rate. Rank correlation between "
        "release date and share missed is {rho:+.2f}.",
        "Most groups are small and their ranges overlap. Only o1-mini against o3-mini is clearly separated "
        "(see P11). The dataset stops at early 2025, so this says nothing about today's models.",
        "Release date is first public availability (viz/data/model-release-dates.csv). The dataset used "
        "'-latest' names, which may have pointed at a later snapshot of the same model.",
        "Models wrote backdoors for different problems, so problem difficulty is mixed in with the writer's skill.",
        "The {n_apps} backdoors from the original APPS set have no writer model and are left out. None were "
        "missed by all seven.",
    ],
    "height": 440,
}

DATES = ROOT / "viz" / "data" / "model-release-dates.csv"
NAMES = {
    "openai/o1-mini": "o1-mini", "openai/o3-mini": "o3-mini", "openai/gpt-4o-mini": "GPT-4o mini",
    "openai/gpt-4o": "GPT-4o", "openai/gpt-3.5-turbo": "GPT-3.5 Turbo",
    "anthropic/claude-3-5-haiku-latest": "Claude 3.5 Haiku", "anthropic/claude-3-7-sonnet-latest": "Claude 3.7 Sonnet",
    "anthropic/claude-3-7-sonnet-thinking-latest": "Claude 3.7 Sonnet thinking",
    "google/gemini-2.0-flash": "Gemini 2.0 Flash",
}
# Where each name sits relative to its dot, so neighbours don't collide.
PLACE = {"GPT-4o mini": "left", "Claude 3.5 Haiku": "top", "Gemini 2.0 Flash": "bottom",
         "Claude 3.7 Sonnet": "right", "Claude 3.7 Sonnet thinking": "right", "o3-mini": "bottom"}


def year(day: str) -> float:
    """A date as a decimal year, so the axis can tick on each 1 January."""
    t = pd.Timestamp(day)
    start, end = pd.Timestamp(year=t.year, month=1, day=1), pd.Timestamp(year=t.year + 1, month=1, day=1)
    return round(t.year + (t - start) / (end - start), 4)


def build() -> Figure:
    cf = S.cases()
    dates = pd.read_csv(DATES)
    g = (cf.groupby("model").agg(n=("caught_by", "size"),
                                 missed=("caught_by", lambda s: int((s == 0).sum())))
         .reset_index().merge(dates, on="model", how="inner"))
    g["share"] = g.missed / g.n
    g["lo"], g["hi"] = zip(*[S.wilson(int(k), int(n)) for k, n in zip(g.missed, g.n)])
    g["writer"] = g.model.map(NAMES)
    g = g.sort_values("release_date").reset_index(drop=True)
    overall = float((cf.caught_by == 0).mean())

    dots = [{"value": [year(r.release_date), round(100 * r.share, 2)],
             "label": {"formatter": f"{r.writer} ({r.n})", "position": PLACE.get(r.writer, "right")},
             "tip": (f"<b>{r.writer}</b>, released {r.release_date}<br>{r.missed} of {r.n} missed by all seven"
                     f" ({100 * r.share:.1f}%)<br>95% range {100 * r.lo:.0f}–{100 * r.hi:.0f}%")}
            for r in g.itertuples()]
    option = C.base(
        grid={"left": 58, "right": 30, "top": 20, "bottom": 52},
        xAxis=C.axis("Release date of the backdoor writer", type="value", min=2023, max=2025.75,
                     interval=0.25, splitLine={"show": False},
                     axisLabel={"fontSize": 11,
                                "formatter": "function (v) { return v % 1 === 0 ? String(v) : ''; }"}),
        yAxis=C.axis("Missed by all seven monitors", gap=42, type="value", min=0, max=50,
                     axisLabel={"formatter": "{value}%"}),
        series=[
            {"name": "_range", "type": "custom", "renderItem": C.VBAR, "itemStyle": {"color": "@s7"},
             "data": [[year(r.release_date), round(100 * r.lo, 2), round(100 * r.hi, 2)] for r in g.itertuples()],
             "encode": {"x": 0, "y": [1, 2]}, "z": 1, "silent": True, "tooltip": {"show": False}},
            {"name": "writers", "type": "scatter", "symbolSize": 11, "z": 3, "data": dots,
             "itemStyle": {"color": "@s7", "borderColor": "@ink-surface", "borderWidth": 1.5},
             "label": {"show": True, "color": "@ink-primary", "fontSize": 12, "distance": 8}},
            {"name": "_all", "type": "line", "data": [], "silent": True,
             "markLine": {"silent": True, "symbol": "none",
                          "lineStyle": {"type": "dashed", "color": "@ink-muted", "width": 1.2},
                          "label": {"formatter": f"all backdoors {100 * overall:.0f}%", "position": "insideEndTop",
                                    "color": "@ink-muted", "fontSize": 11},
                          "data": [{"yAxis": round(100 * overall, 2)}]}},
        ],
    )
    # Spearman by hand (ranks, then Pearson): Series.corr's spearman needs scipy, which we don't install.
    rho = float(pd.to_datetime(g.release_date).rank().corr(g.share.rank()))
    rows = g[["writer", "model", "release_date", "n", "missed", "share", "lo", "hi"]]
    return Figure(option=option, data=rows,
                  facts={"rho": rho, "n_apps": int((cf.model == "unknown").sum())})
