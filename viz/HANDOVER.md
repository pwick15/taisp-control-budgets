# Handover: what's left for each of us

viz/ is set up and holds 23 figures. These are the jobs that belong to particular people. Point your
Claude at your section; [CLAUDE.md](CLAUDE.md) has the general rules.

## Marnick

### 1. Give the eight snapshots real generators

M01 to M08 are views copied from your data explorer (`marnick-data-2`, built 2026-11-02) as exported
ECharts options. They show in the gallery with a "Snapshot, no generator" badge, and `viz check` warns
about each one, because nobody can rebuild them when the data changes. M01 is in the report (the
comments figure); the rest are in the appendix.

| ID | Your view id |
| --- | --- |
| M01 | `cases-catch-set-upset` |
| M02 | `b1-requested-vs-served` |
| M03 | `e3-width-vs-rows` |
| M04 | `geom-score-scale` |
| M05 | `cases-honest-recalibration` |
| M06 | `geom-ensemble-vs-budget` |
| M07 | `free-auc-reason-vs-suspicion` |
| M08 | `geom-campaign-safety` |

For each one:

1. Find the code in your explorer that builds that view.
2. Move its data logic into `build()` in `viz/figures/Mxx-*/figure.py`, reading only committed files
   (`results/` CSVs, or a small derived CSV under `viz/data/` if it needs the logs). Reuse
   `viz/lib/safety.py` where it already computes what you need.
3. Remove `"kind": "snapshot"` and `"source"` from META, and restyle the option to
   [STYLE.md](STYLE.md): colour tokens, no font settings, no sentences on the chart (the check lists what
   each snapshot breaks today, prefixed `(snapshot)`).
4. Keep or improve the title, caption and notes. A title is the finding in 12 words or fewer.
5. `uv run python -m viz build Mxx`, then `uv run python -m viz check --strict Mxx`, and look at the PNGs.

**Done** when `uv run python -m viz check --strict M01 M02 M03 M04 M05 M06 M07 M08` ends with `0 errors`.
Keep the IDs: people already refer to them.

### 2. After your PRs #28 and #29 merge

- They change data our figures read, and both edit `results/analysis/achieved-fpr.csv` and
  `results/analysis/safety-with-ci.csv`, so the second to merge will need those two regenerated.
- Then run `uv run python -m viz build` and `uv run python -m viz check`. Figures whose inputs changed
  rebuild; diff their `spec.json` and post what moved, since the draft quotes some of these numbers.
- Port the three Opus PNGs (`results/analysis/opus-hard51-fig*.png`, from `scripts/analysis_opus_hard51.py`)
  and the score-resolution plot (`scripts/plot_score_resolution_batches.py`) into viz/ as M figures.
- If you can, commit the incrimination and harm ratings for the 51 hard backdoors as a CSV, so the 2x2
  can be rebuilt as a figure (P12's notes mention it).

## Anusha

### Move the rogue AI incidents page into viz/

`interactive_viz/introduction/rogue-ai-incidents.html` goes in as a custom HTML figure. It was tested in the
gallery and renders as it does on its own.

1. `uv run python -m viz new A rogue-ai-incidents --section intro`
2. Move the page into the new folder as `figure.html`
   (`git mv interactive_viz/introduction/rogue-ai-incidents.html viz/figures/A01-rogue-ai-incidents/figure.html`).
3. In `figure.py`, delete `build()` and set META: `"kind": "html"`, `"height": 1100`, a title that states the
   finding in 12 words or fewer, and a short caption.
4. Build, check, and look at `viz/.out/A01-light.png` and `-dark.png`.

Two things worth doing while you're there: the page follows the OS colour setting, so making it also
respond to `data-theme="dark"` on `<html>` (which the gallery sets) would let it follow the gallery's
theme switch; and GIF export, which isn't built. The export buttons live in `act()` in
`viz/kit/page/gallery.js`.

## Punjaya

- `blog/results-figures/` can go once you're happy: all 23 of its figures are now in viz/ (P01 to P15,
  M01 to M08). Its `prose.py` still holds the draft takeaways if you want them.
- `small-sample-explainer.html` (repo root, untracked) can become a custom HTML figure the same way as
  Anusha's page.
- When the final post is assembled, `web/` should embed figures by ID from viz/ rather than draw its own.
- `reports/`, `experiments/*/figures/` and the plots in `src/` stay as they are, as an archive.
