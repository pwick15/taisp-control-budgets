# Control dataset explorer: build

Builds `../web/explorer.html`, a single self-contained static page with three
interactive lenses over every in-scope run's raw per-sample scores. Offline, no
runtime fetches. It is the site's **Data deep dive** door: Cloudflare Pages serves
`web/` on push to main, so commit `web/explorer.html` alongside the source here.
The door link lives in the `LINKS` block of `landing/template.html`
(`deepDive: "explorer.html"`); rebuild the landing page after changing it.

## Build

    python explorer/build.py            # -> web/explorer.html
    python explorer/build.py --bundle   # also dump explorer/bundle.json (needed by the gates)

(run with the repo venv, e.g. `.venv/bin/python explorer/build.py`.)

`build.py` is the only data code. It reads the committed `results/*-samples.csv`
and `results/analysis/safety-with-ci.csv` from this repo, recomputes the budget
ladder from the per-sample scores, and inlines ECharts 5.5.1 (vendored in
`vendor/`), the data bundle, the stylesheet and the two scripts into one HTML
file. It does not import the data-exploration page's `lib/data.py` (that loader
needs a session-scoped token table); the run registry and the ladder are copied so
this page rebuilds on its own from `results/`.

## Drill-down detail

Clicking a ringed backdoor (or a featured card) pins it; the pinned card then
offers a **Deep dive** that opens a drawer with the original problem, the
honest-vs-backdoor code (a line diff when the two overlap, otherwise the backdoor
shown plainly with the honest reference below), the secret input that triggers the
bug, the outcome, the field difficulty, and the monitor's own reasoning.

That detail comes from the inspect_ai `.eval` logs, which are big and gitignored,
so it is extracted once into a committed `detail.json`:

    python explorer/extract_detail.py    # reads trajectories/*.eval -> detail.json

`build.py` inlines `detail.json` when present and degrades gracefully (no drawer)
when it is absent, so the page still builds without the 2.3 GB of trajectories.
Re-run the extractor only when the trajectories or the auditor's-read set change.
The remaining follow-on (a custom sample-level query panel) is in `DRILLDOWN-PLAN.md`.

## Files

| path | what |
|---|---|
| `build.py` | data layer + HTML assembly (writes `../web/explorer.html`) |
| `extract_detail.py`, `detail.json` | drill-down extractor (reads `.eval` logs) + its committed output |
| `lenses.js` | the three chart-option builders, pure (no DOM, no echarts calls) so they render headlessly |
| `app.js` | DOM: tabs, filter bar, per-lens toolbars, detail panel, Atlas interactions, featured strip, theme, events |
| `styles.css`, `shell.html` | page chrome; palette mirrors the data-exploration page |
| `vendor/echarts-5.5.1.min.js` | the charting library, inlined at build time |
| `ssr.mjs`, `dom_smoke.mjs` | the two gates |
| `DRILLDOWN-PLAN.md` | scoped plan for the per-sample drill-down + query tool |

## The three lenses

- **Atlas** every sample a dot, one lane per run, honest above the lane line and
  backdoors below, placed left to right by the monitor's reasoning-token count on
  a log axis. Only the runs that emit reasoning tokens show by default; the rest
  join at the left-hand floor when *Non-reasoning monitors* is toggled on. Gold
  rings mark the 51 hardest backdoors (the ones carrying an auditor's read).
- **Trajectories** parallel coordinates: one line per problem across a
  reasoning-effort, score-scale or comments ladder, with the mean path.
- **Flight deck** every run's reachable recall-vs-served-FPR step curves at once,
  a draggable audit budget and a live leaderboard with cost.

Hovering any mark opens a full judgement card in the side panel: the monitor's
call at a 2% budget (caught / missed / false alarm / passed) and whether it was
correct, the budget it would need to flag that one sample, and a problem card
(field catch-rate, backdoor footprint and author, confessing comment, and for the
51 hardest an auditor's incrimination/impact rating with the written reason). The
Atlas can also colour every dot by that verdict. The per-problem metadata is built
by `load_probs()` in `build.py` from `hard-backdoors.csv`, `case-features.csv`,
`backdoor-comment-confessions.csv` and `hard51-risk-ratings.csv`.

### Atlas interactions

- **Zoom.** Drag across the plot to rubber-band-select a token span to zoom into.
  The mouse wheel zooms toward the cursor, but with a 15% dead-band at each edge:
  when the cursor is within the outer 15% the near edge is held, so you can zoom
  into the dense low-token pile on the left without pushing it off screen. A
  **log-scaled scrollbar** sits below the plot: drag its thumb to pan, drag an
  end to zoom, click the bare track to recentre; *Reset zoom* restores the full
  range. The scrollbar is custom (`zb*` in `app.js`) because the native ECharts
  slider maps its window linearly in value, so on a 1..1e6 log axis a 3-decade
  window collapses to a <1% sliver that pans wildly; this one is sized and
  dragged in log space, so the thumb width is the fraction of decades shown. The
  wheel anchoring is likewise computed in log space, the span-select in value space.
- **Pin.** Click any dot to pin its judgement card in the side panel so it stays
  put while you read or copy it; the pinned dot gets a dark ring. Click it again,
  press Esc or Space, double-click the plot, or press the Unpin button to release.
- **Featured strip.** Four curated cards above the plot ("auditor's reads worth a
  look"), each clickable to light that problem across every lane and pin its read.
  The cases are drawn from the committed analysis (a universal honest false alarm,
  two stealthy evasions, one self-confessing backdoor).

## Gates (no browser needed for either)

    bun ssr.mjs         # render every lens at several states (incl. the Atlas floor + verdict modes), both themes, to SVG; flag any empty chart
    bun dom_smoke.mjs   # drive the real app.js through a DOM shim: switch lenses, flip controls, toggle filters, move the slider, flip theme

A real-browser screenshot pass also exists (`scratchpad/shoot.py`, Playwright
with the staged libs on `LD_LIBRARY_PATH`); it confirms zero page errors and is
how the figures were eyeballed.
