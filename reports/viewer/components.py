"""Building blocks for experiment reports.

A report is a Report made of Sections, and each Section holds blocks (Text, Table, Figure, ...).
Every block renders itself to HTML. Text arguments accept a little inline markup:
**bold**, `code` and [label](https://link). Everything else is escaped.
"""
import html
import re
from dataclasses import dataclass, field
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parent


def esc(text) -> str:
    return html.escape(str(text), quote=True)


_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+|#[\w-]+|[\w./-]+)\)")


def md(text) -> str:
    """Escape text, then apply the small inline markup."""
    out = esc(text)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return _LINK.sub(lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', out)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def fmt_auroc(x: float) -> str:
    """Two decimals, but never round a near-perfect score up to 1.00."""
    return f"{x:.3f}" if x < 1 and round(x, 2) == 1 else f"{x:.2f}"


class Block:
    def html(self) -> str:
        raise NotImplementedError


@dataclass
class Text(Block):
    text: str

    def html(self):
        return f"<p>{md(self.text)}</p>"


@dataclass
class Bullets(Block):
    items: list[str]
    ordered: bool = False

    def html(self):
        tag = "ol" if self.ordered else "ul"
        return f"<{tag}>" + "".join(f"<li>{md(i)}</li>" for i in self.items) + f"</{tag}>"


@dataclass
class Group:
    """A full-width label row inside a Table."""
    label: str


@dataclass
class Table(Block):
    """headers: column titles. rows: lists of cells (or Group). align: one of l/r per column."""
    headers: list[str]
    rows: list
    caption: str = ""
    align: str = ""

    def html(self):
        align = self.align or "l" * len(self.headers)
        cls = lambda i: ' class="num"' if align[i] == "r" else ""
        head = "".join(f"<th{cls(i)}>{md(h)}</th>" for i, h in enumerate(self.headers))
        body = []
        for row in self.rows:
            if isinstance(row, Group):
                body.append(f'<tr class="group"><td colspan="{len(self.headers)}">{md(row.label)}</td></tr>')
            else:
                body.append("<tr>" + "".join(f"<td{cls(i)}>{md(c)}</td>" for i, c in enumerate(row)) + "</tr>")
        caption = f"<caption>{md(self.caption)}</caption>" if self.caption else ""
        return (f'<div class="tablewrap"><table>{caption}<thead><tr>{head}</tr></thead>'
                f'<tbody>{"".join(body)}</tbody></table></div>')


@dataclass
class Callout(Block):
    """kind: 'note' (default) or 'caveat'."""
    text: str
    kind: str = "note"
    title: str = ""

    def html(self):
        label = self.title or ("Caveat" if self.kind == "caveat" else "Note")
        paragraphs = "".join(f"<p>{md(p)}</p>" for p in self.text.split("\n\n"))
        return f'<div class="callout {esc(self.kind)}"><div class="label">{esc(label)}</div>{paragraphs}</div>'


@dataclass
class Tile:
    label: str
    value: str
    note: str = ""
    slot: str = "gray"  # s1, s2, s3 or gray: the dot beside the label


@dataclass
class StatTiles(Block):
    tiles: list[Tile]

    def html(self):
        cells = "".join(
            f'<div class="tile {esc(t.slot)}"><div class="k"><span class="dot"></span>{md(t.label)}</div>'
            f'<div class="v">{md(t.value)}</div><div class="n">{md(t.note)}</div></div>'
            for t in self.tiles
        )
        return f'<div class="tiles">{cells}</div>'


@dataclass
class Steps(Block):
    """A left-to-right pipeline: items are (title, description)."""
    items: list[tuple[str, str]]

    def html(self):
        cells = "".join(f"<li><b>{md(t)}</b><span>{md(d)}</span></li>" for t, d in self.items)
        return f'<ol class="steps">{cells}</ol>'


@dataclass
class Stage:
    title: str
    did: str
    saw: str
    changed: str


@dataclass
class Journey(Block):
    """What we tried, what happened, and what it changed, one card per stage."""
    stages: list[Stage]

    def html(self):
        cards = []
        for i, s in enumerate(self.stages, 1):
            cards.append(
                f'<li><div class="head"><span class="num">Stage {i}</span><h3>{md(s.title)}</h3></div><dl>'
                f"<dt>What we did</dt><dd>{md(s.did)}</dd>"
                f"<dt>What we saw</dt><dd>{md(s.saw)}</dd>"
                f"<dt>What it changed</dt><dd>{md(s.changed)}</dd></dl></li>"
            )
        return f'<ol class="journey">{"".join(cards)}</ol>'


@dataclass
class Glossary(Block):
    terms: list[tuple[str, str]]

    def html(self):
        return '<dl class="glossary">' + "".join(
            f"<dt>{md(t)}</dt><dd>{md(d)}</dd>" for t, d in self.terms) + "</dl>"


@dataclass
class Code(Block):
    text: str

    def html(self):
        return f"<pre><code>{esc(self.text.strip())}</code></pre>"


@dataclass
class LegendItem:
    label: str
    kind: str = "swatch"  # swatch, ring, line or dash
    slot: str = "gray"


@dataclass
class Panel:
    """One small chart in a grid: a heading above an SVG."""
    title: str
    svg: str
    slot: str = "gray"
    note: str = ""


@dataclass
class Figure(Block):
    """A chart with a title, a how-to-read line, a legend, a caption and a table twin.

    body: SVG markup (one chart) or a list of Panels (a grid of small multiples).
    table: the same numbers as a Table, so nothing depends on seeing colour or hovering.
    """
    title: str
    body: object
    how: str = ""
    legend: list[LegendItem] = field(default_factory=list)
    caption: str = ""
    table: Table | None = None
    columns: int = 3

    def html(self):
        legend = ""
        if self.legend:
            legend = '<div class="legend">' + "".join(
                f'<span class="{esc(i.slot)}"><i class="{esc(i.kind)}{" swatch" if i.kind == "swatch" else ""}"></i>{md(i.label)}</span>'
                for i in self.legend) + "</div>"
        if isinstance(self.body, list):
            cls = {2: "panels two"}.get(self.columns, "panels")
            panels = "".join(
                f'<div class="panel {esc(p.slot)}"><h4><span class="dot"></span>{md(p.title)}'
                f'{f" <small>{md(p.note)}</small>" if p.note else ""}</h4>{p.svg}</div>'
                for p in self.body)
            body = f'<div class="{cls}">{panels}</div>'
        else:
            body = self.body
        how = f'<p class="how">{md(self.how)}</p>' if self.how else ""
        caption = f"<figcaption>{md(self.caption)}</figcaption>" if self.caption else ""
        table = (f'<details class="tableview"><summary>View as table</summary>{self.table.html()}</details>'
                 if self.table else "")
        return f'<figure class="fig"><h3>{md(self.title)}</h3>{how}{legend}{body}{caption}{table}</figure>'


@dataclass
class Section:
    title: str
    blocks: list[Block]

    @property
    def id(self):
        return slugify(self.title)

    def html(self):
        return (f'<section class="sec" id="{self.id}"><h2>{md(self.title)}</h2>'
                + "".join(b.html() for b in self.blocks) + "</section>")


@dataclass
class Report:
    """One experiment page. Fill in every field; see reports/experiments/_template.py."""
    title: str
    subtitle: str
    date: str  # YYYY-MM-DD
    authors: list[str]
    summary: list[str]  # the 3-5 findings someone should leave with
    sections: list[Section]
    status: str = ""  # e.g. "Preliminary, n=30"
    tags: list[str] = field(default_factory=list)
    slug: str = ""  # filled in by build.py from the file name


def _read(name: str) -> str:
    return (VIEWER_DIR / name).read_text(encoding="utf-8")


def _shell(title: str, body: str, home_href: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{_read("theme.css")}</style>
</head>
<body>
<div class="topbar"><div class="wrap"><a href="{home_href}">All experiments</a><button class="theme" type="button">Theme: auto</button></div></div>
<div class="wrap">
{body}
</div>
<script>{_read("app.js")}</script>
</body>
</html>
"""


def render_report(report: Report) -> str:
    chips = [f'<span class="chip">{esc(report.date)}</span>',
             f'<span class="chip">{esc(", ".join(report.authors))}</span>']
    if report.status:
        chips.append(f'<span class="chip status">{esc(report.status)}</span>')
    chips += [f'<span class="chip">{esc(t)}</span>' for t in report.tags]
    summary = "".join(f"<li>{md(s)}</li>" for s in report.summary)
    toc = "".join(f'<a href="#{s.id}">{esc(s.title)}</a>' for s in report.sections)
    body = (f'<header class="report"><h1>{md(report.title)}</h1><p class="subtitle">{md(report.subtitle)}</p>'
            f'<div class="meta">{"".join(chips)}</div></header>'
            f'<div class="tldr"><h2>Summary</h2><ul>{summary}</ul></div>'
            f'<nav class="toc">{toc}</nav>'
            + "".join(s.html() for s in report.sections)
            + '<footer class="foot">Built from the CSV files in <code>results/</code> by '
              '<code>reports/build.py</code>.</footer>')
    return _shell(report.title, body, "index.html")


def render_index(reports: list[Report]) -> str:
    cards = []
    for r in sorted(reports, key=lambda r: r.date, reverse=True):
        status = f'<span class="chip status">{esc(r.status)}</span>' if r.status else ""
        cards.append(
            f'<a class="card" href="{esc(r.slug)}.html"><div class="meta"><span class="chip">{esc(r.date)}</span>'
            f'<span class="chip">{esc(", ".join(r.authors))}</span>{status}</div>'
            f"<h2>{md(r.title)}</h2><p>{md(r.summary[0])}</p></a>")
    body = ('<header class="report"><h1>Experiments</h1><p class="subtitle">One page per experiment. '
            'Open a card to see what was tried, the results and the caveats.</p></header>'
            f'<div class="cards">{"".join(cards)}</div>')
    return _shell("Experiments", body, "index.html")
