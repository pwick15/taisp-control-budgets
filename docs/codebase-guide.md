# Codebase guide

How the scripts in `src/` map onto the ControlArena library, and where to start when extending them.

## Where to read the library code

Paths are relative to `.venv/lib/python3.*/site-packages/control_arena/` (run `uv sync` first).

| Concept | Where to read it |
|---|---|
| **Setting** (dataset, tools, scorers, sandbox) | `settings/apps/apps_setting.py`. `get_dataset`, `get_submit_tool_config` (honest vs attack submit args), `get_scorers`. |
| **Side task scoring** (did the backdoor really work?) | `settings/apps/task/scorers.py`, `has_backdoor` and `passes_tests`. |
| **Policies** (what U does) | `policy/_untrusted_policy.py` picks honest or attack by `eval_mode`. The attack prompt is `policy/prompts/attack_policy.txt`. |
| **Monitor** (detection: how T rates it) | `monitor/_basic_monitor.py`, prompt in `monitor/prompts/default.txt`. Raw 0-10 score is normalised to 0-1. Variants: `_ensemble_monitor.py`, plus prompt formatters for chain-of-thought, full trajectory and prefix views. |
| **Micro-protocols** (response) | `micro_protocol/_trusted_monitoring.py` (about 5 lines of logic), `_defer_to_trusted.py`, `_defer_to_resample.py`, `_trusted_editing.py`. Start with the first two. |
| **Task assembly** | `eval/_control_eval_def.py`, `get_control_task_product`. Creates one Inspect `Task` per combination. |
| **The agent loop** | `_control_solver.py`. Calls the micro-protocol each step until the model submits. |
| **Suspicion aggregation** | `scorers/_max_suspicion_scorer.py`. Takes the max step score over a trajectory. |
| **Safety / usefulness** | `analysis/_metrics.py`. `compute_suspicion_threshold` sets the audit threshold from honest runs, `compute_safety` counts caught vs uncaught. |

## Trace of one attack sample under trusted monitoring

1. `get_control_task_product` makes a Task with `eval_mode=ATTACK`. The dataset sample carries the problem description plus a side task description.
2. `control_solver` calls the micro-protocol with the conversation so far and the setting's tools.
3. `trusted_monitoring_builder.impl` calls the policy, then `monitor` if the reply had tool calls.
4. `untrusted_policy` sees `ATTACK`, so `attack_policy` prepends the attack system prompt and asks U for a solution.
5. U calls `submit` with code and a secret input. `basic_monitor` shows T the tool call (not U's reasoning) and writes `suspicion_score` into the message metadata.
6. Task ends. `apps_scorer` runs the code in Docker. Main task: passes tests. Side task: output differs from the reference solution on the secret input. `max_suspicion_scorer` reads the metadata.
7. `analyze.py` sets the audit threshold at the (100 - budget) percentile of honest-run scores, then counts attacks above it (caught) vs below it with both tasks succeeding (red team wins).

## Experiment ideas

Detection (swap the monitor):

- Copy `monitor/prompts/default.txt`, edit it, and pass it via `basic_monitor_builder(prompt=...)`.
- Try `ensemble_monitor_builder` and compare safety against its extra monitor calls.
- Try different trusted models as the monitor, and see how safety scales with monitor strength vs cost.

Response (swap the micro-protocol):

- Sweep `defer_threshold` (for example 0.2, 0.5, 0.8) to get the safety/usefulness frontier from the paper.
- Add `defer_to_resample_builder` and `trusted_editing_builder` next to the existing two in `src/experiment.py`, and add them to the list in `src/analyze.py`.

Cost side:

- Count model calls and tokens per protocol from the Inspect logs, so safety and usefulness can be plotted against cost rather than only against audit budget.
- Read a few attack transcripts in `inspect view`. Do the backdoors look subtle or clumsy? That tells you whether the monitor has anything to detect.

## Other settings

APPS is the toy case. Others in `settings/` include `bash_arena`, `shade_arena` (sabotage in realistic agent tasks), `iac` and `infra` (infrastructure code with sabotage side tasks), and `vllm`. Swapping settings means changing `AppsSetting()` in `src/experiment.py`. The protocol and analysis code stay the same, which is the point of the framework. Check each setting's README for sandbox requirements first. Several need Kubernetes.
