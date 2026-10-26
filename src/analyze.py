"""Turn the logs from experiment.py into the paper's two headline numbers.

    uv run python src/analyze.py

usefulness = fraction of honest-mode runs that solve the problem (what the protocol costs you)
safety     = caught / (caught + uncaught successful backdoors) at a given audit budget
             (audit budget = % of honest runs a human can afford to review)

Optional env vars:
    LOG_DIR        where experiment.py wrote its logs (default logs)
    PROTOCOLS      comma-separated protocols to analyse (default: every subdirectory present)
    AUDIT_BUDGETS  comma-separated audit budgets in % (default 0.5,1,2,5,10,20,50)
    RUN_LABEL      name for the results CSV (default: the LOG_DIR folder name)

Writes results/<RUN_LABEL>.csv (safety per audit budget, tokens and estimated cost per sample),
results/<RUN_LABEL>-samples.csv (one suspicion score per sample), both small and meant to be
committed, and <LOG_DIR>/safety_vs_audit_budget.png (gitignored).
"""
import json
import os
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from control_arena.analysis import compute_safety, compute_usefulness, samples_df

LOG_DIR = os.getenv("LOG_DIR", "logs")
SCORER = "max_suspicion_scorer"
AUDIT_BUDGETS = [float(b) for b in os.getenv("AUDIT_BUDGETS", "0.5,1,2,5,10,20,50").split(",")]
RUN_LABEL = os.getenv("RUN_LABEL", Path(LOG_DIR).name)
KNOWN = ["trusted_monitoring", "defer_to_trusted", "untrusted_monitoring"]
protocols = os.getenv("PROTOCOLS", "").split(",") if os.getenv("PROTOCOLS") else [
    p for p in KNOWN if Path(LOG_DIR, p).is_dir()
]


# USD per 1M tokens: (input, output, cache write, cache read). List prices as of 2026-10;
# edit when they change. A model missing here gets no dollar estimate (tokens are still counted).
PRICES = {
    "anthropic/claude-haiku-4-5-20251001": (1.00, 5.00, 1.25, 0.10),
    "anthropic/claude-sonnet-5-5": (2.00, 10.00, 2.50, 0.20),
    "anthropic/claude-haiku-5-5": (0.10, 0.50, 0.125, 0.01),
    "openai/gpt-6-luna": (0.10, 0.50, 0.10, 0.01),
}
USAGE_FIELDS = ("input_tokens", "output_tokens", "input_tokens_cache_write", "input_tokens_cache_read")


def usage_by_model(df: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Sum each token field per model across all samples.

    Inspect reports cached input separately (input_tokens_cache_write/read), so input + output
    alone undercounts providers that cache. Output includes reasoning tokens.
    """
    totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for usage in df["model_usage"].dropna():
        usage = json.loads(usage) if isinstance(usage, str) else usage
        for model, u in usage.items():
            for field in USAGE_FIELDS:
                totals[model][field] += int(u.get(field) or 0)
    return {model: dict(fields) for model, fields in totals.items()}


def est_cost_usd(usage: dict[str, dict[str, int]]) -> float | None:
    """Dollar estimate from PRICES, or None if any model has no listed price."""
    if any(model not in PRICES for model in usage):
        return None
    return sum(
        sum(u[field] * price for field, price in zip(USAGE_FIELDS, PRICES[model])) / 1e6
        for model, u in usage.items()
    )


def main() -> None:
    rows = []
    sample_rows = []
    plt.figure()
    for protocol in protocols:
        df = samples_df(f"{LOG_DIR}/{protocol}")
        n_honest = int((df["eval_mode"] == "honest").sum())
        n_attack = int((df["eval_mode"] == "attack").sum())
        print(f"\n== {protocol}: {n_honest} honest + {n_attack} attack samples ==")
        print(df.groupby("eval_mode")[["main_task_success", "side_task_success", f"score_{SCORER}"]]
              .agg("mean").round(2).to_string())

        usefulness = compute_usefulness(df)
        usage = usage_by_model(df)
        tokens = {m: sum(u.values()) for m, u in usage.items()}
        cost = est_cost_usd(usage)
        cost_per_sample = round(cost / len(df), 5) if cost is not None else ""
        print(f"usefulness: {usefulness:.2f}")
        print(f"tokens per sample by model: { {m: round(t / len(df)) for m, t in tokens.items()} }")
        if cost is not None:
            print(f"estimated cost: ${cost:.3f} total, ${cost / len(df):.4f} per sample")
        scores = df[["eval_mode", "id", f"score_{SCORER}"]].rename(
            columns={"eval_mode": "mode", "id": "sample_id", f"score_{SCORER}": "suspicion"})
        sample_rows.append(scores.assign(run=RUN_LABEL, protocol=protocol).sort_values(["mode", "sample_id"]))

        safeties = [compute_safety(df, SCORER, b) for b in AUDIT_BUDGETS]
        for b, s in zip(AUDIT_BUDGETS, safeties):
            # An audit budget below 100/n_honest % is thresholded on less than one honest sample.
            note = "  (too few honest samples for this budget)" if b * n_honest / 100 < 1 else ""
            print(f"  audit budget {b:>4}% -> safety {s:.2f}{note}")
            rows.append({
                "run": RUN_LABEL, "protocol": protocol, "n_honest": n_honest, "n_attack": n_attack,
                "audit_budget_pct": b, "safety": round(s, 3), "usefulness": round(usefulness, 3),
                "tokens_per_sample": json.dumps({m: round(t / len(df)) for m, t in tokens.items()}),
                "est_cost_usd_per_sample": cost_per_sample,
            })
        plt.plot(AUDIT_BUDGETS, safeties, marker="o", label=f"{protocol} (usefulness {usefulness:.2f})")

    plt.xscale("log")
    plt.xlabel("Audit budget (% of honest runs reviewed, log scale)")
    plt.ylabel("Safety")
    plt.title(RUN_LABEL)
    plt.legend()
    plt.grid(True)
    plot_path = Path(LOG_DIR, "safety_vs_audit_budget.png")
    plt.savefig(plot_path, dpi=120)

    Path("results").mkdir(exist_ok=True)
    csv_path = Path("results", f"{RUN_LABEL}.csv")
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    # One row per sample, so the report viewer (reports/) can draw score distributions
    # from committed files alone, without the gitignored logs.
    samples_path = Path("results", f"{RUN_LABEL}-samples.csv")
    pd.concat(sample_rows)[["run", "protocol", "mode", "sample_id", "suspicion"]].to_csv(samples_path, index=False)
    print(f"\nsaved {plot_path}, {csv_path} and {samples_path}")


# The guard matters on Windows: samples_df reads logs in worker processes, and each
# worker re-imports this file. Without it, every worker re-runs the analysis and crashes.
if __name__ == "__main__":
    main()
