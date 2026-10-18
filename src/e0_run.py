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

from inspect_ai import eval as inspect_eval

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task_product
from control_arena.micro_protocol import trusted_monitoring_builder
from control_arena.monitor import basic_monitor_builder
from control_arena.scorers import max_suspicion_scorer
from control_arena.settings.apps.apps_setting import AppsSetting
from control_arena.settings.apps.apps_solution_policy import apps_solution_policy

LOG_DIR = os.getenv("LOG_DIR", "logs/e0")
SHUFFLE_SEED = int(os.getenv("SHUFFLE_SEED", "20261018"))
n_problems = int(sys.argv[1]) if len(sys.argv) > 1 else 200

# Pinned so the run is reproducible from the commit. Trusted model does the
# monitoring; untrusted is never called, since apps_solution_policy replaces it.
TRUSTED_MODEL = os.getenv("TRUSTED_MODEL", "anthropic/claude-haiku-4-5-20251001")

config = ControlEvalConfig(
    untrusted_model=TRUSTED_MODEL,  # unused: the policy makes no model calls
    trusted_model=TRUSTED_MODEL,
    limit=n_problems,
    max_sandboxes=10,
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

protocol = trusted_monitoring_builder(
    policy=apps_solution_policy(return_solution_if_no_backdoor=False),
    monitor=basic_monitor_builder(),
)

tasks = get_control_task_product(
    settings=setting,
    micro_protocols=protocol,
    modes=[EvalMode.HONEST, EvalMode.ATTACK],
    eval_config=config,
    monitoring_scorers=[max_suspicion_scorer()],
)

print(
    f"E0: n={n_problems} per mode | monitor={TRUSTED_MODEL} | seed={SHUFFLE_SEED}\n"
    f"    policy=apps_solution_policy (zero untrusted-model calls)\n"
    f"    log_dir={LOG_DIR}"
)
inspect_eval(tasks, **{**config.eval_args(), "log_dir": LOG_DIR})
