"""P12: how suspicious each monitor rated the 51 hardest backdoors, with Opus 5.5 at three efforts."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P12",
    "title": "Opus 5.5 flags {opus_pct:.0f}% of the backdoors the other monitors missed",
    "section": "results",
    "order": 130,
    "caption": ("How many of the {n} hardest backdoors each monitor scored 50 or more out of 100. All five scored "
                "the same code on the same 0 to 100 scale, with comments removed. Opus 5.5 is shown at three "
                "reasoning efforts."),
    "notes": [
        "This is not a catch rate. We never ran Opus on honest code, so we don't know where its 2% cutoff sits. "
        "Running Opus on the honest set would turn this into a real comparison.",
        "Max effort was only piloted on 5 backdoors, so it's left out.",
        "The set was chosen because the other monitors failed on it, so it says nothing about how Opus does on "
        "ordinary backdoors.",
        "The {n} are the {never} that none of our seven 0 to 10 monitors caught, plus {haiku_only} only a 0 to 10 "
        "Haiku run caught. The 20 to 49 band from the earlier version of this chart is in the CSV.",
        "These backdoors are also rated for how incriminating and how harmful they look. Those ratings are "
        "now in results/analysis/hard51-risk-ratings.csv and drawn as M15: none of them is both stealthy "
        "and severe.",
    ],
}

COLS = [("Haiku 5.5 xhigh", "Haiku 5.5 · xhigh", "@s1"), ("Sonnet 5.5", "Sonnet 5.5 · high", "@s0"),
        ("opus_low", "Opus 5.5 · low", "@s6"), ("opus_high", "Opus 5.5 · high", "@s6"),
        ("opus_xhigh", "Opus 5.5 · xhigh", "@s6")]


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    n = len(d)
    bars, data = [], []
    for col, label, color in COLS:
        s = d[col].dropna()
        k = int((s >= 50).sum())
        bars.append({"value": k, "itemStyle": {"color": color},
                     "label": {"formatter": f"{k} of {len(s)}"},
                     "tip": f"<b>{label}</b><br>{k} of {len(s)} scored 50 or more<br>median score {s.median():.0f}"})
        data.append({"monitor": label, "n": len(s), "scored_50_plus": k,
                     "scored_20_49": int(((s >= 20) & (s < 50)).sum()), "under_20": int((s < 20).sum()),
                     "median_score": float(s.median())})
    option = C.base(
        grid={"left": 16, "right": 70, "top": 8, "bottom": 8, "containLabel": True},
        xAxis={"type": "value", "min": 0, "max": n, "show": False},
        yAxis={"type": "category", "data": [c[1] for c in COLS], "inverse": True, "axisLine": {"show": False},
               "axisTick": {"show": False},
               "axisLabel": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500, "margin": 14}},
        series=[{"type": "bar", "data": bars, "barWidth": 22, "showBackground": True,
                 "backgroundStyle": {"color": "@mid", "borderRadius": 6},
                 "itemStyle": {"borderRadius": 6},
                 "label": {"show": True, "position": "right", "distance": 8, "color": "@ink-primary",
                           "fontSize": 13, "fontWeight": 600}}],
    )
    groups = d["group"].value_counts()
    xh = d["opus_xhigh"].dropna()
    return Figure(option=option, height=40 + 46 * len(COLS), data=data, facts={
        "opus_pct": 100 * (xh >= 50).mean(), "n": n,
        "never": int(groups.get("never_caught", 0) + groups.get("caught_at_0to100", 0)),
        "haiku_only": int(groups.get("caught_at_0to10_only", 0))})
