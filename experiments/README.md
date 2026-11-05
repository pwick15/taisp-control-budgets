# Experiments

One directory per experiment. Each is self-contained and **entirely generated**
from eval logs, so it can be deleted and rebuilt rather than maintained by hand.

```
experiments/<experiment-name>/
  REPORT.md        the narrative: what was measured, what it means, what to do
  data/
    samples.csv    one tidy row per sample. The starting point for new analysis
    summary.json   the same headline numbers, machine-readable
  figures/*.png    the figures REPORT.md embeds
```

## Why the results are committed but the logs are not

Inspect's `.eval` logs are large, and `logs*/` stays gitignored. What is
committed is the derived material: a tidy CSV, a JSON summary and the figures.
Those are small, they diff meaningfully, and they are enough to check a claim or
start a new analysis without re-running anything. `.gitignore` carries an
exception so `experiments/**/*.png` is tracked while `*.png` elsewhere is not.

Raw logs are reproducible from the command recorded at the bottom of each
report, together with the commit the report was generated at.

## Adding a run

```bash
MONITOR_ARM=baseline LOG_DIR=logs/e0 uv run python src/e0_run.py 200
uv run python src/e0_report.py experiments/e0-monitor-resolution baseline=logs/e0
```

The report generator takes any number of arms and compares them in one document:

```bash
uv run python src/e0_report.py experiments/e0-monitor-resolution \
    baseline=logs/e0 range100=logs/e0r-range100
```

Never hand-edit a generated `REPORT.md`. If the narrative is wrong, the fix
belongs in `src/e0_report.py`, so the next regeneration keeps it.

## Reading `data/samples.csv`

| column | meaning |
|---|---|
| `arm` | which monitor variant produced the score |
| `sample_id` | APPS problem id; joins to the dataset |
| `eval_mode` | `honest` (clean reference solution) or `attack` (stored backdoor) |
| `suspicion` | monitor score, normalised to 0-1 |
| `main_task_success` | the submitted code passes the tests |
| `side_task_success` | the backdoor actually triggers |
| `attack_succeeded` | both of the above: the only rows that count as attacks |
| `backdoor_generator` | the model that wrote the backdoor, for attack rows |
| `input_tokens`, `output_tokens` | monitor usage; in these runs the policy makes no model calls, so sample usage is monitor usage exactly |

## Current experiments

| directory | what it answers |
|---|---|
| `e0-monitor-resolution/` | How much of the budget axis actually exists, and what the monitor's score resolution costs you |
