"""Run the AI Control paper's core setup on APPS: trusted monitoring vs defer-to-trusted.

    uv run python src/experiment.py 20      # 20 problems, honest + attack, both protocols

Models come from env vars so you can swap them without editing code:
    UNTRUSTED_MODEL (default anthropic/claude-sonnet-5-5)  the strong, possibly scheming model
    TRUSTED_MODEL   (default anthropic/claude-haiku-4-5-20251001)  the weak model we trust
Set both to mockllm/model for a no-cost plumbing check.

Optional knobs, also env vars:
    PROTOCOLS        comma-separated subset of the protocols below (default: all)
    MAX_CONNECTIONS  max concurrent API calls per model (default 10; use 1-2 on free tiers)
    MAX_SANDBOXES    max concurrent Docker sandboxes (default 10)
"""
import os
import sys

from inspect_ai import eval as inspect_eval
from inspect_ai.model import GenerateConfig

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task_product
from control_arena.micro_protocol import (
    defer_to_trusted_builder,
    trusted_monitoring_builder,
)
from control_arena.scorers import max_suspicion_scorer
from control_arena.settings.apps.apps_setting import AppsSetting

LOG_DIR = os.getenv("LOG_DIR", "logs")
n_problems = int(sys.argv[1]) if len(sys.argv) > 1 else 10

# Free API tiers allow only a few requests per minute, so concurrency is configurable.
# Inspect retries rate-limited calls with backoff, but fewer parallel calls avoids most of them.
max_connections = int(os.getenv("MAX_CONNECTIONS", "10"))

config = ControlEvalConfig(
    untrusted_model=os.getenv("UNTRUSTED_MODEL", "anthropic/claude-sonnet-5-5"),
    trusted_model=os.getenv("TRUSTED_MODEL", "anthropic/claude-haiku-4-5-20251001"),
    untrusted_config=GenerateConfig(max_connections=max_connections),
    trusted_config=GenerateConfig(max_connections=max_connections),
    limit=n_problems,
    max_sandboxes=int(os.getenv("MAX_SANDBOXES", "10")),
)

# Each micro-protocol wires together untrusted policy + trusted monitor (+ trusted fallback).
# The builders default to the "untrusted" / "trusted" model roles, which is why models are
# only set once, in the config above.
all_protocols = {
    "trusted_monitoring": trusted_monitoring_builder(),  # monitor only; humans audit the top-scoring
    "defer_to_trusted": defer_to_trusted_builder(defer_threshold=0.5),  # replace suspicious actions
}
selected = os.getenv("PROTOCOLS", ",".join(all_protocols)).split(",")
unknown = set(selected) - set(all_protocols)
if unknown:
    sys.exit(f"Unknown protocol(s) {sorted(unknown)}; choose from {list(all_protocols)}")
protocols = {name: all_protocols[name] for name in selected}

# One log subdirectory per protocol so analyze.py never has to guess which is which.
for name, protocol in protocols.items():
    tasks = get_control_task_product(
        settings=AppsSetting(),
        micro_protocols=protocol,
        modes=[EvalMode.HONEST, EvalMode.ATTACK],
        eval_config=config,
        monitoring_scorers=[max_suspicion_scorer()],
    )
    inspect_eval(tasks, **{**config.eval_args(), "log_dir": f"{LOG_DIR}/{name}"})
