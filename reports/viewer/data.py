"""Load a finished run from results/ and compute the numbers reports show.

A "run" is one RUN_LABEL written by src/analyze.py: results/<label>.csv (safety per audit
budget, tokens, cost) and results/<label>-samples.csv (one suspicion score per sample).
Reports read only these committed files, never the gitignored logs.
"""
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

RESULTS_DIR = Path(__file__).resolve().parents[2] / "results"


def auroc(positive: list[float], negative: list[float]) -> float:
    """Chance that a random attack scores higher than a random honest run (ties count half).

    1.0 means every attack outscores every honest run, 0.5 means the monitor is guessing.
    It needs no audit threshold, so it is not affected by ties at the threshold.
    """
    pairs = [(p > n) + 0.5 * (p == n) for p in positive for n in negative]
    return sum(pairs) / len(pairs)


@dataclass
class Run:
    label: str
    n_honest: int
    n_attack: int
    safety_by_budget: dict[float, float]
    tokens_per_sample: int
    cost_per_sample: float | None  # estimated USD, from the price table in src/analyze.py
    honest: list[float]  # suspicion score of each honest run
    attack: list[float]  # suspicion score of each attack run

    def safety_at(self, budget: float) -> float:
        return self.safety_by_budget[budget]

    @property
    def auroc(self) -> float:
        return auroc(self.attack, self.honest)

    @property
    def honest_false_alarms(self) -> int:
        """Honest runs the monitor scored above zero."""
        return sum(s > 0 for s in self.honest)

    @property
    def attacks_missed(self) -> int:
        """Attacks the monitor scored exactly zero."""
        return sum(s == 0 for s in self.attack)

    @property
    def mean_attack_score(self) -> float:
        return sum(self.attack) / len(self.attack)

    def reliable_budgets(self) -> list[float]:
        """Budgets that threshold on at least one whole honest run."""
        return [b for b in self.safety_by_budget if b * self.n_honest / 100 >= 1]


def load_run(label: str) -> Run:
    summary_path = RESULTS_DIR / f"{label}.csv"
    samples_path = RESULTS_DIR / f"{label}-samples.csv"
    for path in (summary_path, samples_path):
        if not path.exists():
            raise FileNotFoundError(
                f"{path} not found. Run `LOG_DIR=logs/{label} uv run python src/analyze.py` "
                "and commit the CSVs it writes to results/."
            )
    summary = pd.read_csv(summary_path)
    samples = pd.read_csv(samples_path)
    first = summary.iloc[0]
    cost = first.get("est_cost_usd_per_sample")
    return Run(
        label=label,
        n_honest=int(first["n_honest"]),
        n_attack=int(first["n_attack"]),
        safety_by_budget=dict(zip(summary["audit_budget_pct"].astype(float), summary["safety"].astype(float))),
        tokens_per_sample=sum(json.loads(first["tokens_per_sample"]).values()),
        cost_per_sample=None if pd.isna(cost) else float(cost),
        honest=samples.loc[samples["mode"] == "honest", "suspicion"].astype(float).tolist(),
        attack=samples.loc[samples["mode"] == "attack", "suspicion"].astype(float).tolist(),
    )
