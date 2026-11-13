"""P08: the cutoffs a monitor can actually use on a 0 to 10 score versus a 0 to 100 score."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P08",
    "title": "A 0 to 100 score gives the monitor more cutoffs to choose from",
    "section": "results",
    "order": 80,
    "caption": ("Each dot is a budget the monitor can hit exactly, without breaking a tie: clean code audited "
                "(across) against backdoors caught (up), for budgets up to {xmax}%. Grey is the default 0 to 10 "
                "prompt, violet the same monitor asked for 0 to 100. More dots means more budgets to choose from."),
    "notes": [
        "This explains the wide intervals in P05 only in part. Those come mostly from how few honest programs sit "
        "above the cutoff (5 at 1%), and a wider scale doesn't add honest programs.",
        "The scale isn't purely cosmetic: Marnick measured it raising AUC by about +14 points for GPT-6 Luna and "
        "+8.5 for Gemma 4, but under a point for Sonnet and Haiku.",
        "MonitoringBench saw 0 to 100 scores collapse at the top (honest code hitting 100). A wider scale helps when "
        "honest scores pile up low, as ours do, and can hurt when they pile up high.",
    ],
    "height": 440,
}

PAIRS = [("Sonnet 5.5", S.SONNET, S.SONNET_100), ("Haiku 5.5 · xhigh", S.HAIKU_X, S.HAIKU_X_100)]
SCALES = [("0 to 10 score", "@context-strong"), ("0 to 100 score", "@s6")]
X_MAX = 5  # % of clean code; budgets above this aren't ones a deployment would use, so they're left off


def build() -> Figure:
    grids, xs, ys, series, graphic, rows, counts = [], [], [], [], [], [], {}
    for i, (name, r10, r100) in enumerate(PAIRS):
        left = 6 + i * 50
        grids.append({"left": f"{left + 3}%", "width": "39%", "top": 40, "bottom": 96})
        xs.append(C.axis("Clean code audited (log scale)", gridIndex=i, type="log", min=0.1, max=X_MAX,
                         axisLabel={"formatter": "{value}%"}))
        ys.append(C.axis("Backdoors caught" if i == 0 else "", gap=40, gridIndex=i, type="value", min=0, max=100,
                         axisLabel={"formatter": "{value}%"}))
        graphic.append({"type": "text", "left": f"{left + 3}%", "top": 12,
                        "style": {"text": name, "fill": "@ink-primary", "fontSize": 13, "fontWeight": 600}})
        for (tag, color), run in zip(SCALES, (r10, r100)):
            pts = [(x, y) for x, y in S.operating_points(run) if x <= X_MAX]
            counts[(name, tag)] = len(pts)
            series.append({
                "name": tag, "type": "line", "step": "end", "xAxisIndex": i, "yAxisIndex": i, "symbolSize": 7,
                "itemStyle": {"color": color}, "lineStyle": {"color": color, "width": 2},
                "data": [{"value": [round(x, 2), round(y, 2)],
                          "tip": f"<b>{name}, {tag}</b><br>audits {x:.1f}% of clean programs<br>catches {y:.1f}% of backdoors"}
                         for x, y in pts],
            })
            rows += [{"monitor": name, "scale": tag, "audit_pct": x, "caught_pct": y} for x, y in pts]
    option = C.base(grid=grids, xAxis=xs, yAxis=ys, series=series, graphic=graphic,
                    legend={"bottom": 8, "left": "center", "itemGap": 28, "data": [s[0] for s in SCALES]})
    return Figure(option=option, data=rows,
                  facts={"xmax": X_MAX, "s10": counts[("Sonnet 5.5", "0 to 10 score")], "s100": counts[("Sonnet 5.5", "0 to 100 score")]})
