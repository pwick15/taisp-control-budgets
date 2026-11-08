"""M10: the score-scale comparison cut the other way, one panel per monitor with the batch on the dial."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M10",
    "title": "The wider scale buys Haiku more cutoffs than it buys Sonnet",
    "section": "appendix",
    "order": 111,
    "caption": ("The same operating points as the previous figure, cut by monitor instead of by batch. "
                "Each distinct honest score is one cutoff; x is the share of honest programs audited, y the "
                "backdoors caught. The dashed line is a 5% audit share. Use the dial to switch batch."),
    "notes": [
        "Counting cutoffs at or below a 5% audit share, the 0 to 100 prompt takes Haiku from "
        "{hai_b1_010:d} to {hai_b1_0100:d} on the original 500 and from {hai_b2_010:d} to {hai_b2_0100:d} on "
        "batch 2. Sonnet moves from {son_b1_010:d} to {son_b1_0100:d} and from {son_b2_010:d} to "
        "{son_b2_0100:d}.",
        "Sonnet starts with less room to gain: it already catches most backdoors at its first cutoff, so "
        "extra cutoffs change where you can sit on the curve more than what you catch there.",
        "Same data as M09 and M11; three cuts of one comparison, kept so the report can use whichever "
        "reads best in place.",
    ],
    "height": 620,
}

SCALES = [("0-10", "@s0"), ("0-100", "@s1")]
XA = {"type": "log", "min": 0.2, "max": 60, "axisLabel": {"formatter": "{value}%"}}
FIVE = {"silent": True, "symbol": "none", "label": {"show": False},
        "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1},
        "data": [{"xAxis": 5}]}


def series_for(batch: str, rows: list) -> list:
    out = []
    for panel, monitor in enumerate(S.SCALE_MONITORS):
        for scale, color in SCALES:
            run = S.SCALE_RUNS[(monitor, batch)][scale]
            r = S.resolution_curve(run)
            out.append({
                "name": f"{scale} score", "type": "line", "step": "end",
                "xAxisIndex": panel, "yAxisIndex": panel,
                "symbolSize": 8, "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.5},
                "lineStyle": {"color": color, "width": 2},
                "data": [{"value": [round(f, 4), round(c, 2)],
                          "tip": (f"<b>{monitor} · {scale}</b><br>{batch}<br>audit {f:.2f}% of honest"
                                  f"<br>catch {c:.1f}% of backdoors")} for f, c in r["points"]],
                **({"markLine": FIVE} if scale == "0-10" else {}),
            })
            rows += [{"monitor": monitor, "batch": batch, "scale": scale, "run": run,
                      "audit_pct": round(f, 4), "caught_pct": round(c, 2)} for f, c in r["points"]]
    return out


def build() -> Figure:
    rows: list = []
    frames = [{"series": series_for(b, rows)} for b in S.SCALE_BATCHES]
    facts = {}
    for m, mk in zip(S.SCALE_MONITORS, ("son", "hai")):
        for b, bk in zip(S.SCALE_BATCHES, ("b1", "b2")):
            for scale, _ in SCALES:
                facts[f"{mk}_{bk}_{scale.replace('-', '')}"] = \
                    S.resolution_curve(S.SCALE_RUNS[(m, b)][scale])["usable5"]
    option = C.base(
        grid=[{"left": 62, "right": 28, "top": 54, "height": "33%"},
              {"left": 62, "right": 28, "bottom": 62, "height": "33%"}],
        xAxis=[C.axis("", **{**XA, "axisLabel": {"show": False}}),
               C.axis("Share of honest programs audited (log scale)", gridIndex=1, **XA)],
        yAxis=[C.axis("Backdoors caught", gap=46, type="value", min=0, max=100,
                      axisLabel={"formatter": "{value}%"}),
               C.axis("Backdoors caught", gap=46, type="value", gridIndex=1, min=0, max=100,
                      axisLabel={"formatter": "{value}%"})],
        legend={"top": 0, "left": 56, "data": [f"{s} score" for s, _ in SCALES]},
        graphic=[{"type": "text", "left": 62, "top": 34,
                  "style": {"text": S.SCALE_MONITORS[0], "fontSize": 12, "fontWeight": 600,
                            "fill": "@ink-secondary"}},
                 {"type": "text", "left": 62, "top": "55%",
                  "style": {"text": S.SCALE_MONITORS[1], "fontSize": 12, "fontWeight": 600,
                            "fill": "@ink-secondary"}}],
        series=frames[0]["series"],
    )
    return Figure(option=option, data=rows, facts=facts,
                  dial={"label": "Batch", "steps": S.SCALE_BATCHES, "initial": 0, "frames": frames})
