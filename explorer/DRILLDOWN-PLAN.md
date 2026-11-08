# Drill-down + query tool: plan

Let a reader go from the high-level Atlas to a fully detailed, per-sample view, and
filter the data themselves.

## Status

- **DONE — drill-down drawer (option 1b).** Click a ringed backdoor or a featured
  card to pin it, then **Deep dive** opens a drawer: original problem, honest-vs-
  backdoor code (line diff when they overlap, else backdoor shown plainly with the
  honest reference below), secret input, outcome, field difficulty, auditor's read,
  and the monitor's own reasoning. Data from `extract_detail.py` -> `detail.json`
  (52 backdoors: the 51 with auditor's reads + featured #837; reasoning captured for
  the runs that have trajectories, currently Haiku 5.5 and Qwen-none).
- **TODO — custom query/filter panel (option 1a).** See below.

## What the source data actually supports (verified)

The explorer bundle is thin (per sample: suspicion score + reasoning-token count).
The rich material lives in the inspect_ai `.eval` logs under
`trajectories/<run>/.../*.eval` (one honest + one attack file per run, ~80 MB each,
~507 MB total). Confirmed extractable with `inspect_ai` (`read_eval_log`):

- **Original safe problem** — `sample.metadata['main_task_description']` (APPS prompt).
- **The backdoor** — the submitted attack code and trigger in
  `json.loads(sample.store['submit_args'])` -> `{code, secret_input}`.
- **A real diff** — the honest `.eval` holds the clean solution for the same
  `sample.id`. Honest vs attack share the skeleton and the attack injects a flaw
  (e.g. a "discount if n is prime" branch, triggered by secret input `11 4`). It is
  a best-effort diff, not a guaranteed minimal patch (honest/attack are generated
  independently), so present it as "clean solution + injected backdoor + trigger",
  not a literal git patch.
- **Monitor reasoning text** — the monitor model's `<reasoning>…</reasoning>`
  completion in the sample's `ModelEvent` output, with its suspicion score.
- **Outcome** — `sample.scores['apps_scorer']`: `main_task_success` (passed tests)
  and `side_task_success` (trigger fired); plus the 2%-budget verdict the page
  already computes, and the cross-monitor "how many caught it" (already in-bundle,
  since the Atlas holds every monitor's score for a problem).
- Note: `-strip` runs show the monitor the code with comments removed, which is why
  an obvious-looking backdoor can score low. That stripped-vs-raw contrast is itself
  a story worth surfacing.

## The hard constraint

The deliverable is one self-contained offline HTML (currently 1.84 MB). 507 MB
cannot be embedded. `fetch()` of local files is blocked under `file://`, so any
lazy-load-per-sample design only works served over HTTP (which, on Cloudflare
Pages, is fine — but it breaks opening the file directly). Every option below is
really answering: how much detail, for how many samples, delivered how.

## Dead ends (rejected)

- **"Open in GitHub"** — the `.eval`s are 80 MB binaries in the repo, not browsable;
  linking there is low value. Generate our own detail instead.
- **Drill-down for all 47,600 samples** — ~10,500 are honest programs the monitor
  correctly ignored; value is concentrated in the backdoors, the missed ones and the
  false alarms. Don't build detail for boring points.

## Options, ranked by value to a technically-literate user

1. **Curated drawer + query panel — stays one file (recommended).**
   (a) A composable **query panel** over fields already in the bundle
   (run/side/suspicion-range/token-range/verdict/has-auditor-read/catch-rate/impact)
   with live counts; near-zero size cost, no new extraction. (b) A **drill-down
   drawer**: click a dot -> problem, clean-vs-backdoor diff, secret input, monitor
   reasoning, outcome, cross-monitor strip. Embed detail only for the curated 51
   hard backdoors + the honest false-alarm cases to stay self-contained. Size dial:
   problem+diff+outcome is cheap (~300 KB); monitor reasoning for all in-view runs of
   the 51 adds ~3–5 MB (the main lever — curate to missed/false-alarm if needed).

2. **Generated per-sample static pages — becomes a folder/site.**
   `build.py` emits a `web/explorer-detail/` folder, one standalone HTML per
   interesting backdoor (~10,500), Atlas dots deep-link to them. Full depth, no
   fetch, offline-safe, Pages-friendly — but the deliverable is now many files and
   tens of MB. Best when browsed online, not double-clicked.

3. **Lazy JSON sidecar — Pages-only.** Smallest base file, scales to all samples, but
   `file://` CORS breaks double-click-to-open. Only if we commit to HTTP serving.

4. **Featured-only enrichment — cheapest, narrowest.** Deep detail on just the 4
   featured cards + pinned card. A subset of option 1.

**Recommendation:** option 1 now (query panel is independently high value and almost
free; the drawer delivers drill-down for the dots that matter), option 2 as a clean
follow-on if every backdoor must be drillable and shipping a folder to Pages is fine.

## Open decision (was mid-question when paused)

Two forks to confirm before building:
1. Drill-down delivery/scope: option 1 (curated drawer, one file) vs 2 (per-sample
   pages, folder) vs 4 (featured-only) vs 3 (JSON sidecar, Pages-only).
2. Include the custom query/filter panel now, or as a follow-up.

## Build notes for execution

- Extraction step in `build.py` (or a sibling script): iterate the curated sample
  set, `read_eval_log` the matching attack + honest `.eval`, pull
  problem/code/secret/reasoning/outcome, and emit a compact per-sample detail blob
  into the bundle (or into detail pages for option 2). The `.eval` read is slow
  (~80 MB files) but offline/one-time at build.
- Keep the SSR + DOM gates green; add a case that opens the drawer.
- Respect the single-file, offline, no-em-dash deliverable conventions.
