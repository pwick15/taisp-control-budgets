# Figure style

The look we're after: calm, precise and modern. Light marks on a quiet background, one clear point per
figure, colour used for meaning. A reader should get the finding in five seconds and trust the numbers
after thirty. `python -m viz check` enforces the measurable parts of this page; the rest is judgement,
which is why every figure gets looked at in both themes before it's done.

## One finding per figure

- The **title** states the finding as a claim ("Price is a poor guide to monitoring skill"), not the
  topic ("Cost vs safety"). If you can't write that sentence, the figure isn't ready.
- The **caption** says what is plotted and how to read it, in one or two sentences: what a mark is, what
  up and right mean, what any band or shading is.
- Everything else (caveats, method choices, things to confirm) goes in `notes`, which the gallery folds away.
- The chart carries only what the eye needs while looking: axis names, tick labels, names next to the
  marks that matter, and at most a few short annotations. Each piece of text is 8 words or fewer.

Fewer words is the default. Before adding any text to a chart, try deleting it; keep it only if the
figure stops making sense.

## Colour

Colour carries meaning, and a figure uses at most three colours plus grey.

- **Highlight, then grey.** The models or groups the finding is about get colour; everything else is
  `@context` (lines, fills) or `@context-strong` (small markers), with its name in `@ink-muted`.
- **Each model keeps its colour everywhere**: Sonnet 5.5 `@s0` blue, Haiku 5.5 `@s1` orange (Haiku 4.5 the
  same orange, drawn hollow), GLM-5.3 `@s2` aqua, Opus 5.5 `@s6` violet. Use `entity("sonnet55")` from
  `viz.kit` rather than repeating these. A reader who learns "blue is Sonnet" once can read every figure.
- **Categories without a model** use `@s0`, `@s1`, `@s2` in that order (the order is what makes them
  colour-blind safe), never past three in a scatter.
- **Outcomes** read bad to fine: `@s7` red for the outcome the finding is about (missed by every monitor),
  `@warning/0.6` soft amber for partial, `@context` grey for the rest. The worst case is the only loud colour.
- **Tables** use scale tokens: `@goodbad:x` (x from 0 = worst of every setting we ran to 1 = best) or
  `@seq:x` for plain magnitude. The number is always printed in the cell, so colour never stands alone.
- **Text on a fill** uses `@on-strong` (white, on blue, violet, red), `@on-bright` (dark, on amber and
  aqua) or `@on-pale` (on grey and scale cells). Text elsewhere uses `@ink-primary`, `@ink-secondary` or
  `@ink-muted`, never a series colour.
- **Background tint** is allowed when a direction is better: P01 tints the top-left corner `@good/0.11`
  and the bottom-right `@s7/0.09`, plus a muted "↖ better". Keep tints that faint.

Dark mode comes free with tokens, but look at it: a colour that works on cream can sink on charcoal.

## Type

The theme sets Inter everywhere (bundled, so exports match on every machine). Sizes come from one scale:
11 and 12 for ticks, legends and secondary labels; 13 for row labels and names that matter; 18 for
numbers inside table cells; 24 and 28 for a hero number. Weight 600 marks the names and numbers the
finding is about; everything else is regular.

## Marks

- Lines 2 px (2.5 for the highlighted ones, 1.5 for context); markers 7 to 10 px with a 1.5 px surface ring.
- Bars and blocks have rounded data ends (4 to 6 px) and a 2 px surface gap between segments.
- Uncertainty is a soft band (`charts.BAND`) or a soft vertical bar behind the marker (`charts.VBAR`),
  never error-bar whiskers.
- Gridlines are solid hairlines and the y-axis line is hidden; the theme does both. Dashed lines mean a
  threshold or a reference (a budget, zero, the best-buys frontier), nothing else.
- One y-scale per panel. Two measures with different units become two panels (P05), never two axes on one.

## Layout

- Exports are 960 px wide at 2x, light or dark depending on the gallery's theme, with the title and
  caption left out so they paste cleanly into the doc.
- Name the marks directly (`label`, `endLabel`) when there are four series or fewer; use a legend
  (top-left) for more, and keep it to eight entries.
- Long category labels: let the grid fit them (`containLabel`, as `charts.partition_bars` does) rather
  than guessing a margin.
- Every data item can carry a `tip` (HTML) for its tooltip: the exact numbers, intervals and cost.
- A **dial** (buttons above the chart) switches one parameter, usually the audit budget. Default it to
  the value the text discusses (2%).

## Choosing a form

| The finding is about | Use | Worked example |
| --- | --- | --- |
| a trade-off between two measures | scatter, highlighted models in colour, the rest grey | P01 |
| a few numbers compared against the whole field | colour table (`charts.heat_table`) | P02, P06 |
| change across ordered settings | lines, one per model, names at the line ends | P03 |
| how parts of a group split | 100% bars (`charts.partition_bars`), with the 95% range | P10, P11, P12 |
| a curve plus a difference | two stacked panels sharing the x-axis | P05 |
| counts at each score | histogram on a log scale | P14 |
| individual units | one square per unit (`renderItem`) | P07 |
| a matrix with gaps | custom cells (`renderItem`) | P04 |

Copy the worked example's `figure.py` and change the data; that's faster and keeps figures consistent.

## Before calling it done

Look at each PNG `python -m viz check` saved and ask:

- Does the title's claim jump out without reading the caption?
- Is every piece of text readable, unclipped and clear of other text, in light and in dark?
- Are only the things the finding is about in colour?
- Would the figure still make sense pasted alone into the doc, with its caption under it?
