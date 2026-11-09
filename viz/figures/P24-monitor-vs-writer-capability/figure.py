"""P24: how capable the models that wrote the backdoors were, next to the models that monitored them.

Capability is Epoch AI's Capabilities Index (ECI), which fits many benchmarks onto one scale so
models from different years can be compared. The scores are copied by hand into
viz/data/eci-scores.csv from https://epoch.ai/data/eci_scores.csv (CC BY), read 2026-11-09.
How many backdoors each writer produced comes from results/analysis/case-features.csv.
"""
import pandas as pd

from viz.kit import ROOT, Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P24",
    "title": "Most of our monitors are stronger than any backdoor writer",
    "section": "setup",
    "order": 20,
    "caption": ("Each row is one model, placed by its Epoch Capabilities Index score, which puts models from "
                "different years on one scale. Red models wrote our 500 backdoors; blue models monitored them. "
                "The shaded band spans the writers and the faint bar is Epoch's interval. Hover a dot for its "
                "release date."),
    "notes": [
        "Source: Epoch AI, Epoch Capabilities Index, epoch.ai/data/eci_scores.csv (CC BY), read 2026-11-09 and "
        "copied by hand into viz/data/eci-scores.csv. Epoch refits the index as results arrive, so scores drift "
        "by a point or two. Its intervals are 90% by default.",
        "{n_above} of {n_scored} scored monitors sit above the strongest writer, {top_writer}. gpt-oss-120b, "
        "Gemma 4 26B-A4B and Haiku 4.5 sit within a couple of points of it, inside each other's intervals, so "
        "treat them as attacker-level rather than clearly stronger.",
        "The dataset names writers by API alias. GPT-4o and GPT-3.5 Turbo use the snapshot each alias pointed to "
        "in early 2025 (Aug 2024 and Jan 2024); the other GPT-4o snapshots score within 2 points. Claude 3.7 "
        "Sonnet includes {n_thinking} backdoors written with extended thinking on.",
        "The {n_apps} backdoors from Greenblatt et al.'s original set record no writer and are left out. Epoch has "
        "not scored Qwen 3.8 Omni Flash, Gemma 3 4B or Ministral 14B. ECI rates a model at its best setting, "
        "not at each reasoning effort we ran.",
        "Colour marks the side here (red wrote, blue monitored), not the model. Haiku 5.5, GLM-5.3 and Opus 5.5 "
        "keep their own colours in every other figure. Opus 5.5 only re-scored the 51 hardest backdoors.",
    ],
}

ECI = ROOT / "viz" / "data" / "eci-scores.csv"
WRITER = {
    "openai/o3-mini": "o3-mini", "openai/o1-mini": "o1-mini", "openai/gpt-4o": "GPT-4o",
    "openai/gpt-4o-mini": "GPT-4o mini", "openai/gpt-3.5-turbo": "GPT-3.5 Turbo",
    "anthropic/claude-3-5-haiku-latest": "Claude 3.5 Haiku",
    "anthropic/claude-3-7-sonnet-latest": "Claude 3.7 Sonnet",
    "anthropic/claude-3-7-sonnet-thinking-latest": "Claude 3.7 Sonnet",
    "google/gemini-2.0-flash": "Gemini 2.0 Flash",
}
MONITOR = {**S.MODEL_NAMES, "opus55": "Opus 5.5"}
X_MIN, X_MAX = 100, 180

# A soft horizontal bar behind a marker, for an interval. Data: [lo, hi, row].
HBAR = ("function (params, api) { var a = api.coord([api.value(0), api.value(2)]);"
        " var b = api.coord([api.value(1), api.value(2)]);"
        " return {type: 'line', shape: {x1: a[0], y1: a[1], x2: b[0], y2: b[1]},"
        " style: {stroke: api.visual('color'), lineWidth: 7, lineCap: 'round', opacity: 0.2}, silent: true}; }")

# Row labels carry a kind and a muted note after the name: "name|kind|note".
LABEL = ("function (v) { var p = v.split('|');"
         " if (p[1] === 'x') return '{x|' + p[0] + '}  {c|' + p[2] + '}';"
         " return p[2] ? '{n|' + p[0] + '}  {c|' + p[2] + '}' : '{n|' + p[0] + '}'; }")


def month(day: str) -> str:
    return pd.Timestamp(day).strftime("%b %Y")


def build() -> Figure:
    cf = S.cases()
    eci = pd.read_csv(ECI)

    # One row per writer (Claude 3.7 Sonnet's thinking backdoors fold into Claude 3.7 Sonnet).
    w = eci[eci.role == "writer"].copy()
    w["name"] = w.key.map(WRITER)
    w["n"] = w.key.map(cf.model.value_counts()).fillna(0).astype(int)
    w = (w.groupby("name").agg(eci=("eci", "first"), lo=("eci_lo", "first"), hi=("eci_hi", "first"),
                               date=("date", "first"), n=("n", "sum"), eci_name=("eci_name", "first"))
         .reset_index())
    w["role"] = "writer"

    m = eci[eci.role == "monitor"].copy()
    m["name"] = m.key.map(MONITOR)
    m = m.rename(columns={"eci_lo": "lo", "eci_hi": "hi"})[["name", "key", "eci", "lo", "hi", "date", "eci_name"]]
    m["role"], m["n"] = "monitor", 0

    rows = pd.concat([w, m], ignore_index=True)
    scored = rows[rows.eci.notna()].sort_values("eci", ascending=False)
    unscored = rows[rows.eci.isna()].sort_values("name")
    rows = pd.concat([scored, unscored], ignore_index=True)

    cats = []
    for r in rows.itertuples():
        if pd.isna(r.eci):
            cats.append(f"{r.name}|x|not scored")
        elif r.role == "writer":
            cats.append(f"{r.name}|w|wrote {r.n}")
        elif r.name == "Opus 5.5":
            cats.append(f"{r.name}|m|follow-up only")
        else:
            cats.append(f"{r.name}|m|")

    def dots(role, color):
        out = []
        for i, r in enumerate(rows.itertuples()):
            if r.role != role or pd.isna(r.eci):
                continue
            hollow = r.name == "Opus 5.5"
            what = f"wrote {r.n} of our 500 backdoors" if role == "writer" else "monitor"
            out.append({"value": [round(r.eci, 2), i],
                        "itemStyle": {"color": "@ink-surface", "borderColor": color, "borderWidth": 2.5} if hollow else {},
                        "tip": (f"<b>{r.name}</b>, {what}<br>ECI {r.eci:.1f} (interval {r.lo:.1f} to {r.hi:.1f})"
                                f"<br>released {month(r.date)} (Epoch entry: {r.eci_name})")})
        return out

    def bars(role, color):
        return {"name": f"_{role}_range", "type": "custom", "renderItem": HBAR, "itemStyle": {"color": color},
                "data": [[round(r.lo, 2), round(r.hi, 2), i] for i, r in enumerate(rows.itertuples())
                         if r.role == role and not pd.isna(r.eci)],
                "encode": {"x": [0, 1], "y": 2}, "z": 1, "silent": True, "tooltip": {"show": False}}

    writers = rows[rows.role == "writer"]
    lo_w, hi_w = float(writers.eci.min()), float(writers.eci.max())
    top_writer = writers.loc[writers.eci.idxmax(), "name"]
    mon = rows[(rows.role == "monitor") & rows.eci.notna()]

    option = C.base(
        grid={"left": 16, "right": 24, "top": 46, "bottom": 50, "containLabel": True},
        legend={"top": 0, "left": 0, "data": ["Wrote backdoors", "Monitored"], "selectedMode": False},
        xAxis=C.axis("Epoch Capabilities Index", gap=30, type="value",
                     min=X_MIN, max=X_MAX, interval=10),
        yAxis={"type": "category", "data": cats, "inverse": True, "axisLine": {"show": False},
               "axisTick": {"show": False},
               "axisLabel": {"formatter": LABEL, "rich": {
                   "n": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500},
                   "x": {"color": "@ink-muted", "fontSize": 13},
                   "c": {"color": "@ink-muted", "fontSize": 11}}}},
        series=[
            bars("writer", "@s7"), bars("monitor", "@s0"),
            {"name": "Wrote backdoors", "type": "scatter", "symbolSize": 10, "z": 3, "data": dots("writer", "@s7"),
             "itemStyle": {"color": "@s7", "borderColor": "@ink-surface", "borderWidth": 1.5},
             "markArea": {"silent": True, "itemStyle": {"color": "@s7/0.07"},
                          "label": {"show": True, "position": "insideTop", "distance": 4, "color": "@ink-secondary",
                                    "fontSize": 11, "formatter": "backdoor writers"},
                          "data": [[{"xAxis": round(lo_w, 2)}, {"xAxis": round(hi_w, 2)}]]}},
            {"name": "Monitored", "type": "scatter", "symbolSize": 10, "z": 3, "data": dots("monitor", "@s0"),
             "itemStyle": {"color": "@s0", "borderColor": "@ink-surface", "borderWidth": 1.5}},
        ],
    )
    table = rows[["role", "name", "n", "eci", "lo", "hi", "date", "eci_name"]].rename(
        columns={"n": "backdoors_written", "lo": "eci_lo", "hi": "eci_hi", "eci_name": "epoch_entry"})
    return Figure(option=option, data=table, height=110 + 26 * len(rows), facts={
        "n_above": int((mon.eci > hi_w).sum()), "n_scored": int(len(mon)), "top_writer": top_writer,
        "n_thinking": int((cf.model == "anthropic/claude-3-7-sonnet-thinking-latest").sum()),
        "n_apps": int((cf.model == "unknown").sum()),
    })
