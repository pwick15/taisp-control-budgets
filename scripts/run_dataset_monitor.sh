#!/usr/bin/env bash
# One command: score the dataset policy's honest and backdoored solutions with one monitor,
# then run src/analyze.py on the logs.
#
#   scripts/run_dataset_monitor.sh                                    # Haiku 5.5, trusted monitoring, 500 problems
#   MONITOR=openai/gpt-6-luna scripts/run_dataset_monitor.sh          # another monitor
#   MONITOR=anthropic/claude-sonnet-5-5 PROTOCOL=untrusted_monitoring scripts/run_dataset_monitor.sh
#
# Uses the first N problems that have a verified backdoor (honest = the dataset's solution,
# attack = its backdoor), so only the monitor calls an API. Writes results/<LABEL>.csv and
# results/<LABEL>-samples.csv. Needs Docker running and the monitor's API key in .env.
# Re-running needs a new LABEL or `rm -rf logs/<LABEL>`. Needs bash (Git Bash or WSL on Windows).
#
# Env vars (all optional):
#   N                500                              problems per mode
#   MONITOR          anthropic/claude-haiku-5-5       the model that monitors
#   PROTOCOL         trusted_monitoring               or untrusted_monitoring (monitor is U), defer_to_trusted
#   STRIP_COMMENTS   1                                1 hides # comments from the monitor, 0 keeps them
#   AUDIT_BUDGETS    0.5,1,2,5,10,20,50               audit budgets (%) for analyze.py
#   LABEL            dataset-<model>-<tm|um|dtt>-n<N>[-strip]
# MAX_CONNECTIONS and MAX_SANDBOXES pass through to src/experiment.py (use MAX_CONNECTIONS=1-2 on free tiers).
set -euo pipefail
cd "$(dirname "$0")/.."

N="${N:-500}"
MONITOR="${MONITOR:-anthropic/claude-haiku-5-5}"
PROTOCOL="${PROTOCOL:-trusted_monitoring}"
STRIP_COMMENTS="${STRIP_COMMENTS:-1}"

case "$PROTOCOL" in
    trusted_monitoring)   tag=tm;  monitor_role=TRUSTED_MODEL ;;
    untrusted_monitoring) tag=um;  monitor_role=UNTRUSTED_MODEL ;;
    defer_to_trusted)     tag=dtt; monitor_role=TRUSTED_MODEL ;;
    *) echo "PROTOCOL must be trusted_monitoring, untrusted_monitoring or defer_to_trusted, got '$PROTOCOL'" >&2; exit 1 ;;
esac

short_model="$(basename "$MONITOR" | sed 's/^claude-//' | tr -d .-)"
suffix=""; [ "$STRIP_COMMENTS" = "1" ] && suffix="-strip"
LABEL="${LABEL:-dataset-${short_model}-${tag}-n${N}${suffix}}"

if [ -e "logs/$LABEL" ]; then
    echo "logs/$LABEL already exists. Pick a new LABEL or remove it." >&2
    exit 1
fi

export POLICY=dataset STRIP_COMMENTS PROTOCOLS="$PROTOCOL"
export "$monitor_role=$MONITOR" LOG_DIR="logs/$LABEL" RUN_LABEL="$LABEL"
export AUDIT_BUDGETS="${AUDIT_BUDGETS:-0.5,1,2,5,10,20,50}"

# Keep a Mac awake for the length of the run.
keep_awake=""
command -v caffeinate >/dev/null && keep_awake="caffeinate -i"

mkdir -p logs
{
    echo "== $(date) | $N problems, $PROTOCOL, monitor $MONITOR, strip comments $STRIP_COMMENTS, label $LABEL =="
    $keep_awake uv run python src/experiment.py "$N"
    $keep_awake uv run python src/analyze.py
    echo "== done $(date): results/$LABEL.csv and results/$LABEL-samples.csv =="
} 2>&1 | tee "logs/$LABEL.run.log"
