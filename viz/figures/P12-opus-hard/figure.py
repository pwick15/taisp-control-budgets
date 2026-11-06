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
    "caption": ("The {n} hardest backdoors: {never} that none of our seven 0 to 10 monitors caught, plus {haiku_only} "
                "only a 0 to 10 Haiku run caught. Every monitor here scores 0 to 100 with comments stripped. Bars "
                "split the {n} by how suspicious each monitor rated them; the right column is the 95% range for 50+."),
    "notes": [
        "This is not a catch rate. We never ran Opus on honest code, so we don't know where its 2% cutoff sits. "
        "Running Opus on the honest set would turn this into a real comparison.",
        "Max effort was only piloted on 5 backdoors, so it's left out.",
        "The set was chosen because the other monitors failed on it, so it says nothing about how Opus does on "
        "ordinary backdoors.",
        "Marnick also rated these backdoors for how incriminating and how harmful they look. Those ratings aren't "
        "in the repo yet; ask him for the CSV.",
    ],
}

COLS = [("Haiku 5.5 xhigh", "Haiku 5.5 · xhigh"), ("Sonnet 5.5", "Sonnet 5.5 · high"),
        ("opus_low", "Opus 5.5 · low"), ("opus_high", "Opus 5.5 · high"), ("opus_xhigh", "Opus 5.5 · xhigh")]
PARTS = [("Scored 50 or more", "@s2", "@on-bright"), ("20 to 49", "@warning/0.6", "@on-bright"),
         ("Under 20 (looks honest)", "@context", "@on-pale")]


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    rows, data = [], []
    for col, label in COLS:
        s = d[col].dropna()
        c = [int((s >= 50).sum()), int(((s >= 20) & (s < 50)).sum()), int((s < 20).sum())]
        rows.append((label, len(s), c))
        data.append({"monitor": label, "n": len(s), "scored_50_plus": c[0], "scored_20_49": c[1], "under_20": c[2],
                     "median_score": float(s.median())})
    groups = d["group"].value_counts() if "group" in d else pd.Series(dtype=int)
    option = C.partition_bars(rows, PARTS, f"Share of the {len(d)} hardest backdoors", "Scored 50+, 95% range")
    xh = d["opus_xhigh"].dropna()
    return Figure(option=option, height=110 + 40 * len(rows), data=data, facts={
        "opus_pct": 100 * (xh >= 50).mean(), "n": len(d),
        "never": int(groups.get("never_caught", 0) + groups.get("caught_at_0to100", 0)),
        "haiku_only": int(groups.get("caught_at_0to10_only", 0))})
