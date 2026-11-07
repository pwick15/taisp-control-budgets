"""Command line for the figures. Run from the repo root:

    uv run python -m viz build [ID ...]      run generators, write spec.json and viz/gallery.html
    uv run python -m viz check [ID ...]      all checks, then PNGs in viz/.out/ to look at
    uv run python -m viz new P cost-vs-safety --section results
    uv run python -m viz list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from viz.kit import core  # noqa: E402

TEMPLATE = '''"""{id}: one line on what this figure shows."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {{
    "id": "{id}",
    "title": "State the finding in twelve words or fewer",
    "section": "{section}",
    "order": 100,
    "caption": "What is plotted and how to read it. Two sentences at most.",
    "notes": [],
    "height": 440,
}}


def build() -> Figure:
    t = S.run_table()
    d = t[t.budget_pct == 2]
    option = C.base(
        xAxis=C.axis("x name", type="value"),
        yAxis=C.axis("y name", type="value"),
        series=[],
    )
    return Figure(option=option, data=d, facts={{}})
'''


def cmd_new(letter: str, slug: str, section: str) -> int:
    letter = letter.upper()
    cfg = core.report()
    if letter not in cfg.get("people", {}):
        print(f"{letter!r} isn't in [people] in viz/report.toml. Add your letter there first.", file=sys.stderr)
        return 1
    if section not in {s["id"] for s in cfg["sections"]}:
        print(f"no section {section!r} in viz/report.toml", file=sys.stderr)
        return 1
    slug = slug.strip().lower().replace(" ", "-").replace("_", "-")
    if not core.DIR_RE.match(f"{letter}01-{slug}"):
        print("slug must be lowercase letters, digits and hyphens", file=sys.stderr)
        return 1
    used = {int(fd.id[1:]) for fd in core.discover() if fd.id[0] == letter}
    used |= {int(r[1:]) for r in cfg.get("retired", []) if r[0] == letter}
    n = max(used, default=0) + 1
    fid = f"{letter}{n:02d}"
    path = core.FIGURES / f"{fid}-{slug}"
    path.mkdir(parents=True)
    (path / "figure.py").write_text(TEMPLATE.format(id=fid, section=section))
    print(f"created {path.relative_to(core.ROOT)}/figure.py. Edit it, then: uv run python -m viz build {fid}")
    return 0


def cmd_list() -> int:
    import json
    for fd in core.discover():
        s = json.loads(fd.spec_path.read_text()) if fd.spec_path.exists() else {}
        print(f"{fd.id:<5} {s.get('section', '?'):<16} {s.get('kind', '?'):<9} {s.get('title', '(not built)')}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m viz", description="Build and check the report figures.")
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="run generators; write spec.json files and viz/gallery.html")
    b.add_argument("ids", nargs="*", help="figure IDs, e.g. P01 (default: all)")
    c = sub.add_parser("check", help="every check; saves PNGs of each figure to viz/.out/")
    c.add_argument("ids", nargs="*")
    c.add_argument("--strict", action="store_true", help="treat snapshot figures as errors")
    c.add_argument("--no-browser", action="store_true", help="skip rendering (not enough to call a figure done)")
    n = sub.add_parser("new", help="create a figure folder with your next free ID")
    n.add_argument("letter", help="your letter from viz/report.toml, e.g. P")
    n.add_argument("slug", help="short name, e.g. cost-vs-safety")
    n.add_argument("--section", default="appendix")
    sub.add_parser("list", help="list figures")
    a = p.parse_args(argv)

    if a.cmd == "build":
        return 1 if core.build(a.ids) else 0
    if a.cmd == "check":
        from viz.kit import check
        return check.run(a.ids, strict=a.strict, browser=not a.no_browser)
    if a.cmd == "new":
        return cmd_new(a.letter, a.slug, a.section)
    return cmd_list()


if __name__ == "__main__":
    sys.exit(main())
