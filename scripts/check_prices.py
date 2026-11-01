"""Check PRICES against the provider's own per-call cost, recorded in the eval logs.

    uv run python scripts/check_prices.py [samples_per_run]

litellm returns an `estimated_cost` field in each response's usage block for the models it
routes to DeepInfra. That is the best ground truth available for what a call cost, because
it is the provider's own arithmetic rather than ours. This recomputes each call from the
PRICES table and reports the ratio; anything that is not 1.00 means the table is wrong.

Coverage is partial by nature, and the gaps are worth knowing:

  reports a per-call cost   DeepInfra-routed models (GLM-5.3, both Gemma 3 sizes)
  does not                  Anthropic and Google-direct calls, and the OpenAI-routed
                            models, which return no such field at all
  returns zero              any STREAMED call, so a streamed arm cannot be checked this
                            way and must be costed from token counts

So a pass here is strong evidence for the models it covers and says nothing about the rest.
Prices for the uncovered models are taken from the serving proxy's own rate card.
"""
import sys
from pathlib import Path

sys.path.insert(0, "src")
from analyze import PRICES  # noqa: E402
from inspect_ai.log import list_eval_logs, read_eval_log  # noqa: E402

PER_RUN = int(sys.argv[1]) if len(sys.argv) > 1 else 12


def main() -> int:
    runs = sorted(p.name for p in Path("logs").iterdir() if p.is_dir())
    print(f"{'run':52s} {'model':46s} {'n':>4s} {'provider$':>11s} "
          f"{'ours$':>11s} {'ratio':>7s}")
    worst = 1.0
    checked = 0
    for run in runs:
        for proto in sorted(x for x in (Path("logs") / run).iterdir() if x.is_dir()):
            rep = ours = 0.0
            n = 0
            model = None
            for entry in list_eval_logs(str(proto)):
                log = read_eval_log(entry.name)
                for smp in (log.samples or [])[:PER_RUN]:
                    for ev in smp.events:
                        if getattr(ev, "event", None) != "model" or not getattr(ev, "call", None):
                            continue
                        if getattr(ev, "cache", None) == "read":
                            continue
                        usage = (ev.call.response or {}).get("usage") or {}
                        stated = usage.get("estimated_cost")
                        price = PRICES.get(ev.model)
                        if stated is None or price is None:
                            continue
                        model = ev.model
                        detail = usage.get("prompt_tokens_details") or {}
                        cached = detail.get("cached_tokens") or 0
                        written = detail.get("cache_write_tokens") or 0
                        fresh = max((usage.get("prompt_tokens") or 0) - cached - written, 0)
                        out = usage.get("completion_tokens") or 0
                        rep += stated
                        ours += (fresh * price[0] + out * price[1]
                                 + written * price[2] + cached * price[3]) / 1e6
                        n += 1
                        break
            if n and rep:
                ratio = ours / rep
                worst = max(worst, ratio, 1 / ratio)
                checked += 1
                print(f"{run:52s} {model:46s} {n:4d} {rep:11.6f} {ours:11.6f} {ratio:7.3f}")
    print(f"\n{checked} run(s) carried a provider cost. Worst deviation from 1.000: "
          f"{worst:.3f}")
    if worst > 1.01:
        print("FAIL: a price in the table disagrees with the provider by more than 1%")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
