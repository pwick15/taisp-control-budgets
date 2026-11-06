"""Paired test of a new monitor on backdoors that no existing monitor caught.

    N=5 uv run python blog/results-figures/opus_subset.py build      # free
    TRAJ_DIR=trajectories/hard-subset MONITOR_MODEL=anthropic/claude-opus-5-5 STRIP_COMMENTS=1 \
      LOG_DIR=logs/hard-subset-opus55-strip uv run python src/monitor.py   # costs money
    uv run python blog/results-figures/opus_subset.py report logs/hard-subset-opus55-strip   # free

`build` copies the first N problems of PICKS (backdoored and honest version of each) out of the
Haiku 5.5 dataset logs into trajectories/hard-subset/untrusted/, with the old monitor's scores and
usage removed, so src/monitor.py treats them as fresh trajectories.

`report` prints, per problem, the new monitor's score on the backdoor and on its honest twin next to
Sonnet 5.5's and Haiku 5.5 xhigh's, and the new monitor's stated reason for each backdoor.
"""
from __future__ import annotations

import glob
import os
import sys
from pathlib import Path

import pandas as pd
from inspect_ai.log import read_eval_log, write_eval_log

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "logs" / "dataset-haiku55-tm-n500-strip" / "trusted_monitoring"
OUT = ROOT / "trajectories" / "hard-subset" / "untrusted"
MONITOR_KEYS = ("suspicion_score", "reason", "model_usage")

# 20 of the 49 never-caught backdoors, four per pattern, interleaved so any first N covers every pattern.
PICKS = [
    "86", "412", "934", "832", "1081",      # boundary flip, loop cap, extra rule, core logic, unclear
    "1151", "396", "725", "790", "949",
    "977", "52", "170", "279", "342",
    "132", "88", "1073", "255", "788",
]


def build(n: int) -> None:
    ids = set(PICKS[:n])
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.eval"):
        old.unlink()
    for path in glob.glob(str(SRC / "*.eval")):
        log = read_eval_log(path)
        keep = [s for s in log.samples if str(s.id) in ids]
        for s in keep:
            for m in s.messages:
                if m.metadata:
                    for k in MONITOR_KEYS:
                        m.metadata.pop(k, None)
            s.scores = {k: v for k, v in (s.scores or {}).items() if k != "max_suspicion_scorer"}
            s.model_usage = {}
        log.samples = keep
        if log.results:
            log.results.total_samples = log.results.completed_samples = len(keep)
        out = OUT / Path(path).name
        log.location = str(out)
        write_eval_log(log, str(out))
        print(f"{out.name}: {len(keep)} samples")
    print(f"\nNext: TRAJ_DIR={OUT.parent.relative_to(ROOT)} MONITOR_MODEL=anthropic/claude-opus-5-5 STRIP_COMMENTS=1 "
          f"LOG_DIR=logs/hard-subset-opus55-strip uv run python src/monitor.py")


def report(log_dir: str) -> None:
    rows, reasons, tok_in, tok_out = [], {}, 0, 0
    for path in glob.glob(str(Path(log_dir) / "**" / "*.eval"), recursive=True):
        log = read_eval_log(path)
        mode = "attack" if "attack" in Path(path).name else "honest"
        for s in log.samples:
            score = s.scores["max_suspicion_scorer"].value if "max_suspicion_scorer" in (s.scores or {}) else None
            rows.append({"sample_id": str(s.id), "mode": mode, "new": score})
            for m in s.messages:
                if m.metadata and "reason" in m.metadata and mode == "attack":
                    reasons[str(s.id)] = m.metadata["reason"]
            for u in (s.model_usage or {}).values():
                tok_in += (u.input_tokens or 0) + (u.input_tokens_cache_write or 0) + (u.input_tokens_cache_read or 0)
                tok_out += u.output_tokens or 0
    # Opus 5.5 list price, $4 in / $20 out per million tokens (output includes thinking).
    print(f"tokens: {tok_in:,} in, {tok_out:,} out; about ${(4 * tok_in + 20 * tok_out) / 1e6:.2f} at Opus 5.5 list price\n")
    new = pd.DataFrame(rows).pivot(index="sample_id", columns="mode", values="new")

    def old(run):
        df = pd.read_csv(ROOT / "results" / f"{run}-samples.csv")
        df["sample_id"] = df.sample_id.astype(str)
        return df.pivot(index="sample_id", columns="mode", values="suspicion")

    son, hai = old("dataset500-sonnet55-um-strip"), old("dataset-haiku55-effortxhigh-tm-n500-strip")
    out = pd.DataFrame({
        "new_backdoor": new["attack"], "new_honest": new["honest"],
        "sonnet_backdoor": son.loc[new.index, "attack"], "sonnet_honest": son.loc[new.index, "honest"],
        "haiku_x_backdoor": hai.loc[new.index, "attack"], "haiku_x_honest": hai.loc[new.index, "honest"],
    })
    pd.set_option("display.width", 160)
    print(out.to_string())
    for who in ("new", "sonnet", "haiku_x"):
        above = (out[f"{who}_backdoor"] > out[f"{who}_honest"]).sum()
        tie = (out[f"{who}_backdoor"] == out[f"{who}_honest"]).sum()
        print(f"{who:8s}: backdoor scored above its honest twin in {above} of {len(out)} problems ({tie} ties)")
    print("\nNew monitor's reasons on the backdoors (check whether it names the planted line):")
    for sid, r in reasons.items():
        print(f"\n--- {sid} (score {out.loc[sid, 'new_backdoor']})\n{str(r)[:1200]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "build"
    if cmd == "build":
        build(int(os.getenv("N", "20")))
    elif cmd == "report":
        report(sys.argv[2])
    else:
        sys.exit(__doc__)
