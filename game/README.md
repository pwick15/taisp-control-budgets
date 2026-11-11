# Spot the Backdoor (the game)

The player is the knight: ten real programs, some with a hidden backdoor, and after each one the
player sees what ten AI monitors decided on the same code. Built by Anusha Asim, who moved it onto
the project site in PR #47 as a hand-copied `web/spot-the-backdoor.html`. This folder is now its
source, so it shares the site's header, fonts and colours, and rebuilding replaces that file. The
address stays `/spot-the-backdoor`.

- `template.html`: the page (layout, styles, script). Edit copy and layout here.
- `data.json`: the 55 programs (code, plain-English notes, the trick and its secret input, and each
  monitor's suspicion score), plus each monitor's 2% cutoff. Every game includes Marnick's three
  featured cases: one blatant backdoor, one near-invisible one and one clean program that looks guilty.
- `add_cutoffs.py`: writes each monitor's cutoff (`cut`), its tie chance (`p`) and its overall
  catch rate (`catch`) into `data.json`, from `results/*-samples.csv`, using the study's rule in
  `shared/cutoff.py`.
- `build.py`: inlines the data and the shared pieces in `shared/`, and writes
  `web/spot-the-backdoor.html`.

To change something: edit `template.html` or `data.json`, run `python game/build.py`, and commit
both the source and `web/spot-the-backdoor.html`.

A knight flags a program when its score is above its cutoff. A program tied exactly at the cutoff
is checked at random, with the chance the study uses, drawn once per game. So each knight's overall
catch rate matches the story and the blog post (Sonnet 5.5 catches 87.6% at 2%).
