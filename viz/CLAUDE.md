# viz/: every figure for the report

Every chart in this project is a **figure** here: one folder holding its generator and what the generator
produced. The gallery (`viz/gallery.html`, one page, grouped by report section) is where people look at
figures and copy them into the doc. Read [STYLE.md](STYLE.md) before you choose a chart form, colours or
wording; it is the visual standard every figure meets.

Run everything from the repo root:

```
uv run python -m viz new P cost-vs-safety --section results   # new folder, next free ID for letter P
uv run python -m viz build P07                                 # run the generator, rewrite spec.json + gallery
uv run python -m viz check P07                                 # every check, then PNGs in viz/.out/
uv run python -m viz list
```

The first `uv run` installs Playwright (a dev dependency). The browser checks use Chrome, Brave or Edge if
one is installed; otherwise run `uv run playwright install chromium` once.

## Adding a figure

1. Ask whose figure it is if you don't know: the ID letter is the creator's, from `[people]` in
   [report.toml](report.toml). Then `python -m viz new <letter> <slug> --section <id>`. Section ids are in
   report.toml; use `appendix` for anything not in the report.
2. Write `META` and `build()` in the new `figure.py`. Copy the closest worked example (see STYLE.md,
   "Worked examples") rather than starting blank. Shared data code lives in `viz/lib/safety.py`, shared
   chart pieces in `viz/lib/charts.py`; reuse them.
3. `python -m viz build <ID>`, then `python -m viz check <ID>`. Fix every `x` line and rebuild.
4. Open every PNG the check saved for this ID in `viz/.out/` (light and dark, every dial step) and look:
   text readable, nothing clipped or crowded, the finding visible at a glance.

**Done** means `python -m viz check <ID>` ends with `0 errors` and you have looked at every one of those
PNGs. Report both to the person who asked, with the ID.

## Changing a figure or its data

Edit `figure.py` (or the data it reads), then build and check that ID exactly as above. When shared code
in `viz/lib/` or a results CSV changes, run `python -m viz build` with no ID and then `python -m viz check`,
because every figure that depends on it goes **stale**. Before committing a rebuild after new data, diff the
numbers in the affected `spec.json` files and tell the person what moved: titles and captions update
themselves, but the prose in the doc does not.

## Rules

**IDs.** A figure's ID is its creator's letter plus a number (`P07`, `A01`, `M03`); the folder is
`<ID>-<slug>`. People quote IDs in discussion, so an ID is permanent: when a figure is replaced, the new
one gets a new ID and the old ID goes in `retired` in report.toml. The slug may change; the ID may not.

**META** (in `figure.py`):

- `title`: the figure's **finding**, as a claim, in 12 words or fewer, no full stop.
- `caption`: what is plotted and how to read it, 55 words or fewer.
- `section`, `order`: where it sits in the gallery (lower `order` comes first within a section).
- `notes`: optional caveats and open questions for the team, up to 6, each 70 words or fewer.
- `height` in px; `kind`: `echarts` (default), `html` or `snapshot`.

**Numbers in text come from the data.** Write `{gap:.1f}` in a title or caption and return
`facts={"gap": ...}` from `build()`. The check rejects a decimal typed into a title or caption (model
names such as "Sonnet 5.5" are fine), because typed numbers go stale when the data changes.

**Inputs are committed files.** The build records every file a generator opens. Read results from
`results/` (committed CSVs). When a figure needs something derived from gitignored logs, write a small
script under `viz/data/` that produces a committed CSV, commit both, and read the CSV
(`viz/data/derive_magic_numbers.py` is the example).

**Colours are tokens.** Write `"@s0"`, `"@ink-primary"`, `"@goodbad:0.7"`, `"@s1/0.2"`; the gallery turns
them into light or dark colours. Tokens also work inside function strings. Fonts, axis colours, gridlines
and tooltips come from the theme, so options stay free of them. The token list is `viz/kit/theme.py`.

**Text outside the image.** The title and caption sit in the gallery and in the doc, so the option has no
ECharts `title` and no sentences drawn on the chart: a piece of chart text is 8 words or fewer.

**Generated files.** `spec.json` and `gallery.html` are build output. Regenerate them with
`python -m viz build`; hand edits are caught by the check. On a merge conflict in either, take either side
and rebuild.

**Snapshots.** A `snapshot` figure is an exported option with no generator, kept so it shows in the
gallery. The check warns about it (and fails with `--strict`). Replacing one with a real generator is in
[HANDOVER.md](HANDOVER.md).

**Diagrams.** A flow chart or explainer is an ECharts option with `graphic` elements (rects, text, polylines)
and no series, so it follows the theme and gets the same copy and export buttons as a chart. The check
treats an option with graphic and no series as a diagram and doesn't ask it for data. A04 is the example.

**Animation and GIFs.** Every figure with a dial gets a GIF button: the GIF holds each dial position for
1.6 s and loops. If every series in the dial's frames has an `id`, the figure *glides*: marks move to their
new place, live in the gallery and in the GIF (A05 is the example; set `animation: True` in its option).
Without ids it cuts from one position to the next. `python -m viz check` writes `viz/.out/<ID>-light.gif`
for every dial figure; open it.

**Custom HTML.** For an interactive piece ECharts can't express, set `kind: "html"` and put a
self-contained page in `figure.html` next to `figure.py`. The gallery embeds it and sets
`data-theme="light"` or `"dark"` on its `<html>`; use the same palette as `viz/kit/theme.py`. Write its dark
colours under both `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {...} }` and
`:root[data-theme="dark"] {...}` so it follows the gallery's theme switch (A01 does). An HTML figure has no
image export, so a chart from it that belongs in the doc should also be an ECharts figure reading the same
data: A02, A03 and A05 read A01's incident log through `viz/data/incidents.py`.

## The framework itself

`viz/kit/` is the framework: build and gallery (`core.py`), checks (`check.py`, `browser.py`), tokens
(`theme.py`), and the gallery page (`page/`). Change it only when a figure needs something it can't do,
and run the full build and check afterwards.
