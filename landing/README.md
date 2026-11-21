# Knights of the Audit (the story page)

The site's front page: the question, every way into the project (story, blog post, game, data),
then the study told as a short story. A ninja (the model that writes backdoors) against knights
(the monitor models), with an auditor who can only check a small share of the code. It walks
through what a backdoor is, how an audit budget turns scores into catches, trusted versus
untrusted monitors, four findings, advice and limits. The knight cards, the duel and the boss fight
from the first version live inside the story: the cards and duel in "We sent 13 knights through the
same gate", the boss fight in "What gets through looks like an honest bug". It is one self-contained
HTML file.

- `template.html`: the page (layout, styles, script). Edit copy and layout here.
- `data.json`: every number and program the page shows, exported from `results/` and `viz/`.
- `add_story_data.py`: adds what the story needs on top of that export: score piles for the
  cutoff walkthrough (Sonnet 5.5, Haiku 5.5 and the jumpy Ministral 14B), one honest program
  that three knights scored very differently, and every knight's duel calls under the study's tie
  rule (`shared/cutoff.py`).
- `build.py`: inlines the keys the page uses and the shared pieces in `../shared/`, and writes
  `web/index.html`.

To change something: edit `template.html` (or the data), run `python landing/build.py`, and
commit both the source and `web/index.html`. Cloudflare Pages deploys `web/` on push to main.

Every number in the text is computed from the data when the page loads (the `data-fill` spans and
the chart code), except two figures from the report typed into the advice: GLM-5.3's per-token
price and token use against Sonnet's, and Haiku 4.5's per-token price against Haiku 5.5's. The
advice follows the report's four practical recommendations.

The outside links (blog post, GitHub) and the header, footer, fonts and colours shared with the
game and the data page live in `../shared/`. The earlier results page is `web/results.html`, built
by `web/build.py`.

The Spot the Backdoor game is built from `game/` into `web/spot-the-backdoor.html`, served at
`/spot-the-backdoor`; see `game/README.md`.
