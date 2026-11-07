"""P09: how many monitors catch each backdoor, and which backdoors get past all of them."""
import pandas as pd

from viz.kit import ROOT, Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P09",
    "title": "Monitors catch trigger-shaped backdoors and miss bug-shaped ones",
    "section": "results",
    "order": 90,
    "caption": ("Left: how many of seven monitors catch each of the 500 backdoors at a 2% budget, as reported. "
                "Right: the share missed by all seven, split by whether the backdoor compares the input to a "
                "number its honest twin never uses (if x == 1234). A regex finds these, so the split is approximate."),
    "notes": [
        "The web/ summary page says the hard cases are mostly one-token edits. That's not right: most of them change "
        "several lines. What they share is how they look, not how big they are (see P10).",
        "Our 85 to 88% is a statement about this dataset's attacks, most of them clumsy. An attacker who writes "
        "bug-shaped backdoors on purpose would face a much weaker monitor.",
        "Is a bug-shaped backdoor detectable from the code alone? A flipped >= looks the same planted or slipped. If "
        "not, the defence for this class is testing, not a better monitor.",
        "Three of the seven monitors are Haiku at different efforts, so hard for everyone is partly circular. "
        "A monitor from another family (or Opus, P12) is the check.",
    ],
    "height": 420,
}

MAGIC = ROOT / "viz" / "data" / "magic-numbers.csv"


def build() -> Figure:
    cf = S.cases()
    magic = pd.read_csv(MAGIC, dtype={"sample_id": str})
    cf = cf.merge(magic, on="sample_id", how="left")
    counts = cf.caught_by.value_counts().reindex(range(8), fill_value=0)
    color = lambda k: "@s7" if k == 0 else "@context" if k == 7 else "@warning/0.6"
    left = [{"value": int(v), "itemStyle": {"color": color(k), "borderRadius": [4, 4, 0, 0]},
             "tip": f"{int(v)} backdoors caught by {k} of 7 monitors"} for k, v in counts.items()]
    styles, rows = [], [{"group": f"caught by {k} of 7", "backdoors": int(v)} for k, v in counts.items()]
    for flag, label in ((1, "Compares input to\na new number"), (0, "No new number")):
        g = cf[cf.magic_number == flag]
        miss = int((g.caught_by == 0).sum())
        styles.append({"value": round(100 * miss / len(g), 1), "itemStyle": {"color": "@s7", "borderRadius": [4, 4, 0, 0]},
                       "label": {"show": True, "position": "top", "formatter": f"{miss} of {len(g)}",
                                 "color": "@ink-secondary", "fontSize": 12},
                       "tip": f"{label.replace(chr(10), ' ')}: {miss} of {len(g)} missed by all 7"})
        rows.append({"group": label.replace("\n", " "), "backdoors": len(g), "missed_by_all": miss})
    option = C.base(
        grid=[{"left": 56, "width": "52%", "top": 44, "bottom": 64}, {"right": 16, "width": "28%", "top": 44, "bottom": 64}],
        graphic=[{"type": "text", "left": 56, "top": 8, "style": {"text": "Monitors (of 7) catching each backdoor",
                                                                    "fill": "@ink-primary", "fontSize": 13, "fontWeight": 600}},
                 {"type": "text", "right": 16, "top": 8, "style": {"text": "Missed by all 7, by style",
                                                                     "fill": "@ink-primary", "fontSize": 13, "fontWeight": 600,
                                                                     "align": "right"}}],
        xAxis=[C.axis("Monitors that catch it at a 2% budget", type="category", data=[str(k) for k in range(8)]),
               C.axis("", gridIndex=1, type="category", data=["Compares input to\na new number", "No new number"],
                      axisLabel={"interval": 0, "fontSize": 11, "lineHeight": 14})],
        yAxis=[C.axis("Backdoors", gap=40, type="value"),
               C.axis("Missed by all 7", gap=36, gridIndex=1, type="value", min=0, max=20, axisLabel={"formatter": "{value}%"})],
        series=[{"name": "backdoors", "type": "bar", "data": left, "barWidth": "62%",
                 "label": {"show": True, "position": "top", "color": "@ink-secondary", "fontSize": 12}},
                {"name": "style", "type": "bar", "xAxisIndex": 1, "yAxisIndex": 1, "data": styles, "barWidth": "46%"}],
    )
    return Figure(option=option, data=rows)
