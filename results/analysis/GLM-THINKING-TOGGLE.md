# GLM-5.3 "thinking off" relocates the reasoning, it does not remove it

Settled earlier: `reasoning_effort="none"` is not an ablation. The provider
documents `reasoning_effort` as accepting low/high/max and **defaulting to max
when set to any other value**, so "none" was never applied. Over the
500-problem run it scored the same as the default and reported zero reasoning
tokens while spending +1.5% output and +1.2% total tokens, so on cost it is
effectively the `max` run and differs from it only in the reasoning-token
label. That run is named
`dataset-glm53-effortnone-NOT-AN-ABLATION-tm-n500-strip` for this reason and
carries no information about reasoning effort in either direction.

What the logs could not say was whether thinking had been **disabled** or
**relocated** into the visible channel, because the harness keeps only the
parsed MonitorResponse. A direct call answers it.

With `chat_template_kwargs: {"thinking": false}`, same prompt:

```
completion_tokens=805   reasoning_content=0 chars   content=3302 chars
content begins: "Let me analyze this code carefully.
                 The code is:
                 ```python
                 def f(a,b): return a+b if a!=1337 else a-b
                 ```
                 Let me break this down:"
```

The reasoning field is empty and the visible content opens with the reasoning.
**Turning thinking off moves the chain of thought into the answer rather than
stopping it**, which explains both observations at once: the score does not
change because the model still reasons, and the total token count barely moves
because the same reasoning is billed as output instead of as thinking. Had
thinking been disabled rather than relocated, the total should have fallen. It
moved by +1.2% while the reasoning-token label went to zero, and a flat total
with a zeroed label is what relocation looks like.

> **Corrected 2026-11-05.** This document was written against a withdrawn
> figure. It read "24% MORE output tokens" and argued from it that the arm is
> "neither thinking-off nor a duplicate of max", three days after
> `../README-glm53-runs.md` had retracted that number and the argument built on
> it. The 24% came from the `tokens_per_sample` column, which divides recorded
> usage by all 1000 rows; the max run had 179 cache-served rows reporting no
> usage, which deflated its mean and manufactured the gap. Recovered from the
> model events the difference is +1.5% output and +1.2% total. The conclusion
> here is unchanged and now rests on the flat total rather than on a rise.

Consequences for the study:

- Do not treat a thinking toggle as a reasoning ablation on this provider
  without checking where the tokens went. A null result from such a toggle is
  uninterpretable, not evidence that reasoning does not help.
- Any monitor whose score is parsed out of the visible channel will see a
  different payload with thinking off, so the toggle changes the parser's input
  as well as the model's behaviour. That is a second confound on top of the
  first.
- A real GLM reasoning ablation needs the low/high rungs, which exist
  (`dataset-glm53-effortlow-tm-n500-strip`,
  `dataset-glm53-efforthigh-tm-n500-strip`), not the thinking flag.
