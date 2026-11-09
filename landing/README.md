# Knights of the Audit (landing page)

The interactive tour at the root of the site: a ninja robot (the backdoor writer) against knight robots
(the monitors), with real duels, a boss fight and the main findings. It is one self-contained HTML file.

- `template.html`: the page (layout, styles, script). Edit copy and layout here.
- `data.json`: every number and program the page shows, exported from `results/` and `viz/`.
- `build.py`: inlines the data and writes `web/index.html`.

To change something: edit `template.html` (or `data.json`), run `python landing/build.py`, and commit
both the source and `web/index.html`. Cloudflare Pages deploys `web/` on push to main.

Links to the blog post and the data deep dive are set in the `LINKS` block near the top of the script
in `template.html`. An empty value shows that card as "Coming soon".

The previous page (write-up plus cost-vs-safety chart) now lives at `web/results.html`, built by `web/build.py`.

The Spot the Backdoor game is a single self-contained file, `web/spot-the-backdoor.html`, served at `/spot-the-backdoor`.
It has no build step here: replace the file to update the game.
