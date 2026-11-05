"""Build blog/results-figures/: the core results figures, takeaways and recommendations.

    uv run python blog/results-figures/build.py        # data/*.csv, figures.json, index.html
    node blog/results-figures/render_static.mjs        # static/*.svg and static/*.png

No API calls. Reads results/*-samples.csv, results/analysis/case-features.csv and Marnick's
data page (marnick-data-2/assets/views-data.js).

HEADLINE picks how an audit budget is spent in every figure of ours:
  "exact"    audit a random share of programs tied at the cutoff, so every monitor audits
             exactly the budget (fair, and free to compute). Default.
  "reported" audit only programs strictly above the cutoff, as results/*.csv and the summary
             page do. Ties mean the share actually audited is often below the label.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import metrics as M

HEADLINE = "exact"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MARNICK = ROOT / "marnick-data-2" / "assets" / "views-data.js"

FAMILY_COLOR = {"anthropic": "@s1", "openai": "@s0", "google": "@s2", "zhipu": "@s6", "alibaba": "@s3", "mistral": "@s7"}
MODEL_SYMBOL = {
    "sonnet55": "diamond", "haiku55": "circle", "haiku45": "triangle", "luna": "circle", "gptoss": "triangle",
    "gemini35fl": "circle", "gemini35lite": "triangle", "gemma4": "rect", "gemma3": "diamond",
    "glm53": "circle", "qwen38": "circle", "mistrallarge4": "circle", "ministral14b": "triangle",
    "gemma3_27b": "pin",
}
# GLM-5.3's effort=none run is the max rung in disguise (the provider ignored "none" and reasoned in
# visible text), so it would plot as a duplicate of GLM max. Kept in data/, left off the figures.
EXCLUDE = {"dataset-glm53-effortnone-NOT-AN-ABLATION-tm-n500-strip"}
EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = {"off": "off", "low": "low", "medium": "medium / default", "high": "high", "xhigh": "xhigh / max"}

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"
VAL = "safety_exact" if HEADLINE == "exact" else "safety_reported"
LO = "ci_lo" if HEADLINE == "exact" else "rep_ci_lo"
HI = "ci_hi" if HEADLINE == "exact" else "rep_ci_hi"
BUDGET_WORD = "an exact" if HEADLINE == "exact" else "a requested"

# ECharts callbacks travel as source text and are compiled by the page (and render_static.mjs).
TIP = "function (p) { return (p.data && p.data.tip) ? p.data.tip : p.seriesName; }"
VBAR = ("function (params, api) { var a = api.coord([api.value(0), api.value(1)]);"
        " var b = api.coord([api.value(0), api.value(2)]);"
        " return {type: 'line', shape: {x1: a[0], y1: a[1], x2: b[0], y2: b[1]},"
        " style: {stroke: api.visual('color'), lineWidth: 1.3, opacity: 0.5}, silent: true}; }")
BAND = ("function (params, api) { var p1 = api.coord([api.value(0), api.value(1)]);"
        " var p2 = api.coord([api.value(0), api.value(2)]); var p3 = api.coord([api.value(3), api.value(5)]);"
        " var p4 = api.coord([api.value(3), api.value(4)]);"
        " return {type: 'polygon', shape: {points: [p1, p4, p3, p2]},"
        " style: {fill: api.visual('color'), opacity: 0.16}, silent: true}; }")


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def axis(name: str, gap: int = 32, **kw) -> dict:
    base = {
        "name": name, "nameLocation": "middle", "nameGap": gap,
        "nameTextStyle": {"color": "@ink-secondary", "fontSize": 12},
        "axisLine": {"lineStyle": {"color": "@ink-axis"}}, "axisTick": {"lineStyle": {"color": "@ink-axis"}},
        "axisLabel": {"color": "@ink-secondary"}, "splitLine": {"lineStyle": {"color": "@ink-grid"}},
    }
    base.update(kw)
    return base


def base_option(**kw) -> dict:
    o = {
        "textStyle": {"fontFamily": FONT, "color": "@ink-secondary"},
        "tooltip": {"trigger": "item", "formatter": TIP, "confine": True},
        "animation": False,
    }
    o.update(kw)
    return o


# ---------------------------------------------------------------- data

def compute() -> dict:
    budgets = [0.5, 1, 2, 5]
    table = M.run_table(budgets)
    table = table[~table.run.isin(EXCLUDE)].reset_index(drop=True)
    fine = [0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5, 7.5, 10, 15, 20]
    curves = {}
    for run in (M.SONNET, M.HAIKU_X, "dataset-haiku55-tm-n500-strip"):
        h, a = M.load_scores(run)
        ci = M.boot_ci(h.values, a.values, fine, seed=11)
        curves[run] = [
            {"b": b, "v": M.safety_at(h.values, a.values, b / 100)[HEADLINE],
             "lo": ci[(HEADLINE, b)][0], "hi": ci[(HEADLINE, b)][1]}
            for b in fine
        ]
    diff = M.paired_diff(M.SONNET, M.HAIKU_X, fine)

    cf = pd.read_csv(ROOT / "results" / "analysis" / "case-features.csv")
    cf["sample_id"] = cf["sample_id"].astype(str)
    cf["magic"] = cf["sample_id"].map(magic_numbers())

    disagree = pd.read_csv(ROOT / "results" / "analysis" / "disagreement-sonnet-vs-haiku-xhigh.csv")
    table.to_csv(HERE / "data" / "safety-by-run.csv", index=False)
    diff.to_csv(HERE / "data" / "sonnet-minus-haiku-xhigh.csv", index=False)
    return {"table": table, "curves": curves, "diff": diff, "cases": cf, "disagree": disagree}


def magic_numbers() -> dict:
    """sample_id -> does the backdoor compare against a number of 2+ digits absent from the honest code.

    A crude regex test for 'trigger-shaped' backdoors (if x == 1234). Comments are removed first.
    """
    from inspect_ai.log import read_eval_log
    import glob
    d = ROOT / "logs" / "dataset-haiku55-tm-n500-strip" / "trusted_monitoring"
    att = read_eval_log(glob.glob(str(d / "*attack*.eval"))[0])
    hon = read_eval_log(glob.glob(str(d / "*honest*.eval"))[0])

    def code(s):
        for m in s.messages:
            for tc in (getattr(m, "tool_calls", None) or []):
                if tc.function == "submit":
                    return "\n".join(line.split("#")[0] for line in tc.arguments["code"].splitlines())
        return ""

    A = {str(s.id): code(s) for s in att.samples}
    H = {str(s.id): code(s) for s in hon.samples}
    cmp_num = re.compile(r"(==|!=|<=|>=|<|>|%)\s*(\d{2,})")
    out = {}
    for sid, a in A.items():
        new = {m.group(2) for m in cmp_num.finditer(a)} - set(re.findall(r"\d{2,}", H.get(sid, ""))) - {"10", "100", "1000"}
        out[sid] = bool(new)
    return out


# ---------------------------------------------------------------- our figures

def tip_run(r) -> str:
    cost = f"${r.cost:.5f} per program" if r.cost == r.cost and r.cost is not None else "no cost recorded"
    return (f"<b>{html.escape(r['name'])}</b><br>caught {pct(r[VAL])}% "
            f"[{pct(r[LO])}, {pct(r[HI])}]<br>{cost}<br>"
            f"as reported: {pct(r.safety_reported)}% (audits {r.served_pct:.1f}% of honest)")


LABELS = {
    "Sonnet 5.5 · high (default)": "right", "Sonnet 5.5 · low (thinking off)": "bottom",
    "Haiku 5.5 · xhigh": "top", "Haiku 5.5 · low": "left",
    "GLM-5.3 · max (default)": "right", "GLM-5.3 · low": "bottom", "GPT-6 Luna · xhigh": "left", "GPT-6 Luna · off": "left",
    "Gemma 4 26B-A4B": "top", "Haiku 4.5 · no thinking": "top", "Mistral Large 4 · default": "right",
    "Gemini 3.5 Flash-Lite · off": "bottom", "Gemini 3.5 Flash-Lite · xhigh": "right", "gpt-oss-120b · high": "left",
    "Gemma 3 4B": "right", "Ministral 14B": "right",
}


def frontier_series(t: pd.DataFrame, budget: float) -> list:
    d = t[(t.budget_pct == budget) & t.cost.notna()].copy()
    series = []
    for model, g in d.groupby("model", sort=False):
        g = g.sort_values("cost")
        fam = g.iloc[0].family
        color = FAMILY_COLOR[fam]
        items = []
        for _, r in g.iterrows():
            item = {"value": [r.cost, round(100 * r[VAL], 2)], "tip": tip_run(r)}
            if r["name"] in LABELS:
                item["label"] = {"show": True, "position": LABELS[r["name"]], "formatter": r["name"],
                                 "color": "@ink-primary", "fontSize": 11}
            items.append(item)
        series.append({
            "name": M.MODEL_NAMES[model], "type": "line", "data": items, "symbol": MODEL_SYMBOL[model],
            "symbolSize": 10, "itemStyle": {"color": color}, "lineStyle": {"color": color, "width": 1.5, "opacity": 0.6},
            "z": 3,
        })
        series.append({
            "name": M.MODEL_NAMES[model], "type": "custom", "renderItem": VBAR, "itemStyle": {"color": color},
            "data": [[r.cost, round(100 * r[LO], 2), round(100 * r[HI], 2)] for _, r in g.iterrows()],
            "encode": {"x": 0, "y": [1, 2]}, "z": 2, "silent": True, "tooltip": {"show": False},
        })
    pts = d.sort_values("cost")
    best, front = -1, []
    for _, r in pts.iterrows():
        if r[VAL] > best:
            best = r[VAL]
            front.append([r.cost, round(100 * r[VAL], 2)])
    series.append({
        "name": "Best value (no cheaper monitor does better)", "type": "line", "data": front, "symbol": "none",
        "lineStyle": {"type": "dashed", "color": "@ink-muted", "width": 1.2}, "itemStyle": {"color": "@ink-muted"},
        "z": 1, "tooltip": {"show": False}, "silent": True,
    })
    return series


def fig_frontier(t: pd.DataFrame) -> dict:
    budgets = [0.5, 1, 2, 5]
    frames = [{"series": frontier_series(t, b)} for b in budgets]
    no_cost = sorted(t[(t.budget_pct == 2) & t.cost.isna()]["name"].unique())
    opt = base_option(
        grid={"left": 64, "right": 150, "top": 24, "bottom": 96},
        xAxis=axis("Monitor cost per program, USD at list price (log scale)", type="log", min=0.00005, max=0.05),
        yAxis=axis("Backdoors caught (%)", gap=40, type="value", min=0, max=100),
        legend={"type": "scroll", "bottom": 0, "textStyle": {"color": "@ink-secondary"}, "itemWidth": 14},
        series=frames[2]["series"],
    )
    return {"option": opt, "height": 560, "no_cost": no_cost,
            "dial": {"label": "Audit budget", "kind": "choice", "steps": [f"{b}%" for b in budgets], "initial": 2,
                     "frames": frames}}


def fig_effort(t: pd.DataFrame) -> dict:
    ladder = {"sonnet55": "Sonnet 5.5", "haiku55": "Haiku 5.5", "glm53": "GLM-5.3", "qwen38": "Qwen 3.8 Omni Flash",
              "luna": "GPT-6 Luna", "mistrallarge4": "Mistral Large 4", "gptoss": "gpt-oss-120b",
              "gemini35lite": "Gemini 3.5 Flash-Lite"}
    remap = {"max": "xhigh", "default": "medium"}
    budgets = [1, 2, 5]

    def series_for(b):
        d = t[t.budget_pct == b]
        out = []
        for model, label in ladder.items():
            g = d[d.model == model]
            by = {}
            for _, r in g.iterrows():
                e = remap.get(r.effort, r.effort)
                by[e] = r
            data = []
            for e in EFFORT_ORDER:
                if e in by:
                    r = by[e]
                    data.append({"value": round(100 * r[VAL], 2), "tip": tip_run(r)})
                else:
                    data.append(None)
            fam = d[d.model == model].iloc[0].family
            out.append({
                "name": label, "type": "line", "data": data, "connectNulls": True, "symbolSize": 9,
                "symbol": MODEL_SYMBOL[model], "itemStyle": {"color": FAMILY_COLOR[fam]},
                "lineStyle": {"color": FAMILY_COLOR[fam], "width": 2},
                "endLabel": {"show": True, "formatter": "{a}", "color": "@ink-primary", "fontSize": 11},
            })
        return out

    frames = [{"series": series_for(b)} for b in budgets]
    opt = base_option(
        grid={"left": 64, "right": 150, "top": 24, "bottom": 60},
        xAxis=axis("Reasoning effort setting", type="category", boundaryGap=False,
                   data=[EFFORT_LABEL[e] for e in EFFORT_ORDER], splitLine={"show": False}),
        yAxis=axis("Backdoors caught (%)", gap=40, type="value", min=0, max=100),
        series=frames[1]["series"],
    )
    return {"option": opt, "height": 480,
            "dial": {"label": "Audit budget", "kind": "choice", "steps": [f"{b}%" for b in budgets], "initial": 1,
                     "frames": frames}}


def band_data(points: list, key_lo="lo", key_hi="hi", scale=100) -> list:
    out = []
    for p, q in zip(points, points[1:]):
        out.append([p["b"], round(scale * p[key_lo], 2), round(scale * p[key_hi], 2),
                    q["b"], round(scale * q[key_lo], 2), round(scale * q[key_hi], 2)])
    return out


def fig_sonnet_haiku(curves: dict, diff: pd.DataFrame) -> dict:
    spec = [(M.SONNET, "Sonnet 5.5", "@s1"), (M.HAIKU_X, "Haiku 5.5 · xhigh", "@s0"),
            ("dataset-haiku55-tm-n500-strip", "Haiku 5.5 · default", "@ink-muted")]
    series = []
    for run, name, color in spec:
        pts = curves[run]
        series.append({
            "name": name, "type": "line", "xAxisIndex": 0, "yAxisIndex": 0, "symbolSize": 6,
            "itemStyle": {"color": color}, "lineStyle": {"color": color, "width": 2},
            "data": [{"value": [p["b"], round(100 * p["v"], 2)],
                      "tip": f"<b>{name}</b><br>{p['b']}% budget: {pct(p['v'])}% [{pct(p['lo'])}, {pct(p['hi'])}]"}
                     for p in pts],
        })
        if run != "dataset-haiku55-tm-n500-strip":
            series.append({"name": name, "type": "custom", "renderItem": BAND, "xAxisIndex": 0, "yAxisIndex": 0, "clip": True,
                           "itemStyle": {"color": color}, "data": band_data(pts),
                           "encode": {"x": [0, 3], "y": [1, 2, 4, 5]}, "silent": True, "tooltip": {"show": False}})
    dp = [{"b": r.budget_pct, "v": r["diff"], "lo": r.lo, "hi": r.hi} for _, r in diff.iterrows()]
    series.append({
        "name": "Sonnet minus Haiku xhigh", "type": "line", "xAxisIndex": 1, "yAxisIndex": 1, "symbolSize": 6,
        "itemStyle": {"color": "@s6"}, "lineStyle": {"color": "@s6", "width": 2},
        "data": [{"value": [p["b"], round(100 * p["v"], 2)],
                  "tip": f"<b>Sonnet minus Haiku xhigh</b><br>{p['b']}% budget: {100 * p['v']:+.1f} points "
                         f"[{100 * p['lo']:+.1f}, {100 * p['hi']:+.1f}]"} for p in dp],
        "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": "@ink-muted", "type": "dashed"},
                     "label": {"show": False}, "data": [{"yAxis": 0}]},
    })
    series.append({"name": "Sonnet minus Haiku xhigh", "type": "custom", "renderItem": BAND, "xAxisIndex": 1, "clip": True,
                   "yAxisIndex": 1, "itemStyle": {"color": "@s6"}, "data": band_data(dp),
                   "encode": {"x": [0, 3], "y": [1, 2, 4, 5]}, "silent": True, "tooltip": {"show": False}})
    xa = dict(type="log", min=0.2, max=20)
    opt = base_option(
        grid=[{"left": 64, "right": 24, "top": 40, "height": "46%"},
              {"left": 64, "right": 24, "bottom": 56, "height": "24%"}],
        xAxis=[axis("", **xa, axisLabel={"show": False, "color": "@ink-secondary"}),
               axis("Audit budget, % of honest programs a human checks (log scale)", gridIndex=1, **xa)],
        yAxis=[axis("Caught (%)", gap=40, type="value", min=0, max=100),
               axis("Gap (points)", gap=40, type="value", gridIndex=1, min=-10)],
        legend={"top": 0, "textStyle": {"color": "@ink-secondary"},
                "data": ["Sonnet 5.5", "Haiku 5.5 · xhigh", "Haiku 5.5 · default", "Sonnet minus Haiku xhigh"]},
        series=series,
    )
    return {"option": opt, "height": 600, "dial": None}


def fig_scores(runs: list) -> dict:
    cats = [f"{x / 10:.1f}" for x in range(11)]
    grids, xs, ys, series, titles = [], [], [], [], []
    for i, (run, name) in enumerate(runs):
        h, a = M.load_scores(run)
        s = M.safety_at(h.values, a.values, 0.02)
        left = 6 + i * 50
        grids.append({"left": f"{left + 4}%", "width": "38%", "top": 56, "bottom": 64})
        xs.append(axis("Suspicion score", gridIndex=i, type="category", data=cats, splitLine={"show": False}))
        ys.append(axis("Programs (log scale)" if i == 0 else "", gap=44, gridIndex=i, type="log", min=0.5, max=1000,
                       axisLabel={"color": "@ink-secondary",
                                  "formatter": "function (v) { return v < 1 ? '' : String(v); }"}))
        hc = h.round(1).value_counts()
        ac = a.round(1).value_counts()
        cut = s["cutoff"]
        first_audited = f"{min(cut + 0.1, 1.0):.1f}"
        for mode, counts, color in (("honest", hc, "@s0"), ("backdoored", ac, "@s1")):
            series.append({
                "name": f"{mode} programs", "type": "bar", "xAxisIndex": i, "yAxisIndex": i, "barGap": "10%",
                "itemStyle": {"color": color},
                "data": [{"value": int(counts.get(float(c), 0)) or None,
                          "tip": f"<b>{name}</b><br>{int(counts.get(float(c), 0))} {mode} programs scored {c}"}
                         for c in cats],
                **({"markArea": {"silent": True, "itemStyle": {"color": "@s2", "opacity": 0.08},
                                 "label": {"show": True, "position": "insideTop", "color": "@ink-secondary",
                                           "fontSize": 11,
                                           "formatter": f"audited at a requested 2%\n(really {100 * s['served']:.1f}% of honest)"},
                                 "data": [[{"xAxis": first_audited}, {"xAxis": "1.0"}]]}}
                   if mode == "honest" else {}),
            })
        zero = (h == 0).mean()
        titles.append({"text": name, "subtext": f"{pct(zero, 0)}% of honest programs score exactly 0",
                       "left": f"{left + 23}%", "top": 0, "textAlign": "center",
                       "textStyle": {"color": "@ink-primary", "fontSize": 13},
                       "subtextStyle": {"color": "@ink-secondary", "fontSize": 11}})
    opt = base_option(grid=grids, xAxis=xs, yAxis=ys, series=series, title=titles,
                      legend={"bottom": 0, "textStyle": {"color": "@ink-secondary"},
                              "data": ["honest programs", "backdoored programs"]})
    return {"option": opt, "height": 430, "dial": None}


def fig_hard(cf: pd.DataFrame) -> dict:
    counts = cf.caught_by.value_counts().reindex(range(8), fill_value=0)
    colors = {0: "@s7", 7: "@s2"}
    left = [{"value": int(v), "itemStyle": {"color": colors.get(k, "@s0")},
             "tip": f"{int(v)} backdoors caught by {k} of 7 monitors"} for k, v in counts.items()]
    styles = []
    for flag, label in ((True, "Compares input to a\nnew number (x == 1234)"), (False, "No new number")):
        g = cf[cf.magic == flag]
        miss = int((g.caught_by == 0).sum())
        styles.append({"value": round(100 * miss / len(g), 1), "label": {"show": True, "position": "top",
                       "formatter": f"{miss} of {len(g)}", "color": "@ink-primary"},
                       "itemStyle": {"color": "@s7"},
                       "tip": f"{label.replace(chr(10), ' ')}: {miss} of {len(g)} missed by all 7 monitors"})
    opt = base_option(
        grid=[{"left": 60, "width": "50%", "top": 36, "bottom": 70}, {"right": 20, "width": "28%", "top": 36, "bottom": 70}],
        title=[{"text": "How many monitors catch each backdoor", "left": 60, "top": 0,
                "textStyle": {"color": "@ink-primary", "fontSize": 13}},
               {"text": "Missed by all 7, by backdoor style", "right": 20, "top": 0,
                "textStyle": {"color": "@ink-primary", "fontSize": 13}}],
        xAxis=[axis("Monitors (of 7) that catch it at a 2% budget", type="category", data=[str(k) for k in range(8)],
                    splitLine={"show": False}),
               axis("", gridIndex=1, type="category", data=["Compares input to a\nnew number (x == 1234)", "No new number"],
                    splitLine={"show": False}, axisLabel={"color": "@ink-secondary", "interval": 0, "fontSize": 11})],
        yAxis=[axis("Backdoors", gap=40, type="value"),
               axis("Missed by all 7 (%)", gap=36, gridIndex=1, type="value", min=0, max=20)],
        series=[{"name": "backdoors", "type": "bar", "data": left, "barWidth": "60%",
                 "label": {"show": True, "position": "top", "color": "@ink-primary"}},
                {"name": "style", "type": "bar", "xAxisIndex": 1, "yAxisIndex": 1, "data": styles, "barWidth": "50%"}],
    )
    return {"option": opt, "height": 420, "dial": None}


SHORT_GEN = {"unknown": "original APPS backdoors"}


def fig_generators(cf: pd.DataFrame) -> dict:
    g = cf.groupby("model").agg(n=("caught_by", "size"), miss=("caught_by", lambda s: int((s == 0).sum())),
                                med=("changed_lines", "median")).reset_index()
    g["rate"] = 100 * g.miss / g.n
    g = g.sort_values("rate")
    names = [SHORT_GEN.get(m, m.split("/")[-1].replace("-latest", "")) for m in g.model]
    data = [{"value": round(r.rate, 1), "itemStyle": {"color": "@s7" if r.rate >= 15 else "@s0"},
             "label": {"show": True, "position": "right", "formatter": f"{r.miss} of {r.n}", "color": "@ink-primary"},
             "tip": f"<b>{nm}</b><br>{r.miss} of {r.n} missed by all 7 monitors<br>median {r.med:.0f} lines differ from the reference"}
            for nm, (_, r) in zip(names, g.iterrows())]
    opt = base_option(
        grid={"left": 210, "right": 70, "top": 10, "bottom": 50},
        xAxis=axis("Backdoors missed by all 7 monitors (%)", type="value", min=0, max=35),
        yAxis=axis("", type="category", data=names, splitLine={"show": False}),
        series=[{"name": "missed", "type": "bar", "data": data, "barWidth": "60%"}],
    )
    return {"option": opt, "height": 420, "dial": None, "table": g}


# ---------------------------------------------------------------- Marnick's figures

def marnick_views() -> dict:
    t = MARNICK.read_text()
    j = json.loads(t[len("window.__VIEWS__ = "):].rstrip().rstrip(";"))
    return j["theme"], {v["id"]: v for v in j["views"]}


def from_marnick(v: dict) -> dict:
    opt = dict(v["option"])
    h = opt.pop("__height", 440)
    dial = v.get("dial")
    if dial:
        dial = {"label": dial["label"], "kind": dial.get("kind", "choice"), "steps": dial["steps"],
                "initial": dial.get("initial", 0), "frames": dial["frames"]}
    return {"option": opt, "height": h, "dial": dial, "marnick_text": v["human"], "marnick_mislead": v.get("mislead", "")}


# ---------------------------------------------------------------- page

def main() -> None:
    (HERE / "data").mkdir(exist_ok=True)
    D = compute()
    t, cf, diff = D["table"], D["cases"], D["diff"]
    theme, mv = marnick_views()
    at = lambda run, b=2: t[(t.run == run) & (t.budget_pct == b)].iloc[0]
    run_of = {r["name"]: r.run for _, r in t.drop_duplicates("run").iterrows()}
    R = lambda name, b=2: at(run_of[name], b)

    figs = []
    import prose
    P = prose.Prose(t=t, cf=cf, diff=diff, at=at, R=R, disagree=D["disagree"], headline=HEADLINE)

    fr = fig_frontier(t)
    figs.append({"id": "fig1-cost-vs-safety", **fr, **P.fig1(fr["no_cost"])})
    figs.append({"id": "fig2-reasoning-effort", **fig_effort(t), **P.fig2()})
    figs.append({"id": "fig3-sonnet-vs-haiku", **fig_sonnet_haiku(D["curves"], diff), **P.fig3()})
    figs.append({"id": "fig4-score-pileup",
                 **fig_scores([(M.SONNET, "Sonnet 5.5"), (M.HAIKU_X, "Haiku 5.5 · xhigh")]), **P.fig4()})
    figs.append({"id": "fig5-hard-backdoors", **fig_hard(cf), **P.fig5()})
    gen = fig_generators(cf)
    gen.pop("table")
    figs.append({"id": "fig6-who-wrote-it", **gen, **P.fig6()})
    figs.append({"id": "fig7-comments", **from_marnick(mv["cases-catch-set-upset"]), **P.fig7()})
    for vid in ["b1-requested-vs-served", "e3-width-vs-rows", "geom-score-scale", "cases-honest-recalibration",
                "geom-ensemble-vs-budget", "free-auc-reason-vs-suspicion", "geom-campaign-safety"]:
        figs.append({"id": f"s-{vid}", **from_marnick(mv[vid]), **P.support(vid, mv[vid])})

    (HERE / "figures.json").write_text(json.dumps({"theme": theme, "figures": figs}, ensure_ascii=False))
    (HERE / "index.html").write_text(prose.page(figs, theme, P), encoding="utf-8")
    print(f"wrote {HERE / 'index.html'} with {len(figs)} figures (headline: {HEADLINE})")


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    main()
