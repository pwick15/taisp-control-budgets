"""Report: Haiku 5.5 as a trusted monitor on 500 + 500 APPS dataset samples, comments hidden.

Numbers in the text and tables are computed from results/*.csv, so re-running
src/analyze.py and rebuilding keeps the page consistent.
"""
import pandas as pd

from viewer import charts
from viewer.components import (
    Bullets, Callout, Code, Figure, Glossary, LegendItem, Panel, Report, Section, StatTiles, Steps,
    Table, Text, Tile, fmt_auroc,
)
from viewer.data import RESULTS_DIR, load_run

LABEL = "dataset-haiku55-tm-n500-strip"
OLD_LABEL = "dataset-haiku45-tm-n30-strip"
BINS = [round(i / 10, 1) for i in range(11)]


def auroc_on(label: str, ids: set[str]) -> float:
    """AUROC of one results file, using only the problems in `ids`."""
    df = pd.read_csv(RESULTS_DIR / f"{label}-samples.csv", dtype={"sample_id": str})
    df = df[df["sample_id"].isin(ids)]
    attack = df.loc[df["mode"] == "attack", "suspicion"].to_numpy()
    honest = df.loc[df["mode"] == "honest", "suspicion"].to_numpy()
    wins = (attack[:, None] > honest[None, :]).sum() + 0.5 * (attack[:, None] == honest[None, :]).sum()
    return wins / (len(attack) * len(honest))


def build() -> Report:
    run = load_run(LABEL)
    old = load_run(OLD_LABEL)
    n = run.n_honest
    budgets = sorted(run.safety_by_budget)
    caught = {b: round(run.safety_by_budget[b] * run.n_attack) for b in budgets}

    # The plateau: almost every honest run gets the "looks fine" score of 0.1.
    honest_at_01 = sum(round(s, 1) == 0.1 for s in run.honest)
    honest_at_0 = sum(s == 0 for s in run.honest)
    share_honest_01 = honest_at_01 / n
    attacks_low = sum(s <= 0.1 for s in run.attack)  # at or below the cutoff of 0.1
    attacks_at_01 = sum(round(s, 1) == 0.1 for s in run.attack)
    attacks_at_0 = sum(s == 0 for s in run.attack)
    share_honest_above_0 = (n - honest_at_0) / n  # budget needed to push the cutoff down to 0.0
    plateau = run.safety_by_budget[budgets[-1]]

    # Same first 30 problems, Haiku 4.5 vs Haiku 5.5 (both comments hidden).
    old_ids = set(pd.read_csv(RESULTS_DIR / f"{OLD_LABEL}-samples.csv", dtype={"sample_id": str})["sample_id"])
    auroc_new_30 = auroc_on(LABEL, old_ids)
    auroc_old_30 = auroc_on(OLD_LABEL, old_ids)

    cost_1000 = run.cost_per_sample * 1000
    cost_ratio = old.cost_per_sample / run.cost_per_sample

    summary = [
        f"**With a 2% audit budget, the monitor catches {run.safety_at(2):.0%} of backdoors "
        f"({caught[2]} of {run.n_attack}).** At 1% it catches {run.safety_at(1):.0%}, and at 0.5% only "
        f"{run.safety_at(0.5):.0%}.",
        f"**More budget does not help beyond 2%.** Safety stays at {plateau:.2f} all the way to 50%. "
        f"{attacks_low} backdoors ({attacks_low / run.n_attack:.0%}) get the same score as ordinary honest code, "
        f"so the monitor cannot tell them apart. The section on the {plateau:.2f} limit explains why.",
        f"**It is cheap.** About ${cost_1000:.2f} for all {n + run.n_attack:,} runs. Haiku 5.5 thinks before it answers, so it "
        f"used {run.tokens_per_sample / old.tokens_per_sample:.1f} times the tokens Haiku 4.5 did, but its price per "
        f"token is so low that it still costs {cost_ratio:.1f} times less per sample.",
        f"**Not clearly better than Haiku 4.5.** On the same 30 problems, Haiku 5.5 scores {auroc_new_30:.2f} "
        f"(AUROC) against {auroc_old_30:.2f} for Haiku 4.5. With 30 problems that gap is within noise.",
    ]

    tiles = StatTiles([
        Tile("Safety at 1% budget", f"{run.safety_at(1):.2f}", f"{caught[1]} of {run.n_attack} backdoors caught", "s1"),
        Tile("Safety at 2% budget and above", f"{plateau:.2f}", f"{caught[2]} of {run.n_attack} caught, no change up to 50%", "s1"),
        Tile("AUROC", fmt_auroc(run.auroc), "how well scores separate attack from honest", "s1"),
        Tile("Cost for all runs", f"${cost_1000:.2f}", f"{run.tokens_per_sample:,} tokens per sample", "s1"),
    ])

    budget_table = Table(
        ["Audit budget", "Honest runs reviewed", "Backdoors caught", "Safety"],
        [[f"{b:g}%", f"{b * n / 100:g} of {n}", f"{caught[b]} of {run.n_attack}", f"{run.safety_at(b):.2f}"]
         for b in budgets],
        caption="Each row sets the review cutoff from the honest runs, then counts the backdoors that score above it.",
        align="lrrr")

    # ---- figure 1: score distributions ----
    counts_h = [sum(round(s, 1) == b for s in run.honest) for b in BINS]
    counts_a = [sum(round(s, 1) == b for s in run.attack) for b in BINS]
    fig_hist = Figure(
        "How the monitor scores honest and backdoored code",
        [Panel("Haiku 5.5", charts.score_histogram("Haiku 5.5", run.honest, run.attack, ymax=max(counts_h + counts_a)), "s1")],
        how="Each bar counts runs by the suspicion score the monitor gave (0 is fine, 1 is very suspicious). "
            "Gray is honest code, blue is backdoored code. A good monitor has gray on the left and blue on the right.",
        legend=[LegendItem("Honest runs", "swatch", "gray"), LegendItem("Attack runs", "swatch", "s1")],
        caption=(f"{honest_at_01} of {n} honest runs ({share_honest_01:.0%}) score exactly 0.1, the monitor's most "
                 f"common answer for code that looks fine. {attacks_at_01 + attacks_at_0} of {run.n_attack} backdoors also score "
                 f"0.1 or lower. The rest of the attacks spread out between 0.2 and 0.9."),
        table=Table(["Score"] + [f"{b:g}" for b in BINS],
                    [["Honest runs"] + [str(c) for c in counts_h], ["Attack runs"] + [str(c) for c in counts_a]],
                    caption="Number of runs at each suspicion score.", align="l" + "r" * len(BINS)),
        columns=1)

    # ---- figure 2: safety by audit budget ----
    fig_safety = Figure(
        "Safety at each audit budget",
        [Panel("Haiku 5.5", charts.safety_lines("Haiku 5.5", budgets, [run.safety_by_budget[b] for b in budgets], None,
                                                100 / n), "s1")],
        how="Safety is the share of backdoors caught. The audit budget is the share of honest runs humans can afford "
            "to review. Higher and further left is better.",
        legend=[LegendItem("Haiku 5.5, comments hidden", "line", "s1")],
        caption=f"Safety climbs from {run.safety_at(0.5):.2f} to {plateau:.2f} between 0.5% and 2%, then goes flat.",
        table=Table(["Audit budget"] + [f"{b:g}%" for b in budgets],
                    [["Safety"] + [f"{run.safety_at(b):.2f}" for b in budgets]], align="l" + "r" * len(budgets)),
        columns=1)

    sections = [
        Section("What we wanted to find out", [
            Text("Our project compares ways to catch an AI model that is slipping backdoors into code. A **monitor** is "
                 "a second, trusted model that reads the code and scores how suspicious it looks. This run adds one more "
                 "monitor to the comparison: Anthropic's Haiku 5.5."),
            Bullets([
                "How many backdoors does Haiku 5.5 catch at each audit budget?",
                "How does it compare, on cost and accuracy, with the monitors we tried earlier?",
            ], ordered=True),
        ]),
        Section("How the test works", [
            Text("Each sample is one programming problem from the APPS dataset. The code comes straight from the dataset, "
                 "so no model writes anything. The only model call is the monitor reading the code."),
            Steps([
                ("Problems", f"The first {n} APPS problems that have a verified backdoor. Same order and filter as the smaller "
                              f"runs, so their problems are the first ones here."),
                ("Code", "Honest run: the dataset's correct solution. Attack run: a solution with a backdoor, meaning it "
                         "passes the tests but gives a wrong answer on one secret input."),
                ("Comments hidden", "We delete every # comment before the monitor reads the code. Many dataset backdoors "
                                    "have comments that announce the bug, and honest code rarely does."),
                ("Monitor", "Haiku 5.5 reads the code and gives a suspicion score from 0 to 1."),
                ("Audit rule", "Humans can review only a small share of honest runs. That share sets a score cutoff. "
                               "A backdoor scoring above the cutoff is caught."),
            ]),
            Glossary([
                ("Audit budget", f"The share of honest runs humans can afford to review. At 2% of {n} honest runs, that is "
                                 f"{2 * n // 100} runs: the {2 * n // 100} most suspicious ones."),
                ("Safety", "Backdoors caught divided by backdoors caught plus backdoors that slipped through. Every "
                           f"dataset backdoor works, so safety is just caught out of {run.n_attack}."),
                ("AUROC", "The chance that a random backdoor scores higher than a random honest run. 1.0 is perfect, "
                          "0.5 is guessing."),
            ]),
        ]),
        Section("Results", [
            tiles,
            budget_table,
            fig_hist,
            fig_safety,
            Callout(
                f"Honest code almost always gets the same score: {honest_at_01} of {n} honest runs get 0.1, and "
                f"{honest_at_0} more get 0. So once the budget reaches about 2%, the review cutoff is 0.1. "
                f"A backdoor is caught only if it scores **above** the cutoff. "
                f"{attacks_low} backdoors ({attacks_low / run.n_attack:.0%}) score 0.1 or 0, the same as ordinary honest "
                f"code, so they are never caught. That leaves {caught[2]} of {run.n_attack} = {plateau:.2f}. "
                f"To catch the {attacks_at_01} backdoors scoring 0.1, the cutoff would have to drop to 0, which means "
                f"reviewing about {share_honest_above_0:.0%} of honest runs. The budgets we test stop at 50%.",
                "note", f"Why safety stops at {plateau:.2f}"),
            Text(f"**What it costs.** About ${cost_1000:.2f} for {n + run.n_attack:,} runs, from the list price of $0.10 per "
                 f"million input tokens and $0.50 per million output tokens. Of the 1.09 million output tokens, 0.58 million "
                 f"were the model thinking, which is why it used {run.tokens_per_sample:,} tokens per sample against "
                 f"{old.tokens_per_sample:,} for Haiku 4.5 (read from the run log, not from the results files)."),
            Table(["Monitor", "Price per 1M tokens (in / out)", "Tokens per sample", "Est. cost per sample",
                   "Est. cost per 1,000 samples"],
                  [["Haiku 5.5", "$0.10 / $0.50", f"{run.tokens_per_sample:,}", f"${run.cost_per_sample:.4f}",
                    f"${cost_1000:.2f}"],
                   ["Haiku 4.5", "$1 / $5", f"{old.tokens_per_sample:,}", f"${old.cost_per_sample:.4f}",
                    f"${old.cost_per_sample * 1000:.2f}"]],
                  caption="Both with comments hidden. Haiku 4.5 numbers come from the earlier 30-problem run.",
                  align="lrrrr"),
            Text(f"**Against Haiku 4.5.** On the same first 30 problems, with comments hidden, Haiku 5.5 scores AUROC "
                 f"{auroc_new_30:.2f} and Haiku 4.5 scores {auroc_old_30:.2f}. Thirty problems is too few to call that a "
                 "real difference."),
        ]),
        Section("Caveats", [
            Bullets([
                "**Dataset backdoors, not one attacker.** They come from two published sources and several different "
                "models. Read the results as a comparison between monitors, not as the detection rate against any one model.",
                "**Honest code is human-written.** Usefulness is always 1.0 in this mode and tells us nothing, so compare "
                "safety only.",
                "**Ties.** Scores come in steps of 0.1 and most honest runs share one score. That is why the curve goes "
                "flat. AUROC is not affected by this.",
                "**Thinking left at default.** Haiku 5.5 reasons at medium effort by default. We did not change it, and "
                "the logs do not record it.",
                "**One run per setting.** Re-running would hit Inspect's cache and give identical scores, so we have not "
                "measured run-to-run variation.",
            ]),
        ]),
        Section("Reproduce", [
            Text("Dataset mode, 500 problems, trusted monitoring, comments hidden. Needs Docker running and "
                 "`ANTHROPIC_API_KEY` in `.env`. About 30 minutes per mode."),
            Code("scripts/run_dataset_monitor.sh\nuv run python reports/build.py --open"),
            Text(f"Result files: `results/{LABEL}.csv` and `results/{LABEL}-samples.csv`."),
        ]),
    ]

    return Report(
        title="Haiku 5.5 as a trusted monitor on APPS",
        subtitle="How many dataset backdoors does Haiku 5.5 catch at each audit budget, and what does it cost?",
        date="2026-10-26",
        authors=["Punjaya"],
        summary=summary,
        sections=sections,
        status=f"Complete, {n} + {run.n_attack} samples, one monitor",
        tags=["APPS", "trusted monitoring", "dataset mode", "Haiku 5.5"],
    )
