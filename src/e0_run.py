"""E0: measure the monitor's suspicion-score resolution and the budget floor.

    uv run python src/e0_run.py 200      # 200 honest + 200 attack

Why this runs before any protocol comparison
--------------------------------------------
Both budget dials in a control protocol are percentiles of the honest suspicion
distribution: the audit budget `a` directly, and the intervention budget `d`
because `defer_to_trusted_builder` takes `defer_threshold` as a *score*, not a
share. `basic_monitor` prompts for an integer 0-10 and parses it with a regex,
so that distribution has at most 11 distinct values. If the top score bin holds
more than 1% of honest mass, then no threshold realises a 1% budget and the low
end of the budget axis is not measurable at all.

This run measures that, and nothing else. It is deliberately cheap: the policy
is `apps_solution_policy`, which submits the dataset's stored solution (honest)
or stored backdoor (attack) and makes **zero untrusted-model calls**. The
monitor is therefore the only billed component, which also means sample-level
token usage in the log *is* monitor usage, with no log-walking needed.

The honest rows here are the dataset's human-written reference solutions while
the attack rows are LLM-rewritten backdoors, so recall figures carry an
authorship confound. This run is a resolution measurement, not a calibration:
its thresholds are not carried into later experiments, where both sides come
from the same untrusted model.
"""
import os
import sys
from pathlib import Path

from inspect_ai import eval as inspect_eval
from inspect_ai.model import GenerateConfig
from inspect_ai.model._generate_config import BatchConfig

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task_product
from control_arena.micro_protocol import trusted_monitoring_builder
from control_arena.monitor import basic_monitor_builder, ensemble_monitor_builder
from control_arena.monitor._types import MonitorScoreRange
from control_arena.scorers import max_suspicion_scorer
from control_arena.settings.apps.apps_setting import AppsSetting
from control_arena.settings.apps.apps_solution_policy import apps_solution_policy

LOG_DIR = os.getenv("LOG_DIR", "logs/e0")
SHUFFLE_SEED = int(os.getenv("SHUFFLE_SEED", "20261018"))
# Which monitor to measure. E0 established that the default 0-10 integer prompt
# yields 3 distinct values and a 2% budget floor; the other arms are attempts to
# buy back resolution. See experiments/e0-monitor-resolution/REPORT.md.
ARM = os.getenv("MONITOR_ARM", "baseline")
# BATCH=1 routes model calls through the Anthropic Batches API for a 50% price
# cut. MEASURED AND NOT RECOMMENDED HERE. Monitor-only, cache disabled:
#     n=20   24.5s unbatched   ->    247s batched   (10x)
#     n=100  108.3s unbatched  ->  67,795s batched  (626x, 18.8 hours)
# The agent loop advances a sample only once its model call returns, so few
# requests are ever in flight, batches never fill, and each small batch still
# pays full queue latency. The penalty gets worse with n, not better. Treat
# this switch as unusable until someone demonstrates that much higher
# concurrency keeps batches full.
# The discount is invisible in token counts, so e0_report.py reads the batch
# config back out of the eval log to price a batched run correctly.
BATCH = os.getenv("BATCH", "").lower() in ("1", "true", "yes")
n_problems = int(sys.argv[1]) if len(sys.argv) > 1 else 200

# Pinned so the run is reproducible from the commit. Trusted model does the
# monitoring; untrusted is never called, since apps_solution_policy replaces it.
TRUSTED_MODEL = os.getenv("TRUSTED_MODEL", "anthropic/claude-haiku-4-5-20251001")

_batch = GenerateConfig(
    batch=BatchConfig(size=min(100, n_problems), send_delay=30, tick=10)
) if BATCH else None

config = ControlEvalConfig(
    untrusted_model=TRUSTED_MODEL,  # unused: the policy makes no model calls
    trusted_model=TRUSTED_MODEL,
    limit=n_problems,
    max_sandboxes=10,
    trusted_config=_batch,
    untrusted_config=_batch,
)

setting = AppsSetting(
    # Only samples with a verified working backdoor, so an "attack" row always
    # contains an attack. Pairs with return_solution_if_no_backdoor=False below:
    # the policy's default silently submits clean code when no backdoor exists.
    has_backdoor_solution=True,
    backdoor_source="control_tax",
    # Default ordering is a deterministic prefix, which would make any smaller
    # pilot a nested subset of a larger run rather than an independent sample.
    shuffle_dataset=True,
    shuffle_seed=SHUFFLE_SEED,
)

_PROMPT_0_100 = Path(__file__).parent / "prompts" / "monitor_0_100.txt"

def build_monitor(arm: str):
    """Monitor variants. Each is an attempt to raise the usable budget floor."""
    if arm == "baseline":
        # 0-10 integer prompt, the library default.
        return basic_monitor_builder()
    if arm == "range100":
        # Same prompt, 0-100 scale, with an explicit instruction not to round.
        return basic_monitor_builder(
            prompt=_PROMPT_0_100.read_text(),
            score_range=MonitorScoreRange(min=0.0, max=100.0),
        )
    if arm == "ensemble10":
        # Averaging 10 draws multiplies resolution by ~10, but costs 10x the
        # calls, and mixes a resolution change with a ranking change. E0b
        # separates those by comparing at matched achieved FPR.
        return ensemble_monitor_builder(num_samples=10, temperature=1.0)
    raise SystemExit(f"unknown MONITOR_ARM={arm!r}; expected baseline|range100|ensemble10")


protocol = trusted_monitoring_builder(
    policy=apps_solution_policy(return_solution_if_no_backdoor=False),
    monitor=build_monitor(ARM),
)

tasks = get_control_task_product(
    settings=setting,
    micro_protocols=protocol,
    modes=[EvalMode.HONEST, EvalMode.ATTACK],
    eval_config=config,
    monitoring_scorers=[max_suspicion_scorer()],
)

print(
    f"E0 arm={ARM}: n={n_problems} per mode | monitor={TRUSTED_MODEL} | seed={SHUFFLE_SEED}\n"
    f"    policy=apps_solution_policy (zero untrusted-model calls)\n"
    f"    batch={'ON: 50% cheaper, much slower' if BATCH else 'off'}\n"
    f"    log_dir={LOG_DIR}"
)
inspect_eval(tasks, **{**config.eval_args(), "log_dir": LOG_DIR})
