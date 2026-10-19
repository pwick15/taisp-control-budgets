"""Template for a new experiment page.

1. Copy this file to reports/experiments/<short-slug>.py (the file name becomes the page URL).
2. Fill in build() below. Delete any block you do not need.
3. Run `uv run python reports/build.py --open`.

Build it as-is with `uv run python reports/build.py --template` to see every component.

Where numbers come from: run src/analyze.py on your logs and commit the two CSVs it writes
(results/<label>.csv and results/<label>-samples.csv). Then load them here with
    run = load_run("<label>")
and use run.auroc, run.safety_at(10), run.honest, run.attack, run.cost_per_sample and so on.
Write sentences that quote numbers with f-strings, so the text cannot drift from the data.

Writing tips: lead with the finding, keep sentences short, define a term the first time you use it,
and put every caveat in the Caveats section.
"""
from viewer import charts
from viewer.components import (
    Bullets, Callout, Code, Figure, Glossary, Group, Journey, LegendItem, Panel, Report, Section,
    Stage, StatTiles, Steps, Table, Text, Tile,
)

# Placeholder scores so the template builds without any results files. Replace with load_run(...).
HONEST = [0.0] * 24 + [0.1] * 6
ATTACK = [0.1, 0.2, 0.5, 0.7, 0.8, 0.8, 0.9, 0.9, 0.9, 0.9] * 3


def build() -> Report:
    figure = Figure(
        "Where the monitor puts honest and attack runs",          # what the chart shows
        [Panel("Monitor name", charts.score_histogram("Monitor name", HONEST, ATTACK, ymax=30), "s1", "variant")],
        how="One sentence telling the reader how to read the chart and what good looks like.",
        legend=[LegendItem("Honest runs", "swatch", "gray"), LegendItem("Attack runs", "swatch", "s1")],
        caption="One or two sentences on what stands out.",
        table=Table(["Score", "Honest runs", "Attack runs"],     # the same numbers as a table, for accessibility
                    [[f"{b / 10:.1f}", str(sum(round(s, 1) == b / 10 for s in HONEST)),
                      str(sum(round(s, 1) == b / 10 for s in ATTACK))] for b in range(11)],
                    align="lrr"),
        columns=1,
    )
    return Report(
        title="Short title that names the experiment",
        subtitle="The question this experiment answers, in one sentence.",
        date="2026-01-01",
        authors=["Your name"],
        summary=[                                                  # 3 to 5 findings, most important first
            "**The headline finding.** One or two sentences with the key number.",
            "**A second finding.** Another sentence.",
            "**The biggest caveat.** What to keep in mind before relying on this.",
        ],
        status="Preliminary, n=30",                                # or "Final", "Needs replication", ...
        tags=["APPS", "trusted monitoring"],
        sections=[
            Section("What we wanted to find out", [
                Text("Plain-language setup. Say what a monitor, a protocol or a score is if the reader may not know."),
                Bullets(["First question.", "Second question."], ordered=True),
                Callout("A short note the reader should not miss.", "note", "Title of the note"),
            ]),
            Section("How the test works", [
                Steps([("Step one", "What happens first."), ("Step two", "What happens next."),
                       ("Step three", "What comes out.")]),
                Glossary([("Term", "Definition in one sentence.")]),
            ]),
            Section("How we got here", [
                Journey([Stage("First attempt", "What we ran.", "What we saw.", "What we changed because of it.")]),
            ]),
            Section("Results", [
                StatTiles([Tile("Monitor A", "0.93", "AUROC", "s1"), Tile("Monitor B", "0.87", "AUROC", "s2")]),
                Table(["Monitor", "AUROC", "Cost per sample"],
                      [Group("Group label (optional)"), ["Monitor A", "0.93", "$0.005"], ["Monitor B", "0.87", "$0.0003"]],
                      caption="What the table shows.", align="lrr"),
                figure,
            ]),
            Section("Caveats", [Callout("Sample size, how the data was made, anything that limits the conclusion.", "caveat")]),
            Section("Reproduce", [Code("uv run python src/experiment.py 30\nuv run python src/analyze.py")]),
        ],
    )
