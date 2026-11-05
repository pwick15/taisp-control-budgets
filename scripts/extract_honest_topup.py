"""Per-sample scores from an honest-only top-up, into results/honest-topup/.

    uv run python scripts/extract_honest_topup.py logs/<label>

Why not src/analyze.py. That script's job is safety against an audit budget, which needs
both arms: with no attack rows the denominator is empty, and ControlArena's
`compute_safety` returns 1.0 from an empty denominator rather than failing. A one-sided arm
has no safety number and must not be given one.

Writes results/honest-topup/<label>-samples.csv with the same columns as a run's samples
file, so it can be concatenated onto the arm it extends. It lands in honest-topup/ and not
results/, because every analysis script globs `results/*-samples.csv` and a one-sided arm in
that glob would be read as a run with 500 honest and 0 attack samples.
"""
import csv
import glob
import sys
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import read_eval_log

OUT = Path("results/honest-topup")
FIELDS = ("reasoning_tokens", "output_tokens", "input_tokens",
          "input_tokens_cache_write", "input_tokens_cache_read")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    log_dir = Path(sys.argv[1])
    label = log_dir.name
    rows = []
    for proto in sorted(p for p in log_dir.iterdir() if p.is_dir()):
        for f in sorted(glob.glob(str(proto / "*.eval"))):
            log = read_eval_log(f)
            for smp in (log.samples or []):
                md = smp.metadata or {}
                mode = md.get("eval_mode")
                if mode != "honest":
                    sys.exit(f"{f} carries a {mode!r} sample; this extractor is honest-only")
                score = None
                for key, sc in (smp.scores or {}).items():
                    if "suspicion" in key:
                        try:
                            score = float(sc.value)
                        except (TypeError, ValueError):
                            score = None
                        break
                tot: dict[str, int] = defaultdict(int)
                for ev in smp.events:
                    if getattr(ev, "event", None) != "model":
                        continue
                    u = getattr(getattr(ev, "output", None), "usage", None)
                    if u is None:
                        continue
                    for k in FIELDS:
                        tot[k] += int(getattr(u, k, 0) or 0)
                rows.append({"run": label, "protocol": proto.name, "mode": "honest",
                             "sample_id": str(smp.id), "suspicion": score,
                             "reasoning_tokens": tot["reasoning_tokens"]})
    if not rows:
        sys.exit(f"no samples found under {log_dir}")
    ids = [r["sample_id"] for r in rows]
    if len(set(ids)) != len(ids):
        sys.exit(f"{len(ids) - len(set(ids))} duplicate sample ids; refusing to write")
    unscored = sum(1 for r in rows if r["suspicion"] is None)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{label}-samples.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path}: {len(rows)} honest samples, {unscored} without a score")
    if unscored:
        print("  An unscored honest row is a missing threshold observation, not a neutral "
              "one, so the top-up is incomplete until it is zero.")


if __name__ == "__main__":
    main()
