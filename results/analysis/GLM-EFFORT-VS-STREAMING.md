# GLM-5.3: is the effort ladder an effort ladder, or a serving artefact?

**Answer: it is an effort ladder.** Streaming changes generation length by 0 to 10 percent.
The effort parameter changes it eightfold. Measured 2026-11-01, 200 calls, $0.57.

## Why the question was asked

The four GLM-5.3 arms in this study do not all travel the same code path, and nothing in
the write-ups said so. Read out of the request records in the eval logs:

| arm | `stream` | `service_tier` | completion tokens, median |
|---|---|---|---|
| max (unset) | **true** | null | 3,183 |
| effort=none | **true** | null | 3,178 |
| effort=high | false | "default" | 422 |
| effort=low | false | "default" | 134 |

The two long-generating rungs were streamed and the two short ones were not, so the ladder
crosses a serving boundary exactly where the token count jumps. Served model is
byte-identical on both paths, `system_fingerprint` is null on both, and `stop_reason` is
`stop` on all 2,000 calls rather than `max_tokens`, so neither a different checkpoint nor a
cap was visible in the logs. No existing arm varies streaming at fixed effort, so the logs
could not separate the two explanations. This probe does.

## Design

50 real monitor prompts (25 honest, 25 attack) recovered from the `effort=high` run's own
logs, including resolving the log's content attachments, so the prompts are the study's
prompts rather than a reconstruction. Each was sent through `deepinfra/zai-org/GLM-5.3`
four ways: {`reasoning_effort=high`, no effort field} x {`stream` off, `stream` on}, at
temperature 0, `max_tokens` 8192. Prompt tokens were identical across all four cells
(median 1,109.5), so the cells differ only in the two variables under test.

## Result

| effort | stream | completion median | completion mean | reasoning median | truncated |
|---|---|---|---|---|---|
| high | off | 423 | 579 | 80 | 0/50 |
| high | **on** | 420 | 618 | 92 | 0/50 |
| unset | off | 3,322 | 3,541 | 2,865 | 3/50 |
| unset | **on** | 3,658 | 3,690 | 3,084 | 3/50 |

- **Streaming, at fixed effort:** 423 to 420 (-0.7%) on the high rung, 3,322 to 3,658
  (+10%) on the unset rung.
- **Effort, at fixed streaming:** 423 to 3,322 (7.9x) not streamed, 420 to 3,658 (8.7x)
  streamed.

The same holds within each arm, so it is not a honest/attack composition effect:

| effort | stream | honest median | attack median |
|---|---|---|---|
| high | off | 336 | 606 |
| high | on | 322 | 574 |
| unset | off | 1,291 | 5,246 |
| unset | on | 1,407 | 5,367 |

## What this means for the ladder

The ladder stands, and the earlier worry that it was partly a serving comparison is wrong.
Combined with the already-established fact that DeepInfra's `reasoning_effort` defaults to
**max** when omitted (commit ffe7414, verified on the live endpoint), the ordering
low < high < max(unset) is monotone and the "non-monotone effort knob" was a labelling
artefact, not a provider anomaly. The arms remain comparable with each other.

Two caveats worth carrying forward rather than discarding:

- **Streaming is not free of effect.** +10% on the long rung is small against an 8x
  lever but is not zero, and it is systematic. An arm whose cost is quoted to two
  significant figures should not mix the two paths.
- **A streamed call reports no cost.** Every streamed cell above returned
  `estimated_cost: 0` from the proxy, while the non-streamed cells returned real figures
  that match this repo's price table to ratio 1.000. So the provider's own cost field,
  which is the best available ground truth for a proxied model, is unavailable for exactly
  the runs that used streaming. Those runs must be costed from token counts and the price
  table, never from the reported cost, or they read as free.

## Reproducing

    python scripts/probe_glm_effort_vs_streaming.py full

Prompts are extracted from `logs/dataset-glm53-efforthigh-tm-n500-strip`, so the raw logs
must be present. 200 calls, about 25 minutes at concurrency 5.
