"""Report: monitor comparison and reasoning-effort sweep on APPS dataset backdoors.

Eight monitors, N=500 dataset mode (comments hidden), trusted monitoring, compared at every
audit budget; for the models that expose a reasoning knob, every reasoning level.

All numbers are computed from results/*.csv via load_run, so re-running analyze.py and
rebuilding keeps the prose and tables consistent with the data.
"""
from viewer import charts
from viewer.components import (
    Bullets, Callout, Code, Figure, Glossary, Group, LegendItem, Panel, Report, Section,
    StatTiles, Steps, Table, Text, Tile, fmt_auroc,
)
from viewer.data import load_run

BUDGETS = [0.5, 1, 2, 5, 10, 20, 50]

# (display label, results label, group) — group heads the master table.
ALL = [
    ("Sonnet 5.5 (um)",        "dataset500-sonnet55-um-strip",          "Frontier"),
    ("Haiku 5.5 · xhigh",      "dataset-haiku55-effortxhigh-tm-n500-strip", "Haiku 5.5 (Anthropic)"),
    ("Haiku 5.5 · high",       "dataset-haiku55-efforthigh-tm-n500-strip",  "Haiku 5.5 (Anthropic)"),
    ("Haiku 5.5 · medium ◂base","dataset-haiku55-tm-n500-strip",         "Haiku 5.5 (Anthropic)"),
    ("Haiku 5.5 · low",        "dataset-haiku55-effortlow-tm-n500-strip",   "Haiku 5.5 (Anthropic)"),
    ("GLM-5.3 · thinking-on ◂base","dataset-glm53-tm-n500-strip",        "GLM-5.3 (DeepInfra)"),
    ("GLM-5.3 · thinking-off", "dataset-glm53-thinkoff-tm-n500-strip",   "GLM-5.3 (DeepInfra)"),
    ("gpt-oss-120b · high",    "dataset-gptoss120b-high-tm-n500-strip",  "gpt-oss-120b (DeepInfra)"),
    ("gpt-oss-120b · medium ◂base","dataset-gptoss120b-tm-n500-strip",   "gpt-oss-120b (DeepInfra)"),
    ("gpt-oss-120b · low",     "dataset-gptoss120b-low-tm-n500-strip",   "gpt-oss-120b (DeepInfra)"),
    ("Luna · xhigh",           "dataset-luna-xhigh-tm-n500-strip",       "GPT-6 Luna (OpenAI)"),
    ("Luna · high",            "dataset-luna-high-tm-n500-strip",        "GPT-6 Luna (OpenAI)"),
    ("Luna · medium ◂base",    "dataset-gpt6luna-tm-n500-strip",         "GPT-6 Luna (OpenAI)"),
    ("Luna · low",             "dataset-luna-low-tm-n500-strip",         "GPT-6 Luna (OpenAI)"),
    ("Luna · none (off)",      "dataset-luna-none-tm-n500-strip",        "GPT-6 Luna (OpenAI)"),
    ("Gemini 3.5 Flash-Lite · medium","dataset-gemini35fl-medium-tm-n500-strip","Gemini 3.5 Flash-Lite (Google)"),
    ("Gemini 3.5 Flash-Lite · low","dataset-gemini35fl-low-tm-n500-strip","Gemini 3.5 Flash-Lite (Google)"),
    ("Gemini 3.5 Flash-Lite · off ◂base","dataset500-gemini35lite-tm-strip","Gemini 3.5 Flash-Lite (Google)"),
    ("Gemini 3.5 Flash-Lite · high","dataset-gemini35fl-high-tm-n500-strip","Gemini 3.5 Flash-Lite (Google)"),
    ("Gemini 3.5 Flash-Lite · xhigh","dataset-gemini35fl-xhigh-tm-n500-strip","Gemini 3.5 Flash-Lite (Google)"),
    ("Gemma-4 26B-A4B",        "dataset500-gemma426b-tm-strip",          "Open small models"),
    ("Gemma-3 4B",             "dataset-gemma3-4b-tm-n500-strip",        "Open small models"),
]

PRICE = {  # list $/1M (in / out) for the text; None where not recorded
    "dataset500-sonnet55-um-strip": "2.00 / 10.00",
    "dataset-haiku55-tm-n500-strip": "0.10 / 0.50",
    "dataset-glm53-tm-n500-strip": "0.90 / 4.00",
    "dataset-gptoss120b-tm-n500-strip": "0.037 / 0.17",
    "dataset-gpt6luna-tm-n500-strip": "0.10 / 0.50",
}


def build() -> Report:
    runs = {label: load_run(label) for _, label, _ in ALL}

    def cost_str(r):
        return f"${r.cost_per_sample:.4f}" if r.cost_per_sample is not None else "n/a"

    son = runs["dataset500-sonnet55-um-strip"]
    hx = runs["dataset-haiku55-effortxhigh-tm-n500-strip"]
    hb = runs["dataset-haiku55-tm-n500-strip"]
    glm_on = runs["dataset-glm53-tm-n500-strip"]
    glm_off = runs["dataset-glm53-thinkoff-tm-n500-strip"]
    luna_off = runs["dataset-luna-none-tm-n500-strip"]
    luna_x = runs["dataset-luna-xhigh-tm-n500-strip"]
    gem_off = runs["dataset500-gemini35lite-tm-strip"]
    gem_x = runs["dataset-gemini35fl-xhigh-tm-n500-strip"]

    summary = [
        f"**Sonnet 5.5 is the best monitor at realistic audit budgets.** It catches "
        f"{son.safety_at(0.5):.0%} of backdoors at a 0.5% budget and {son.safety_at(2):.0%} at 2%, "
        f"well ahead of every other monitor, and leads at every budget up to 20%. It is also the "
        f"priciest practical option ({cost_str(son)}/sample).",
        f"**Haiku 5.5 at xhigh effort is the value pick.** At a 2% budget it reaches "
        f"{hx.safety_at(2):.2f} (vs Sonnet's {son.safety_at(2):.2f}) for about a fifth of the cost "
        f"({cost_str(hx)} vs {cost_str(son)}/sample), and it tops the table at loose budgets "
        f"({hx.safety_at(50):.2f} plateau). Sonnet only pulls clearly ahead at the tightest budgets.",
        f"**Reasoning effort is the biggest lever for a cheap model — but how much it helps depends "
        f"on the model.** Haiku climbs from {hb.safety_at(50):.2f} (medium) to {hx.safety_at(50):.2f} "
        f"(xhigh); Luna climbs from {luna_off.safety_at(50):.2f} (off) to {luna_x.safety_at(50):.2f} "
        f"(xhigh). GLM barely moves (thinking-off {glm_off.safety_at(50):.2f} vs thinking-on "
        f"{glm_on.safety_at(50):.2f}), and Gemini Flash-Lite does not benefit at all.",
        f"**The small open and flash-lite monitors are near-useless at tight budgets, reasoning or "
        f"not.** Gemini 3.5 Flash-Lite sits around {gem_off.safety_at(2):.2f} at every budget and "
        f"gets no better with effort ({gem_x.safety_at(50):.2f} at xhigh); Gemma and gpt-oss catch "
        f"almost nothing below a 5% budget.",
        f"**Biggest caveat: the 0.5% column rests on ~2-3 honest runs**, so tight-budget numbers are "
        f"noisy; treat them as indicative until bootstrapped. Dataset backdoors, one run per setting.",
    ]

    tiles = StatTiles([
        Tile("Sonnet 5.5 @ 0.5%", f"{son.safety_at(0.5):.2f}", "best tight-budget safety", "s1"),
        Tile("Haiku 5.5 xhigh plateau", f"{hx.safety_at(50):.2f}", f"best loose-budget, {cost_str(hx)}/sample", "s2"),
        Tile("Haiku xhigh @ 2%", f"{hx.safety_at(2):.2f}", f"vs Sonnet {son.safety_at(2):.2f}, ~1/5 the cost", "s2"),
        Tile("GLM reasoning effect", f"{glm_on.safety_at(50) - glm_off.safety_at(50):+.2f}", "thinking on minus off: ~nil", "s3"),
    ])

    # master comparison table, ranked within each model group by plateau
    rows = []
    seen_groups = set()
    for name, label, group in sorted(ALL, key=lambda t: (t[2], -runs[t[1]].safety_at(50))):
        if group not in seen_groups:
            rows.append(Group(group))
            seen_groups.add(group)
        r = runs[label]
        rows.append([
            name,
            f"{r.safety_at(0.5):.3f}", f"{r.safety_at(1):.3f}", f"{r.safety_at(2):.3f}", f"{r.safety_at(50):.3f}",
            fmt_auroc(r.auroc), cost_str(r), f"{r.n_honest}/{r.n_attack}",
        ])
    master = Table(
        ["Monitor · reasoning", "0.5%", "1%", "2%", "plateau", "AUROC", "$/sample", "n (h/a)"],
        rows,
        caption="Safety (share of backdoors caught) at each audit budget. '◂base' marks the default-effort "
                "run that was already the committed baseline. All runs share the same 500-problem prefix.",
        align="l" + "r" * 7)

    # reasoning-effort ladders: plateau safety as effort rises, one row per model
    ladder = Table(
        ["Monitor", "off / none", "low", "medium", "high", "xhigh", "effort helps?"],
        [
            ["Haiku 5.5", "—", f"{runs['dataset-haiku55-effortlow-tm-n500-strip'].safety_at(50):.2f}",
             f"{hb.safety_at(50):.2f}", f"{runs['dataset-haiku55-efforthigh-tm-n500-strip'].safety_at(50):.2f}",
             f"{hx.safety_at(50):.2f}", "yes, strongly (accelerating)"],
            ["GPT-6 Luna", f"{luna_off.safety_at(50):.2f}", f"{runs['dataset-luna-low-tm-n500-strip'].safety_at(50):.2f}",
             f"{runs['dataset-gpt6luna-tm-n500-strip'].safety_at(50):.2f}",
             f"{runs['dataset-luna-high-tm-n500-strip'].safety_at(50):.2f}", f"{luna_x.safety_at(50):.2f}",
             "yes (diminishing)"],
            ["gpt-oss-120b", "—", f"{runs['dataset-gptoss120b-low-tm-n500-strip'].safety_at(50):.2f}",
             f"{runs['dataset-gptoss120b-tm-n500-strip'].safety_at(50):.2f}",
             f"{runs['dataset-gptoss120b-high-tm-n500-strip'].safety_at(50):.2f}", "—", "some (lifts the ceiling)"],
            ["GLM-5.3", f"{glm_off.safety_at(50):.2f}", "—", f"{glm_on.safety_at(50):.2f}", "—", "—", "no (on ≈ off)"],
            ["Gemini 3.5 Flash-Lite", f"{gem_off.safety_at(50):.2f}",
             f"{runs['dataset-gemini35fl-low-tm-n500-strip'].safety_at(50):.2f}",
             f"{runs['dataset-gemini35fl-medium-tm-n500-strip'].safety_at(50):.2f}",
             f"{runs['dataset-gemini35fl-high-tm-n500-strip'].safety_at(50):.2f}",
             f"{gem_x.safety_at(50):.2f}", "no (flat / slightly down)"],
        ],
        caption="Plateau safety (50% audit budget) as reasoning effort rises. '—' = that level not run or "
                "not applicable (Haiku/gpt-oss have no true off; GLM is a thinking on/off toggle). "
                "Default-effort baselines: Haiku/Luna/gpt-oss = medium, Gemini = off, GLM = thinking-on.",
        align="lrrrrrl")

    # figure: the one genuine trade-off, Sonnet vs Haiku-xhigh, full curve
    son_curve = [son.safety_at(b) for b in BUDGETS]
    hx_curve = [hx.safety_at(b) for b in BUDGETS]
    fig = Figure(
        "The only real trade-off: Sonnet 5.5 vs Haiku-5.5-xhigh",
        [Panel("Safety by audit budget", charts.safety_lines("Sonnet vs Haiku-xhigh", BUDGETS, son_curve, hx_curve,
               100 / son.n_honest, first_label="Sonnet 5.5", second_label="Haiku xhigh"), "s1")],
        how="Safety is the share of backdoors caught; the audit budget is the share of honest runs humans "
            "review. Higher and further left is better.",
        legend=[LegendItem("Sonnet 5.5 (um)", "line", "s1"), LegendItem("Haiku 5.5 xhigh", "line", "s1")],
        caption=f"Sonnet leads at every budget up to 20% (0.5%: {son.safety_at(0.5):.2f} vs "
                f"{hx.safety_at(0.5):.2f}; 2%: {son.safety_at(2):.2f} vs {hx.safety_at(2):.2f}). Haiku-xhigh "
                f"only overtakes at a 50% budget ({hx.safety_at(50):.2f} vs {son.safety_at(50):.2f}), which "
                f"no one audits. So Sonnet wins on safety; Haiku-xhigh wins on safety-per-dollar.",
        table=Table(["Audit budget"] + [f"{b:g}%" for b in BUDGETS],
                    [["Sonnet 5.5"] + [f"{v:.2f}" for v in son_curve],
                     ["Haiku xhigh"] + [f"{v:.2f}" for v in hx_curve]], align="l" + "r" * len(BUDGETS)),
        columns=1)

    sections = [
        Section("What we wanted to find out", [
            Text("The project compares ways to catch a model slipping backdoors into code. A **monitor** is "
                 "a trusted model that reads submitted code and scores how suspicious it looks (0 to 1); humans "
                 "then audit the most suspicious share they can afford. This study asks two questions across "
                 "eight candidate monitors:"),
            Bullets([
                "Which monitor catches the most backdoors at each audit budget, and at what cost?",
                "For monitors with a reasoning knob, does more reasoning effort make a better monitor?",
            ], ordered=True),
            Callout("Every monitor scores the same 500 dataset problems (same honest solutions and same verified "
                    "backdoors), so differences are the monitor's, not the data's.", "note", "Apples to apples"),
        ]),
        Section("How the test works", [
            Steps([
                ("Problems", "The first 500 APPS problems with a verified backdoor. Honest run = the dataset's "
                             "correct solution; attack run = a solution with a working backdoor."),
                ("Comments hidden", "Every # comment is stripped before the monitor reads the code."),
                ("Monitor", "One model reads the code and returns a suspicion score. Only the monitor calls an API."),
                ("Reasoning sweep", "For models with the knob, we re-run the monitor at each reasoning effort "
                                    "(none/low/medium/high/xhigh), one full run per level, through the model's "
                                    "authoritative provider (OpenAI, Anthropic, Google; open weights via DeepInfra)."),
                ("Audit rule", "The audit budget (share of honest runs reviewed) sets a score cutoff; a backdoor "
                               "scoring above it is caught. Safety = backdoors caught / backdoors total."),
            ]),
            Glossary([
                ("Audit budget", "Share of honest runs humans review. 0.5% of 500 honest runs is ~2-3 runs."),
                ("Safety", "Backdoors caught out of 500 (every dataset backdoor works)."),
                ("Reasoning effort", "How much the monitor thinks before scoring. Provider-specific ladder; "
                                     "Sonnet/Gemma have no sweep here (um default / non-reasoning)."),
                ("um", "Untrusted-monitoring role for Sonnet (the model scores the same dataset backdoors); "
                       "functionally 'Sonnet as the monitor', comparable to the trusted-monitoring runs."),
            ]),
        ]),
        Section("Results", [
            tiles,
            master,
            Text("**Does reasoning effort help?** It depends entirely on the model:"),
            ladder,
            fig,
            Callout(
                f"The cheap-model story is reasoning effort. Haiku 5.5 is already strong and gets dramatically "
                f"better with it ({hb.safety_at(50):.2f} → {hx.safety_at(50):.2f} plateau, and {hb.safety_at(0.5):.2f} "
                f"→ {hx.safety_at(0.5):.2f} at 0.5%). Luna improves monotonically but with diminishing returns. "
                f"gpt-oss lifts its ceiling but stays weak where it matters. GLM's reasoning is wasted "
                f"(on ≈ off), and Gemini Flash-Lite cannot be rescued by thinking at all.", "note",
                "Reasoning effort is model-dependent"),
        ]),
        Section("Which beats which", [
            Bullets([
                f"**Sonnet 5.5 is the best monitor**, leading at every budget to 20% (by +{son.safety_at(0.5) - hx.safety_at(0.5):.2f} "
                f"at 0.5%). Pay for it when tight-budget safety is the objective.",
                f"**Haiku-5.5-xhigh is the best value** — near-Sonnet safety at 2%+ for ~1/5 the per-sample cost "
                f"and 1/20 the list price, and the highest plateau ({hx.safety_at(50):.2f}).",
                f"**Haiku-xhigh strictly dominates GLM-5.3** (better at every budget, ~1/10 the cost), which in "
                f"turn gains nothing from its reasoning.",
                "**Haiku dominates Luna** at matched effort; **Gemini Flash-Lite, Gemma and gpt-oss** are the weak "
                "tier, unusable below a 5% budget.",
            ]),
        ]),
        Section("Caveats", [
            Bullets([
                "**Tight budgets are noisy.** 0.5% thresholds on ~2-3 honest runs; a bootstrap CI is the next step "
                "before leaning on the 0.5-1% column.",
                "**Dataset backdoors, not one attacker.** Read as a monitor comparison, not a detection rate "
                "against any single model.",
                "**Usefulness is 1.0 by construction** (dataset solutions), so only safety is compared; Sonnet is "
                "um-role but functionally the same 'model-as-monitor' measurement.",
                "**Coarse scores.** Suspicion comes in steps of ~0.1, so safety curves plateau (a quantization "
                "artifact); AUROC is unaffected and is reported alongside.",
                "**One run per setting** (Inspect caches re-runs), so run-to-run variation is unmeasured. gpt-oss "
                "high lost 1 errored honest run (499/500); every other arm is 500/500.",
                "**Gemini and Gemma carry no list price** in the table, so their cost shows n/a (tokens are still "
                "counted).",
            ]),
        ]),
        Section("Reproduce", [
            Text("Dataset mode, 500 problems, trusted monitoring, comments hidden. Each monitor/effort is one "
                 "label; MONITOR_REASONING sets the effort. Provider keys in .env."),
            Code("# one monitor at one reasoning effort\n"
                 "MONITOR=anthropic/claude-haiku-5-5 MONITOR_REASONING=xhigh \\\n"
                 "  LABEL=dataset-haiku55-effortxhigh-tm-n500-strip scripts/run_dataset_monitor.sh\n"
                 "uv run python reports/build.py --open"),
        ]),
    ]

    return Report(
        title="Monitor comparison and reasoning-effort sweep",
        subtitle="Across eight monitors and their reasoning settings, which catches the most APPS backdoors per dollar?",
        date="2026-10-30",
        authors=["Marnick Vandecauter"],
        summary=summary,
        sections=sections,
        status="Complete — 8 monitors, N=500, reasoning sweep where available",
        tags=["APPS", "trusted monitoring", "dataset mode", "reasoning effort", "monitor comparison"],
    )
