#!/usr/bin/env bash
# Score MORE honest samples for an arm that already exists, and nothing else.
#
#   LABEL=<arm>-honest-topup IDS=<ids.json> MONITOR=... PROTOCOL=... \
#     [MONITOR_REASONING=xhigh] scripts/run_honest_topup.sh
#
# Why only the honest side. Every audit threshold in this study is a percentile of the
# HONEST score distribution, so the number of operating points a comparison can stand on is
# set by how many honest rows sit above the cutoff. Buying attack samples does not move that
# at all, and the attack pool is capped at 1,061 paired problems anyway. Measured by
# resampling the real honest distributions: doubling the honest arm takes the Sonnet against
# Haiku interval at a 0.5% budget from [-0.634, +0.800] to [+0.043, +0.586], which is the
# difference between a comparison that spans zero and one that does not.
#
# This does NOT produce a run. A run is 500 honest and 500 attack, both scored, and
# results/ enforces that. The output is a one-sided top-up and lands in
# results/honest-topup/, which no analysis script globs. src/analyze.py is deliberately not
# called: with no attack rows its safety figure has an empty denominator, and
# `compute_safety` returns 1.0 from an empty denominator rather than failing.
set -euo pipefail
cd "$(dirname "$0")/.."

: "${LABEL:?set LABEL, e.g. dataset-haiku55-xhigh-scale100-n500-strip-honest-topup}"
: "${IDS:?set IDS to a JSON file holding the sample ids to score}"
MONITOR="${MONITOR:?set MONITOR to the model that scores}"
PROTOCOL="${PROTOCOL:-trusted_monitoring}"
STRIP_COMMENTS="${STRIP_COMMENTS:-1}"

case "$PROTOCOL" in
    trusted_monitoring)   monitor_role=TRUSTED_MODEL ;;
    untrusted_monitoring) monitor_role=UNTRUSTED_MODEL ;;
    *) echo "PROTOCOL must be trusted_monitoring or untrusted_monitoring, got '$PROTOCOL'" >&2
       exit 1 ;;
esac

if [ -e "logs/$LABEL" ]; then
    echo "logs/$LABEL already exists. Pick a new LABEL or remove it." >&2
    exit 1
fi

n_ids="$(python3 -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$IDS")"

export POLICY=dataset STRIP_COMMENTS PROTOCOLS="$PROTOCOL"
export "$monitor_role=$MONITOR" LOG_DIR="logs/$LABEL" RUN_LABEL="$LABEL"
export MODES=honest SAMPLE_IDS="$IDS"

mkdir -p logs results/honest-topup
{
    echo "== $(date) | HONEST-ONLY top-up: $n_ids named ids, $PROTOCOL, monitor $MONITOR, "\
"strip comments $STRIP_COMMENTS, label $LABEL =="
    uv run python src/experiment.py "$n_ids"
    echo "== done $(date): logs/$LABEL, extract with scripts/extract_honest_topup.py =="
} 2>&1 | tee "logs/$LABEL.run.log"
