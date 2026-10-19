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

Writes results/<RUN_LABEL>.csv (small, meant to be committed) and
<LOG_DIR>/safety_vs_audit_budget.png (gitignored).
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
KNOWN = ["trusted_monitoring", "defer_to_trusted"]
protocols = os.getenv("PROTOCOLS", "").split(",") if os.getenv("PROTOCOLS") else [
    p for p in KNOWN if Path(LOG_DIR, p).is_dir()
]


def tokens_by_model(df: pd.DataFrame) -> dict[str, int]:
    """Sum input + output tokens per model across all samples (the cost axis)."""
    totals: dict[str, int] = defaultdict(int)
    for usage in df["model_usage"].dropna():
        usage = json.loads(usage) if isinstance(usage, str) else usage
        for model, u in usage.items():
            totals[model] += int(u.get("input_tokens", 0)) + int(u.get("output_tokens", 0))
    return dict(totals)


def main() -> None:
    rows = []
    plt.figure()
    for protocol in protocols:
        df = samples_df(f"{LOG_DIR}/{protocol}")
        n_honest = int((df["eval_mode"] == "honest").sum())
        n_attack = int((df["eval_mode"] == "attack").sum())
        print(f"\n== {protocol}: {n_honest} honest + {n_attack} attack samples ==")
        print(df.groupby("eval_mode")[["main_task_success", "side_task_success", f"score_{SCORER}"]]
              .agg("mean").round(2).to_string())

        usefulness = compute_usefulness(df)
        tokens = tokens_by_model(df)
        print(f"usefulness: {usefulness:.2f}")
        print(f"tokens per sample by model: { {m: round(t / len(df)) for m, t in tokens.items()} }")

        safeties = [compute_safety(df, SCORER, b) for b in AUDIT_BUDGETS]
        for b, s in zip(AUDIT_BUDGETS, safeties):
            # An audit budget below 100/n_honest % is thresholded on less than one honest sample.
            note = "  (too few honest samples for this budget)" if b * n_honest / 100 < 1 else ""
            print(f"  audit budget {b:>4}% -> safety {s:.2f}{note}")
            rows.append({
                "run": RUN_LABEL, "protocol": protocol, "n_honest": n_honest, "n_attack": n_attack,
                "audit_budget_pct": b, "safety": round(s, 3), "usefulness": round(usefulness, 3),
                "tokens_per_sample": json.dumps({m: round(t / len(df)) for m, t in tokens.items()}),
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
    print(f"\nsaved {plot_path} and {csv_path}")


# The guard matters on Windows: samples_df reads logs in worker processes, and each
# worker re-imports this file. Without it, every worker re-runs the analysis and crashes.
if __name__ == "__main__":
    main()
