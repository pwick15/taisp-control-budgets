"""Write viz/data/token-bill.csv: what each monitor run's token bill is made of.

Splits a run's spend into the five things you actually pay for, priced with the same table
src/analyze.py uses: fresh input, cache writes, cache reads, the output you can read, and the
hidden reasoning you cannot. Figures quote dollars per 1,000,000 samples so runs of different
sizes sit on one axis.

This reads the gitignored eval logs, which only some of us have, so its output is committed
and M20 reads that instead. Rerun it when a run is added or its usage is recovered:

    uv run python viz/data/derive_token_bill.py
"""
from __future__ import annotations

import csv
import glob
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from analyze import PRICES  # noqa: E402
from inspect_ai.log import read_eval_log  # noqa: E402

OUT = Path(__file__).resolve().parent / "token-bill.csv"
PER = 1_000_000  # dollars are quoted per this many samples


def main() -> None:
    rows, skipped = [], []
    for d in sorted(p for p in (ROOT / "logs").iterdir() if p.is_dir()):
        tot: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        n_samples = 0
        for path in sorted(glob.glob(str(d / "*" / "*.eval"))):
            try:
                log = read_eval_log(path)
            except Exception:
                continue
            for s in log.samples or []:
                n_samples += 1
                for ev in (s.events or []):
                    if getattr(ev, "event", None) != "model":
                        continue
                    out = getattr(ev, "output", None)
                    u = getattr(out, "usage", None) if out else None
                    if u is None:
                        continue
                    t = tot[str(getattr(ev, "model", "") or "")]
                    for f in ("input_tokens", "output_tokens", "input_tokens_cache_write",
                              "input_tokens_cache_read", "reasoning_tokens"):
                        t[f] += int(getattr(u, f, 0) or 0)
        if not n_samples or not tot:
            continue
        model = max(tot, key=lambda m: sum(tot[m].values()))
        price = PRICES.get(model)
        if price is None:
            skipped.append((d.name, model))
            continue
        p_in, p_out, p_cw, p_cr = price
        t = tot[model]
        visible = max(t["output_tokens"] - t["reasoning_tokens"], 0)
        scale = PER / n_samples / 1e6
        rows.append({
            "run": d.name, "model": model, "n_samples": n_samples,
            "usd_input": round(t["input_tokens"] * p_in * scale, 2),
            "usd_cache_write": round(t["input_tokens_cache_write"] * p_cw * scale, 2),
            "usd_cache_read": round(t["input_tokens_cache_read"] * p_cr * scale, 2),
            "usd_visible_output": round(visible * p_out * scale, 2),
            "usd_hidden_reasoning": round(t["reasoning_tokens"] * p_out * scale, 2),
        })
    rows.sort(key=lambda r: r["run"])
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(rows)} run(s)")
    for name, model in skipped:
        print(f"  skipped {name}: no price for {model!r}")


if __name__ == "__main__":
    main()
