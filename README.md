# AI control: cost-benefit analysis of control protocols

Built on [ControlArena](https://github.com/UKGovernmentBEIS/control-arena) (UK AISI / Redwood) and [Inspect](https://inspect.aisi.org.uk/). The starting point is a small replication of [AI Control: Improving Safety Despite Intentional Subversion](https://arxiv.org/abs/2312.06942) (Greenblatt et al.) on the APPS coding setting.

## Project goals

Run a cost-benefit analysis of AI control protocols to find:

1. **Detection:** which methods are best at spotting an untrusted model that is misbehaving (monitors, prompts, ensembles, which trusted model does the monitoring).
2. **Response:** which methods are best at acting on a detection (audit, defer to trusted, resample, trusted editing).

In ControlArena terms, detection is the **monitor** and response is the **micro-protocol**. Each one trades **safety** (how often backdoors are caught) against **usefulness** (how many tasks still get solved) and against **cost** (extra model calls, human audit budget).

## Setup

You need:

- [uv](https://docs.astral.sh/uv/getting-started/installation/) (manages Python 3.12+ and the virtualenv for you)
- [Docker](https://docs.docker.com/get-docker/), running. The APPS setting scores code inside a container.
- An Anthropic API key (and an OpenAI key only if you switch a model to OpenAI)

```bash
git clone <repo-url> && cd controlarena
uv sync                         # creates .venv and installs the locked dependencies
cp .env.example .env            # then fill in ANTHROPIC_API_KEY
```

`.env` is gitignored. Never commit it. Inspect loads it automatically from the working directory, so run commands from the repo root.

### Check your setup (no API cost)

Point both models at Inspect's mock model. This exercises the whole pipeline (dataset download, Docker sandbox, scoring) without calling any API:

```bash
UNTRUSTED_MODEL=mockllm/model TRUSTED_MODEL=mockllm/model LOG_DIR=/tmp/mock-logs \
  uv run python src/experiment.py 1
```

The scores will be all zero, since the mock model solves nothing. You are only checking that it runs to completion. The first run is slower because it pulls the Docker image and downloads the dataset.

## Running experiments

```bash
uv run python src/experiment.py 5      # smoke run: 5 problems x 2 modes x 2 protocols
uv run python src/analyze.py           # usefulness, safety table, saves safety_vs_audit_budget.png
uv run inspect view --log-dir logs     # browse full transcripts in the browser
```

`experiment.py` takes the problem count as its only argument. Cost scales as problems x 4 runs, plus one trusted-model monitor call per step.

5 problems is only a plumbing check, since each attack is close to a coin flip at that size. Use 50 or more for any number you plan to quote.

### Running on free API tiers

Google AI Studio and Mistral (Experiment plan) have free tiers with no credit card. Put the key in `.env` (see `.env.example`) and pick models by prefix, for example:

```bash
UNTRUSTED_MODEL=google/gemini-2.5-flash TRUSTED_MODEL=mistral/ministral-8b-latest \
  PROTOCOLS=trusted_monitoring MAX_CONNECTIONS=1 MAX_SANDBOXES=2 LOG_DIR=logs/gemini-ministral-tm \
  uv run python src/experiment.py 20
LOG_DIR=logs/gemini-ministral-tm uv run python src/analyze.py
```

U and T can come from different providers, as above. A Google-only pair also works, e.g. `google/gemini-3.5-flash` as U and `google/gemini-3.5-flash-lite` as T. On the Mistral free tier, `mistral-large-latest` is not available and `mistral-small-latest` was rate-limited in testing; the Ministral models work. Free tiers cap requests per minute and per day, so keep `MAX_CONNECTIONS` low. Models must support tool calling, because the APPS setting submits code through a `submit` tool. Model IDs change, so check each provider's model list first.

### Configuration

All optional, set in `.env` or the shell:

| Variable | Default | Meaning |
|---|---|---|
| `UNTRUSTED_MODEL` | `anthropic/claude-sonnet-5-5` | Strong model U, which may attack |
| `TRUSTED_MODEL` | `anthropic/claude-haiku-4-5-20251001` | Weak model T, which monitors and acts as fallback |
| `LOG_DIR` | `logs` | Where eval logs go. Read by both scripts, so set it for both. |
| `PROTOCOLS` | all | Comma-separated subset to run or analyse, e.g. `trusted_monitoring` |
| `MAX_CONNECTIONS` | `10` | Max concurrent API calls per model. Use 1-2 on free tiers. |
| `MAX_SANDBOXES` | `10` | Max concurrent Docker sandboxes |
| `POLICY` | `model` | `model`: U writes the code. `dataset`: use the dataset's known-good solutions and verified backdoors instead of U, so only the monitor calls an API. For testing the monitor when U can't write working backdoors; usefulness is meaningless in this mode. |
| `AUDIT_BUDGETS` | `0.5,1,2,5,10,20,50` | Audit budgets (%) that `analyze.py` evaluates |
| `RUN_LABEL` | `LOG_DIR` folder name | Name of the results CSV written to `results/` |

Logs (`logs*/`) and plots (`*.png`) are gitignored. They are large and reproducible. To share results, share the numbers and the command that produced them, not the files. `analyze.py` writes the numbers to `results/<RUN_LABEL>.csv`, which is small enough to commit.

## Repo layout

| Path | What it does |
|---|---|
| `src/experiment.py` | Builds the tasks (setting x protocol x honest/attack) and runs them through Inspect. Writes one log subdirectory per protocol. |
| `src/analyze.py` | Loads the logs into a DataFrame, computes usefulness and safety, plots safety vs audit budget. |
| `docs/codebase-guide.md` | Where things live in the ControlArena library, a trace of one attack sample, and experiment ideas. |
| `pyproject.toml`, `uv.lock` | Dependencies. Use `uv add <pkg>` so the lockfile stays in sync. |

## Metrics

- **Usefulness:** fraction of honest-mode runs that solve the problem.
- **Safety:** caught / (caught + uncaught successful backdoors) at a given audit budget. The audit budget is the percentage of honest runs a human can afford to review. The audit threshold is set from the honest-run suspicion scores.

## Protocols currently wired up

- **trusted monitoring:** U acts, T scores it, humans audit the top X% of scores. Nothing is blocked.
- **defer to trusted:** same, but any action scoring above `defer_threshold` (0.5, an untuned guess) is discarded and T writes the code instead. Safer, but T is weaker, so fewer problems get solved.

ControlArena also ships `defer_to_resample` and `trusted_editing` micro-protocols, and `ensemble_monitor_builder` for detection. See `docs/codebase-guide.md`.

## Working on this together

- Work on a branch and open a PR. Keep commits small and scoped to one change (for example "add resample protocol" or "sweep defer threshold").
- When you add an experiment, keep the knobs (models, thresholds, prompts) in one place at the top of the script or in env vars, so results can be reproduced from the commit.
- Put the exact command and problem count next to any number you report.

## Troubleshooting

- **`docker` errors or sandbox failures:** start Docker Desktop and retry.
- **Auth errors:** check `ANTHROPIC_API_KEY` is set in `.env` and that you run from the repo root.
- **Rate limits or high cost:** lower the problem count, or lower `max_sandboxes` in `src/experiment.py`.
- **Some other setting needs more than Docker:** several settings (`iac`, `infra`, ...) need Kubernetes. Read the setting's README in the library before switching.
