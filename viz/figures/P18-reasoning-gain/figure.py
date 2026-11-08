"""P18: how many more backdoors each model catches at its top reasoning setting than at its lowest."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P18",
    "title": "More reasoning adds up to {top:.0f} points, but barely moves Sonnet",
    "section": "results",
    "order": 32,
    "caption": ("Backdoors caught at each model's highest reasoning setting minus its lowest, at a 2% audit "
                "budget. Stronger blue means a bigger gain; the small line is the catch rate before and after."),
    "notes": [
        "The gains are percentage points, not percent: GLM-5.3 goes from {glm_lo:.0f}% to {glm_hi:.0f}% caught.",
        "Sonnet starts at {son_lo:.0f}%, so it has little room to gain. Its small number is a ceiling, not a weakness.",
        "Mistral Large 4 ({mistral:+.1f}) and Gemini Flash-Lite ({gemini:+.1f}) are left out, as in the draft table. "
        "More reasoning made both slightly worse; P03 shows them.",
    ],
}

MODELS = {"glm53": "GLM-5.3", "luna": "GPT-6 Luna", "gptoss": "gpt-oss-120b", "qwen38": "Qwen 3.8",
          "haiku55": "Haiku 5.5", "sonnet55": "Sonnet 5.5"}
LEFT_OUT = ("mistrallarge4", "gemini35lite")
RANK = {"off": 0, "low": 1, "medium": 2, "default": 2, "high": 3, "xhigh": 4, "max": 4}


def gain(at2, model: str) -> dict:
    d = at2[at2.model == model].copy()
    d["rank"] = d.effort.map(RANK)
    d = d.sort_values("rank")
    lo, hi = d.iloc[0], d.iloc[-1]
    return {"model": MODELS.get(model, model), "from_setting": lo.effort, "to_setting": hi.effort,
            "caught_from": lo.safety_exact, "caught_to": hi.safety_exact,
            "gain_points": 100 * (hi.safety_exact - lo.safety_exact)}


def build() -> Figure:
    t = S.run_table()
    at2 = t[t.budget_pct == 2]
    rows = sorted((gain(at2, m) for m in MODELS), key=lambda r: -r["gain_points"])
    top = rows[0]["gain_points"]

    cells = []
    for i, r in enumerate(rows):
        x = r["gain_points"] / top
        # Dark text reads better than white on all but the deepest blue of the scale.
        ink = "@on-strong" if x >= 0.85 else "@on-pale"
        text = (f"{{big|+{r['gain_points']:.1f} points}}\n"
                f"{{small|{100 * r['caught_from']:.0f}% → {100 * r['caught_to']:.0f}%}}")
        cells.append({"col": 0, "row": i, "color": f"@deep:{x:.3f}", "text": text, "ink": ink})

    tab = C.heat_table(["Gain from lowest to highest setting"], [r["model"] for r in rows],
                       cells, left=140, cell_h=60)
    option = tab["option"]
    # A narrow column reads as a table; full width would read as six coloured bars.
    option["grid"].update({"left": "center", "right": None, "width": 300})
    rich = option["series"][0]["label"]["rich"]
    for item, c in zip(option["series"][0]["data"], cells):
        item["label"]["color"] = c["ink"]
        item["label"]["rich"] = {k: {**v, "color": c["ink"]} for k, v in rich.items()}

    by = {r["model"]: r for r in rows}
    left_out = {m: gain(at2, m)["gain_points"] for m in LEFT_OUT}
    return Figure(option=option, height=tab["height"], data=rows,
                  facts={"top": top,
                         "glm_lo": 100 * by["GLM-5.3"]["caught_from"], "glm_hi": 100 * by["GLM-5.3"]["caught_to"],
                         "son_lo": 100 * by["Sonnet 5.5"]["caught_from"],
                         "mistral": left_out["mistrallarge4"], "gemini": left_out["gemini35lite"]})
