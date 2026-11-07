# Handover: what's left for each of us

viz/ holds 41 figures, every one with a generator, and `viz check --strict` passes. These are the jobs
that belong to particular people. Point your Claude at your section; [CLAUDE.md](CLAUDE.md) has the
general rules.

## Marnick

Done:

- **M01 to M08** have real generators in place of the snapshots copied from the data explorer. M01's
  counts at 2% match its snapshot exactly; several titles changed to sharper findings.
- **M09 to M14** are the score-resolution plots from #28 and the three Opus PNGs from #29, now viz
  figures. **M15** draws the hard-backdoor risk ratings (`results/analysis/hard51-risk-ratings.csv`).
- **M16 to M20** are further explorer views (edit size, reasoning dose, comment arms, the token bill).
- #28 and #29 are merged and every figure was rebuilt on the repaired data.

Open: nothing assigned.

## Anusha

Done:

- **A01** is the rogue AI incidents page, moved in as a custom HTML figure. It now follows the gallery's
  theme switch as well as the OS setting.
- **A02** (disclosure delays), **A03** (data loss) and **A05** (incident timeline) are ECharts figures
  drawn from A01's incident log through `viz/data/incidents.py`, so editing the log updates all four.
- **A04** is the trusted vs untrusted monitoring diagram, drawn with ECharts graphic elements so it gets
  the theme and the copy and export buttons.
- **A06** shows GPT-6 Luna and Qwen 3.8 catching more backdoors with more reasoning while false alarms on clean code stay flat.
- **GIF export.** Every figure with a dial has a GIF button, and `viz check` writes `viz/.out/<ID>-light.gif`
  for each one and fails if the export breaks. Figures whose series carry ids glide between dial positions
  (A05); the rest cut. See "Animation and GIFs" in [CLAUDE.md](CLAUDE.md).

Open: HTML figures (A01) still have no image export, only the page itself. Their charts reach the doc as
ECharts figures instead (A02, A03, A05).

## Punjaya

- Done: `blog/results-figures/` is gone, its figures now P01 to P15 and M01 to M08. Its draft takeaways
  are still in history (`git show 03e213b:blog/results-figures/prose.py`), and the Opus subset script
  moved to `scripts/opus_subset.py`.
- `small-sample-explainer.html` (repo root, untracked) can become a custom HTML figure the same way as
  Anusha's page.
- When the final post is assembled, `web/` should embed figures by ID from viz/ rather than draw its own.
- `reports/`, `experiments/*/figures/` and the plots in `src/` stay as they are, as an archive.
