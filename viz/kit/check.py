"""python -m viz check: the rules a figure must pass before anyone calls it done.

Static checks read META, spec.json and git. Browser checks render every figure (each dial step,
light and dark) in a headless browser, look for errors and for text that is clipped, overlapping
or too long, and save PNGs to viz/.out/ so a person or agent can look at them.

Snapshot figures (no generator yet) are warnings, not errors, unless --strict is passed.
"""
from __future__ import annotations

import base64
import json
import re
import subprocess
from dataclasses import dataclass, field

from . import core, theme

TITLE_WORDS = 12
CAPTION_WORDS = 55
NOTE_WORDS = 70
MAX_NOTES = 6
TEXT_WORDS = 8          # the longest single piece of text drawn inside a chart
CHART_WORDS = 70        # every word drawn inside a chart: ticks, legend, labels, notes
LEGEND_ITEMS = 8
FONT_SIZES = {11, 12, 13, 14, 15, 16, 18, 20, 24, 28}
HEIGHT = (160, 900)
HTML_HEIGHT = (160, 2400)  # custom HTML figures can be long pages
DECIMAL = re.compile(r"(?<![\w{.:])\d+\.\d+")
# Version numbers in model names ("Sonnet 5.5", "GLM-5.3") aren't data, so they're removed before
# the typed-number check. Add a family here if a new model's name trips it.
MODEL_NAME = re.compile(r"(?i)\b(sonnet|haiku|opus|claude|qwen|gemini|glm|gpt|gemma|llama|mistral|ministral|"
                        r"large|flash|deepseek|grok|luna)[\s-]*\d+(?:\.\d+)+")
# Hex colours have 3, 4, 6 or 8 digits, so an issue number like "#97660" (5 digits) isn't one.
COLOUR = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b|\brgba?\(|\bhsla?\(")
FN = re.compile(r"^\s*(function\s*\(|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)")


@dataclass
class Findings:
    items: list[tuple[str, str, str]] = field(default_factory=list)  # (level, figure id or "*", message)

    def err(self, fid: str, msg: str) -> None:
        self.items.append(("error", fid, msg))

    def warn(self, fid: str, msg: str) -> None:
        self.items.append(("warning", fid, msg))


def words(s: str) -> int:
    return len(re.findall(r"[A-Za-z][A-Za-z'’-]*", s or ""))


def git_lists() -> tuple[set[str], callable]:
    tracked = set(subprocess.run(["git", "ls-files", "-z"], cwd=core.ROOT, capture_output=True, check=True)
                  .stdout.decode().split("\0")) - {""}

    def ignored(paths: list[str]) -> set[str]:
        if not paths:
            return set()
        r = subprocess.run(["git", "check-ignore", "--no-index", "--stdin", "-z"], cwd=core.ROOT,
                           input="\0".join(paths).encode(), capture_output=True)
        return set(r.stdout.decode().split("\0")) - {""}

    return tracked, ignored


# ------------------------------------------------------------------ option lint

def _walk(node, path="option"):
    if isinstance(node, dict):
        for k, v in node.items():
            yield f"{path}.{k}", k, v
            yield from _walk(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield f"{path}[{i}]", None, v
            yield from _walk(v, f"{path}[{i}]")


def lint_option(fid: str, option: dict, dial: dict | None, f: Findings) -> None:
    trees = [("option", option)] + [(f"dial frame {i}", fr) for i, fr in enumerate((dial or {}).get("frames") or [])]
    for label, tree in trees:
        if label == "option" and "title" in tree:
            f.err(fid, "has an ECharts title. Titles live in META['title'], outside the image")
        for path, key, v in _walk(tree, label):
            if key == "fontFamily":
                f.err(fid, f"sets fontFamily at {path}. The theme sets the font")
            if key == "fontSize" and isinstance(v, (int, float)) and v not in FONT_SIZES:
                f.err(fid, f"fontSize {v} at {path} isn't on the type scale {sorted(FONT_SIZES)}")
            if key == "type" and v == "dashed" and ".splitLine." in path:
                f.err(fid, f"dashed gridlines at {path}. Gridlines are solid hairlines")
            if not isinstance(v, str):
                continue
            if COLOUR.search(v):
                f.err(fid, f"raw colour at {path}: {v[:60]!r}. Use a token from viz/kit/theme.py")
            if v.startswith("@") and not theme.known(v):
                f.err(fid, f"unknown colour token {v!r} at {path}")
            if FN.match(v):
                for tok in theme.TOKEN_RE.findall(v):
                    if not theme.known(tok):
                        f.err(fid, f"unknown colour token {tok!r} inside a function at {path}")
    for axis in ("xAxis", "yAxis"):
        ax = option.get(axis)
        axes = ax if isinstance(ax, list) else [ax] if ax else []
        per_grid: dict[int, int] = {}
        for a in axes:
            g = (a or {}).get("gridIndex", 0)
            per_grid[g] = per_grid.get(g, 0) + 1
        if any(n > 1 for n in per_grid.values()):
            f.err(fid, f"two {axis} scales on one grid (dual axis). Use two panels or a common base")
    legends = option.get("legend")
    for lg in legends if isinstance(legends, list) else [legends] if legends else []:
        if len(lg.get("data") or []) > LEGEND_ITEMS:
            f.err(fid, f"legend has {len(lg['data'])} entries; the limit is {LEGEND_ITEMS}. Group the rest as 'Other' or facet")
    for g in option.get("graphic") or []:
        txt = ((g or {}).get("style") or {}).get("text", "")
        if words(txt) > TEXT_WORDS:
            f.err(fid, f"graphic text has {words(txt)} words: {txt[:50]!r}. Move sentences to the caption")


# ------------------------------------------------------------------ static checks

def check_static(figs: list[core.FigDir], f: Findings, strict: bool) -> dict[str, dict]:
    cfg = core.report()
    sections = {s["id"] for s in cfg["sections"]}
    people = cfg.get("people", {})
    retired = set(cfg.get("retired", []))
    tracked, ignored_fn = git_lists()
    specs: dict[str, dict] = {}

    seen: dict[str, str] = {}
    for fd in core.discover():
        if fd.id in seen:
            f.err(fd.id, f"two folders use this ID: {seen[fd.id]} and {fd.path.name}")
        seen[fd.id] = fd.path.name

    for fd in figs:
        fid = fd.id
        if not core.DIR_RE.match(fd.path.name):
            f.err(fid, f"folder {fd.path.name!r} must be <ID>-<slug>, for example P07-cost-vs-safety")
        if fid[:1] not in people:
            f.err(fid, f"letter {fid[:1]!r} isn't in [people] in viz/report.toml")
        if fid in retired:
            f.err(fid, "this ID is retired. Take the next free one with `python -m viz new`")
        if not (fd.path / "figure.py").exists():
            f.err(fid, "no figure.py")
            continue
        try:
            meta = dict(core.load_module(fd).META)
        except Exception as e:  # noqa: BLE001
            f.err(fid, f"figure.py doesn't import: {e}")
            continue
        for key in ("id", "title", "section", "caption"):
            if not meta.get(key):
                f.err(fid, f"META needs {key!r}")
        if meta.get("id") and meta["id"] != fid:
            f.err(fid, f"META id {meta['id']!r} doesn't match the folder")
        if meta.get("section") and meta["section"] not in sections:
            f.err(fid, f"section {meta['section']!r} isn't in viz/report.toml ({', '.join(sorted(sections))})")
        title, caption = meta.get("title", ""), meta.get("caption", "")
        if title.startswith("State the finding") or caption.startswith("What is plotted and how to read it"):
            f.err(fid, "title or caption is still the template text from `python -m viz new`")
        if words(title) > TITLE_WORDS:
            f.err(fid, f"title has {words(title)} words; the limit is {TITLE_WORDS}")
        if title.rstrip().endswith("."):
            f.err(fid, "title ends with a full stop")
        if words(caption) > CAPTION_WORDS:
            f.err(fid, f"caption has {words(caption)} words; the limit is {CAPTION_WORDS}")
        for where, text in (("title", title), ("caption", caption)):
            for num in DECIMAL.findall(MODEL_NAME.sub("", text)):
                f.err(fid, f"{where} has a typed number {num}. Compute it in build() and use a {{fact}}")
        notes = meta.get("notes", [])
        if len(notes) > MAX_NOTES:
            f.err(fid, f"{len(notes)} notes; the limit is {MAX_NOTES}")
        for n in notes:
            if words(n) > NOTE_WORDS:
                f.err(fid, f"a note has {words(n)} words; the limit is {NOTE_WORDS}: {n[:50]!r}")
        kind = meta.get("kind", "echarts")
        h, rng = int(meta.get("height", core.DEFAULT_HEIGHT)), HTML_HEIGHT if kind == "html" else HEIGHT
        if not rng[0] <= h <= rng[1]:
            f.err(fid, f"height {h} is outside {rng}")
        if kind == "snapshot":
            msg = ("snapshot with no generator: nobody can rebuild it when the data changes. "
                   "See viz/HANDOVER.md")
            (f.err if strict else f.warn)(fid, msg)
            if not meta.get("source"):
                f.err(fid, "snapshot needs META['source'] saying where it came from")

        if not fd.spec_path.exists():
            f.err(fid, f"not built. Run `uv run python -m viz build {fid}`")
            continue
        spec = json.loads(fd.spec_path.read_text(encoding="utf-8"))
        specs[fid] = spec
        b = spec.get("build", {})
        if core.spec_hash(spec) != b.get("spec"):
            f.err(fid, f"spec.json was edited by hand. Rebuild it: `uv run python -m viz build {fid}`")
        if b.get("code") != core.code_hash(fd):
            f.err(fid, f"stale: figure.py, viz/lib or a code dependency changed since the last build. Run `uv run python -m viz build {fid}`")
        inputs = b.get("inputs", {})
        for path, h in inputs.items():
            p = core.ROOT / path
            if not p.exists():
                f.err(fid, f"input {path} no longer exists")
            elif core.file_hash(p) != h:
                f.err(fid, f"stale: {path} changed since the last build. Run `uv run python -m viz build {fid}`")
        ign = ignored_fn(list(inputs))
        for path in inputs:
            if path in ign:
                f.err(fid, f"reads {path}, which git ignores, so nobody else can rebuild this figure. "
                           "Commit a small derived file under viz/data/ instead")
            elif path not in tracked:
                if path.startswith("viz/"):
                    f.warn(fid, f"reads {path}, which isn't in git yet. Add it in the same commit: git add {path}")
                else:
                    f.err(fid, f"reads {path}, which isn't committed, so nobody else can rebuild this figure")
        if kind == "echarts":
            lint_option(fid, spec.get("option") or {}, spec.get("dial"), f)
            frames = [spec.get("option") or {}] + list((spec.get("dial") or {}).get("frames") or [])
            # A diagram (graphic elements and no series at all, like A04) has no data by design.
            diagram = not any(fr.get("series") for fr in frames) and any(fr.get("graphic") for fr in frames)
            if not diagram and not any(s.get("data") for fr in frames for s in (fr.get("series") or [])):
                f.err(fid, "the chart has no data: every series is empty")
            if not spec.get("data") and not diagram:
                f.warn(fid, "no data table: build() returned no Figure.data, so there's no CSV button")
        elif kind == "snapshot":
            sub = Findings()
            lint_option(fid, spec.get("option") or {}, spec.get("dial"), sub)
            for _, _, msg in sub.items:
                f.warn(fid, f"(snapshot) {msg}")

    # The browser checks must see the current specs, so bring the gallery up to date first.
    if core.write_gallery():
        f.warn("*", "viz/gallery.html was out of date, so check regenerated it. Commit the new copy")
    return specs


# ------------------------------------------------------------------ browser checks

def check_browser(ids: list[str], specs: dict[str, dict], f: Findings, strict: bool) -> list[str]:
    from . import browser
    core.OUT.mkdir(exist_ok=True)
    for old in [*core.OUT.glob("*.png"), *core.OUT.glob("*.gif")]:
        if not ids or old.name.split("-")[0] in ids:
            old.unlink()
    results, page_errors, shots, gifs = browser.run(ids)
    for e in page_errors:
        f.err("*", f"gallery page error: {e}")
    saved = []
    for r in results:
        fid = r["id"]
        if r.get("html"):
            continue
        spec = specs.get(fid, {})
        snap = spec.get("kind") == "snapshot"
        report = f.warn if (snap and not strict) else f.err
        where = f"{r['mode']}"
        if spec.get("dial"):
            where += f", {spec['dial']['label'].lower()} {spec['dial']['steps'][r['step']]}"
        for e in r["errors"]:
            report(fid, f"render error ({where}): {e[:200]}")
        for t in sorted(set(r["clipped"])):
            report(fid, f"text runs off the chart ({where}): {t[:60]!r}")
        for a, b in sorted({tuple(x) for x in r["overlaps"]}):
            report(fid, f"text overlaps ({where}): {a[:40]!r} and {b[:40]!r}")
        for t in sorted(set(r["long"])):
            report(fid, f"text in the chart is over {TEXT_WORDS} words ({where}): {t[:60]!r}. Move it to the caption")
        if r["words"] > CHART_WORDS:
            report(fid, f"{r['words']} words drawn in the chart ({where}); the limit is {CHART_WORDS}")
        if r.get("png"):
            step = ""
            if spec.get("dial"):
                step = "-" + re.sub(r"[^A-Za-z0-9.]+", "", str(spec["dial"]["steps"][r["step"]]))
            out = core.OUT / f"{fid}{step}-{r['mode']}.png"
            out.write_bytes(base64.b64decode(r["png"].split(",", 1)[1]))
            saved.append(out.relative_to(core.ROOT).as_posix())
    for fid, g in gifs.items():
        steps = len(specs.get(fid, {}).get("dial", {}).get("steps", []))
        if g.get("error"):
            f.err(fid, f"GIF export failed: {g['error']}")
        elif g["frames"] < steps:
            f.err(fid, f"GIF export has {g['frames']} frames for {steps} dial positions")
        else:
            out = core.OUT / f"{fid}-light.gif"
            out.write_bytes(base64.b64decode(g["gif"]))
            saved.append(out.relative_to(core.ROOT).as_posix())
    for (fid, theme_name), png in shots.items():
        out = core.OUT / f"{fid}-{theme_name}.png"
        out.write_bytes(png)
        saved.append(out.relative_to(core.ROOT).as_posix())
    return saved


# ------------------------------------------------------------------ entry point

def run(ids: list[str] | None, strict: bool = False, browser: bool = True) -> int:
    figs = core.discover()
    if ids:
        want = {i.upper() for i in ids}
        figs = [fd for fd in figs if fd.id in want]
        missing = want - {fd.id for fd in figs}
    else:
        missing = set()
    f = Findings()
    for m in sorted(missing):
        f.err(m, f"no folder viz/figures/{m}-*")
    specs = check_static(figs, f, strict)
    saved: list[str] = []
    if browser:
        try:
            saved = check_browser([fd.id for fd in figs] if ids else [], specs, f, strict)
        except RuntimeError as e:
            f.err("*", f"browser checks didn't run: {e}")
    else:
        f.warn("*", "browser checks skipped (--no-browser). A figure isn't done until they pass")

    by_fig: dict[str, list[tuple[str, str]]] = {}
    for level, fid, msg in f.items:
        by_fig.setdefault(fid, []).append((level, msg))
    n_err = sum(1 for lv, _, _ in f.items if lv == "error")
    n_warn = sum(1 for lv, _, _ in f.items if lv == "warning")
    print(f"viz check: {len(figs)} figure{'s' if len(figs) != 1 else ''}{' (strict)' if strict else ''}")
    for fd in figs:
        items = by_fig.get(fd.id, [])
        status = "FAIL" if any(lv == "error" for lv, _ in items) else ("warn" if items else "ok")
        print(f"  {fd.id:<5}{status}")
        for lv, msg in items:
            print(f"         {'x' if lv == 'error' else '!'} {msg}")
    for lv, msg in by_fig.get("*", []):
        print(f"  {'x' if lv == 'error' else '!'} {msg}")
    if saved:
        print(f"\nScreenshots: {len(saved)} PNGs and GIFs in viz/.out/. Open them and look before calling a figure done.")
    print(f"\n{n_err} error{'s' if n_err != 1 else ''}, {n_warn} warning{'s' if n_warn != 1 else ''}.")
    return 1 if n_err else 0
