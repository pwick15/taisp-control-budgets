# Figures

Every chart for the report lives here, one folder per figure: `figure.py` (the generator) next to
`spec.json` (what it produced). Open **`gallery.html`** in a browser to see them all, grouped by report
section, with buttons to copy an image, download PNG, SVG or CSV, export an animated GIF of any figure
with a dial, and switch light/dark.

```
uv run python -m viz build          # rebuild every figure and the gallery
uv run python -m viz check          # every check; screenshots go to viz/.out/
uv run python -m viz new P my-slug --section results
```

- [CLAUDE.md](CLAUDE.md): how to add or change a figure, and the rules the check enforces. Point your Claude here.
- [STYLE.md](STYLE.md): the visual style.
- [HANDOVER.md](HANDOVER.md): open jobs for each of us.
- [report.toml](report.toml): the report's sections and each person's ID letter.
