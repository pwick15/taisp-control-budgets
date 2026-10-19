"""Report: untrusted monitor baseline (Haiku vs Sonnet vs Luna, comments kept and hidden).

Numbers in the text and tables are computed from results/*.csv, so re-running
src/analyze.py and rebuilding keeps the page consistent.
"""
from viewer import charts
from viewer.components import (
    Bullets, Callout, Code, Figure, Glossary, Group, Journey, LegendItem, Panel, Report, Section,
    Stage, StatTiles, Steps, Table, Text, Tile, fmt_auroc,
)
from viewer.data import load_run

# key in the results file names, display name, model id, colour slot, role
MONITORS = [
    ("haiku45-tm", "Haiku 4.5", "anthropic/claude-haiku-4-5-20251001", "s1", "Trusted, weak"),
    ("sonnet55-um", "Sonnet 5.5", "anthropic/claude-sonnet-5-5", "s2", "Untrusted, strong"),
    ("gpt6luna-tm", "GPT-6 Luna", "openai/gpt-6-luna", "s3", "Trusted, weak, other provider"),
]
PRICES = {"s1": "$1 / $5", "s2": "$2 / $10", "s3": "$0.10 / $0.50"}  # per 1M tokens, input / output
BINS = [round(i / 10, 1) for i in range(11)]


def build() -> Report:
    raw = {k: load_run(f"dataset-{k}-n30") for k, *_ in MONITORS}
    strip = {k: load_run(f"dataset-{k}-n30-strip") for k, *_ in MONITORS}
    name = {k: n for k, n, *_ in MONITORS}
    haiku, sonnet, luna = (m[0] for m in MONITORS)
    n = raw[haiku].n_honest
    budgets = sorted(raw[haiku].safety_by_budget)
    unreliable_below = 100 / n  # budgets under this threshold on less than one whole honest run

    cost_ratio_haiku = raw[sonnet].cost_per_sample / raw[haiku].cost_per_sample
    cost_ratio_luna = raw[sonnet].cost_per_sample / raw[luna].cost_per_sample
    drops = [raw[k].auroc - strip[k].auroc for k in raw]

    summary = [
        f"**Sonnet 5.5 is the best monitor.** It separated honest from backdoored solutions almost "
        f"perfectly (AUROC {fmt_auroc(raw[sonnet].auroc)}), ahead of Haiku 4.5 "
        f"({fmt_auroc(raw[haiku].auroc)}) and GPT-6 Luna ({fmt_auroc(raw[luna].auroc)}).",
        f"**Hiding code comments hurt every monitor.** AUROC fell by {min(drops):.2f} to {max(drops):.2f}. "
        f"Part of what monitors catch is the comments an attacker leaves, not the backdoor itself. "
        f"Sonnet still led afterwards ({fmt_auroc(strip[sonnet].auroc)}).",
        f"**The weaker monitors fail in different ways.** Haiku raised {raw[haiku].honest_false_alarms} false alarms "
        f"on {n} honest solutions. Luna raised none, but gave {raw[luna].attacks_missed} of {raw[luna].n_attack} "
        f"backdoors a score of 0.",
        f"**This is the best case for untrusted monitoring.** The monitor and the attacker never coordinate here, "
        f"so treat Sonnet's numbers as an upper bound. With {n} + {n} samples, small gaps are noise.",
    ]

    tiles = StatTiles([
        Tile(f"{nm} ({role.split(',')[0].lower()})",
             f"{fmt_auroc(raw[k].auroc)} → {fmt_auroc(strip[k].auroc)}",
             "AUROC, comments kept → comments hidden", slot)
        for k, nm, _, slot, role in MONITORS
    ])

    # ---- results table ----
    def row(k, run):
        return [name[k], fmt_auroc(run.auroc), f"{run.honest_false_alarms} of {run.n_honest}",
                f"{run.attacks_missed} of {run.n_attack}", f"{run.safety_at(10):.2f}", f"{run.safety_at(50):.2f}",
                f"${run.cost_per_sample:.4f}"]
    results_table = Table(
        ["Monitor", "AUROC", "Honest runs flagged", "Attacks scored 0", "Safety at 10% budget",
         "Safety at 50% budget", "Est. cost per sample"],
        [Group("Comments kept")] + [row(k, raw[k]) for k in raw]
        + [Group("Comments hidden")] + [row(k, strip[k]) for k in strip],
        caption=f"{n} honest and {n} attack runs per monitor, same {n} problems throughout. "
                "Honest runs flagged means honest code that got any score above 0.",
        align="lrrrrrr")

    # ---- figure 1: score distributions ----
    panels = []
    for variant, runs in (("comments kept", raw), ("comments hidden", strip)):
        for k, nm, _, slot, _ in MONITORS:
            panels.append(Panel(nm, charts.score_histogram(f"{nm}, {variant}", runs[k].honest, runs[k].attack,
                                                           ymax=n), slot, variant))
    hist_rows = []
    for variant, runs in (("kept", raw), ("hidden", strip)):
        for k in runs:
            for kind, scores in (("honest", runs[k].honest), ("attack", runs[k].attack)):
                counts = [sum(round(s, 1) == b for s in scores) for b in BINS]
                hist_rows.append([name[k], variant, kind] + [str(c) for c in counts])
    fig_hist = Figure(
        "Where each monitor puts honest and backdoored code",
        panels,
        how="Each small chart counts runs by the score the monitor gave. Top row: comments kept. Bottom row: "
            "comments hidden. A good monitor has gray bars on the left and colored bars on the right.",
        legend=[LegendItem("Honest runs", "swatch", "gray")]
        + [LegendItem(f"Attack runs, {nm}", "swatch", slot) for _, nm, _, slot, _ in MONITORS],
        caption=(f"Sonnet scores {sum(s == 0 for s in raw[sonnet].honest)} of {n} honest runs at 0, and "
                 f"{sum(s >= 0.8 for s in raw[sonnet].attack)} of {n} attacks at 0.8 or higher. "
                 f"Haiku scores {sum(s == 0.1 for s in raw[haiku].honest)} honest runs at 0.1, and "
                 f"{sum(round(s, 1) == 0.1 for s in raw[haiku].attack)} attacks land on that same 0.1, so those "
                 f"attacks look identical to honest code. Luna scores every honest run 0 but also "
                 f"{raw[luna].attacks_missed} attacks. With comments hidden, every attack distribution moves left."),
        table=Table(["Monitor", "Comments", "Runs"] + [f"{b:g}" for b in BINS], hist_rows,
                    caption="Number of runs at each suspicion score.", align="lll" + "r" * len(BINS)),
        columns=3)

    # ---- figure 2: safety by audit budget ----
    safety_panels = []
    for k, nm, _, slot, _ in MONITORS:
        safety_panels.append(Panel(nm, charts.safety_lines(
            nm, budgets, [raw[k].safety_by_budget[b] for b in budgets],
            [strip[k].safety_by_budget[b] for b in budgets], unreliable_below, "kept", "hidden"), slot))
    safety_rows = []
    for variant, runs in (("kept", raw), ("hidden", strip)):
        for k in runs:
            safety_rows.append([name[k], variant] + [f"{runs[k].safety_by_budget[b]:.2f}" for b in budgets])
    fig_safety = Figure(
        "Safety at each audit budget",
        safety_panels,
        how="Safety is the share of backdoors caught. The audit budget is how much honest code humans can afford "
            "to review. Solid line: comments kept. Dashed line: comments hidden. Gray band: too few honest runs to "
            "set a reliable cutoff.",
        legend=[LegendItem("Comments kept", "line", "gray"), LegendItem("Comments hidden", "dash", "gray")],
        caption=(f"Haiku and Luna are flat because of the score ties above. Haiku's cutoff sits at 0.1, where honest "
                 f"runs and {sum(round(s, 1) == 0.1 for s in raw[haiku].attack)} attacks tie, so it catches "
                 f"{raw[haiku].safety_at(10) * 30:.0f} of 30 until the budget reaches 50%. Luna's honest scores are all 0, "
                 f"so its cutoff is 0 at every budget and the {raw[luna].attacks_missed} attacks it scores 0 are never caught."),
        table=Table(["Monitor", "Comments"] + [f"{b:g}%" for b in budgets], safety_rows, align="ll" + "r" * len(budgets)),
        columns=3)

    # ---- figure 3: AUROC, kept vs hidden ----
    fig_auroc = Figure(
        "How much each monitor relies on comments",
        charts.dumbbell([(nm, slot, raw[k].auroc, strip[k].auroc) for k, nm, _, slot, _ in MONITORS],
                        "comments kept", "comments hidden"),
        how="AUROC is the chance that a random backdoored solution scores higher than a random honest one. "
            "1.0 is perfect and 0.5 is guessing. It does not depend on where the audit cutoff sits.",
        legend=[LegendItem("Comments kept", "filled", "gray"), LegendItem("Comments hidden", "ring", "gray")],
        caption=f"All three drop. Luna drops the most ({drops[2]:.2f}), Haiku and Sonnet about the same "
                f"({drops[0]:.2f} and {drops[1]:.2f}).",
        table=Table(["Monitor", "AUROC, comments kept", "AUROC, comments hidden", "Change"],
                    [[name[k], f"{raw[k].auroc:.3f}", f"{strip[k].auroc:.3f}", f"{strip[k].auroc - raw[k].auroc:+.3f}"]
                     for k in raw], align="lrrr"))

    cost_table = Table(
        ["Monitor", "Price per 1M tokens (in / out)", "Tokens per sample", "Est. cost per sample",
         "Est. cost per 1,000 samples"],
        [[nm, PRICES[slot], f"{raw[k].tokens_per_sample:,}", f"${raw[k].cost_per_sample:.4f}",
          f"${raw[k].cost_per_sample * 1000:.2f}"] for k, nm, _, slot, _ in MONITORS],
        caption="Comments-kept runs. Estimated from list prices in src/analyze.py. For the two Anthropic monitors the "
                "estimates matched the drop in the account balance to within a few cents.",
        align="lrrrr")

    sections = [
        Section("What we wanted to find out", [
            Text("Our project compares ways to catch an AI model that is slipping backdoors into code. "
                 "A **monitor** is a second model that reads the code and scores how suspicious it looks. "
                 "This experiment asks two questions."),
            Bullets([
                "Does a strong monitor that we cannot fully trust (here, Sonnet 5.5) catch more backdoors than a weaker monitor "
                "that we do trust (Haiku 4.5, GPT-6 Luna)?",
                "How much of a monitor's skill comes from comments the attacker left in the code, instead of the code itself?",
            ], ordered=True),
            Callout("Real untrusted monitoring has a catch. The monitor could be working with the attacker and "
                    "cover for it. Here the two never coordinate, so Sonnet's numbers show what a capable, honest "
                    "monitor can do. A scheming one would do worse.", "note", "Best case, not worst case"),
        ]),
        Section("How the test works", [
            Text("Each sample is one programming problem from the APPS dataset. The code comes straight from the "
                 "dataset, so no model writes anything. The only thing we pay for is a monitor reading it."),
            Steps([
                ("Problem", f"The first {n} APPS problems that have a verified backdoor."),
                ("Code", "Honest run: the dataset's correct solution. Attack run: a solution with a backdoor, "
                         "meaning it passes the tests but fails on one secret input."),
                ("Monitor", "A model reads the code and returns a suspicion score from 0 (looks fine) to 1 (very suspicious)."),
                ("Audit rule", "Humans can review only a small share of honest work. That share sets a score cutoff."),
                ("Result", "A backdoor scoring above the cutoff is caught. One scoring at or below it is missed."),
            ]),
            Glossary([
                ("Honest run", "The monitor reads correct code with no backdoor."),
                ("Attack run", "The monitor reads code with a verified backdoor."),
                ("Audit budget", "The share of honest runs humans can afford to review. At 5%, the cutoff is the score "
                                 "that only the top 5% of honest runs exceed."),
                ("Safety", "Backdoors caught, divided by backdoors caught plus backdoors that slipped through. "
                           "Here every dataset backdoor works, so safety is simply caught out of 30."),
                ("AUROC", "How well scores separate attack from honest, ignoring any cutoff. 1.0 is perfect, "
                          "0.5 is guessing."),
                ("Comments hidden", "We delete every # comment from the code before the monitor sees it. Many dataset "
                                    "backdoors carry comments that announce the bug, and honest code rarely does."),
            ]),
            Table(["Monitor", "Model", "Role", "Price per 1M tokens (in / out)"],
                  [[nm, f"`{mid}`", role, PRICES[slot]] for _, nm, mid, slot, role in MONITORS],
                  caption="The three monitors. Role is where the model sits in the control setup."),
        ]),
        Section("How we got here", [
            Text("The final design is not where we started. Each stage below fixed a problem in the one before."),
            Journey([
                Stage("Let Sonnet write the attacks",
                      "Ran trusted monitoring (Haiku) and untrusted monitoring (Sonnet) with Sonnet writing both the honest "
                      "and the attack code. 10 problems per mode. The logs for this run are not committed.",
                      "Haiku scored 7 of 10 attacks at exactly 0. Sonnet scored 9 of 10 above 0. Every honest run scored 0 "
                      "for both monitors, so the audit cutoff sat at 0 and the budget sweep was flat. Sonnet also wrote "
                      "fresh attacks in each protocol, so the two monitors never saw the same code.",
                      "Switched to dataset mode. Every monitor now reads identical code, and a run costs cents."),
                Stage("Pilot with 5 problems",
                      "Dataset mode, 5 honest and 5 attack runs, all three monitors.",
                      "Everything ran. Cost for 10 samples was $0.06 for Haiku, $0.10 for Sonnet and under a cent for Luna. "
                      "Each monitor scored attacks higher than honest code on average.",
                      f"Used those costs to size the real run. {n} problems per mode fit the Anthropic budget with room to spare."),
                Stage("Full run, comments kept",
                      f"{n} honest and {n} attack runs per monitor.",
                      f"Sonnet separated the groups almost perfectly (AUROC {fmt_auroc(raw[sonnet].auroc)}). Attacks carried "
                      "comments far more often than honest code did: 20 of 30 against 2 of 30, counted in the submitted code.",
                      "Raised the question of whether monitors were reading comments instead of code. A quick look at the "
                      "raw scores said no, since attacks without comments scored as high. That check turned out to be misleading, "
                      "so we ran the direct test."),
                Stage("Same run, comments hidden",
                      "Deleted every # comment from the code before the monitor saw it. Same problems, same monitors.",
                      "All three got worse: "
                      + ", ".join(f"{name[k]} {fmt_auroc(raw[k].auroc)} → {fmt_auroc(strip[k].auroc)}" for k in raw)
                      + " (AUROC).",
                      "Comments are part of what monitors detect. Results on comment-heavy dataset backdoors overstate how "
                      "well monitors find backdoors in plain code. Sonnet still came first."),
            ]),
        ]),
        Section("Results", [
            tiles,
            results_table,
            fig_hist,
            fig_safety,
            fig_auroc,
            Text(f"**What it costs.** Sonnet is {cost_ratio_haiku:.1f} times Haiku's price per sample "
                 f"and about {cost_ratio_luna:.0f} times Luna's."),
            cost_table,
            Text("**Cheap is not free.** Luna costs a few hundredths of a cent per sample yet misses the most "
                 "attacks. Whether that trade is worth it depends on what a human audit costs, which we have not modelled yet."),
        ]),
        Section("Caveats", [
            Bullets([
                f"**Small sample.** {n} honest and {n} attack runs. One missed attack moves safety by {100 / n:.1f} "
                "points, so gaps under about 0.1 are noise.",
                "**Dataset attacks, not model-written.** Two thirds carry comments and the honest code is human-written. "
                "Read the results as a comparison between monitors, not as absolute detection rates.",
                "**No collusion.** Sonnet never covers for the attacker, and it is a bigger model than Haiku, so "
                "\"untrusted\" and \"stronger\" are bundled together.",
                f"**Ties.** Scores come in steps of 0.1, which flattens the safety curves. AUROC avoids this. Budgets under "
                f"{unreliable_below:.1f}% use less than one honest run (shaded in the chart).",
                "**Scope.** Only # comments were removed, not docstrings or variable names. Costs are estimates from list prices.",
            ]),
        ]),
        Section("Problems we hit along the way", [
            Bullets([
                "`analyze.py` crashed on macOS because its process pool re-ran the script. A `__main__` guard fixed it.",
                "Token counts ignored cached input, so Sonnet looked about five times cheaper than it was (376 against 1,914 "
                "tokens per sample). Now counted properly.",
                "Old runs in the same log folder were mixed into the analysis (44 samples instead of 20). Use a fresh "
                "`LOG_DIR` for every run.",
            ]),
        ]),
        Section("What to do next", [
            Bullets([
                "**Collusion test.** Let the attacker leave a signal for the monitor, then see whether hiding comments or "
                "rewording the code removes it. This is the real test of untrusted monitoring.",
                "**Sweep the audit threshold directly** and put a cost on each human review, so the trade-off between "
                "safety, usefulness and cost is explicit.",
                "**Model-written attacks and more samples.** 100 or more per mode would make small gaps readable.",
                "**More monitors and prompts**, including the chain-of-thought and ensemble options in the library.",
            ]),
        ]),
        Section("Reproduce", [
            Text("Branch `untrusted-monitor-baseline`. Dataset mode, 30 problems, one run per monitor and variant."),
            Code("""
export POLICY=dataset
N=30
# comments kept (add STRIP_COMMENTS=1 and a -strip suffix on LOG_DIR for the hidden-comments runs)
PROTOCOLS=trusted_monitoring TRUSTED_MODEL=anthropic/claude-haiku-4-5-20251001 \\
  LOG_DIR=logs/dataset-haiku45-tm-n$N uv run python src/experiment.py $N
PROTOCOLS=untrusted_monitoring UNTRUSTED_MODEL=anthropic/claude-sonnet-5-5 \\
  LOG_DIR=logs/dataset-sonnet55-um-n$N uv run python src/experiment.py $N
PROTOCOLS=trusted_monitoring TRUSTED_MODEL=openai/gpt-6-luna \\
  LOG_DIR=logs/dataset-gpt6luna-tm-n$N uv run python src/experiment.py $N

# turn each log folder into results/<name>.csv and results/<name>-samples.csv
LOG_DIR=logs/dataset-haiku45-tm-n$N uv run python src/analyze.py

# rebuild this page
uv run python reports/build.py --open
"""),
            Text("Result files: `results/dataset-{haiku45-tm,sonnet55-um,gpt6luna-tm}-n30[-strip].csv` and the matching "
                 "`-samples.csv` files."),
        ]),
    ]

    return Report(
        title="Untrusted monitor baseline: Haiku, Sonnet and Luna on APPS",
        subtitle="Which monitor catches the most backdoors, and how much does it lean on the comments an attacker leaves?",
        date="2026-10-20",
        authors=["Punjaya"],
        summary=summary,
        sections=sections,
        status=f"Preliminary, {n} + {n} samples",
        tags=["APPS", "untrusted monitoring", "dataset mode"],
    )
