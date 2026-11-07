"""Find figures, run their generators, and write spec.json files and the gallery.

A figure is a folder viz/figures/<ID>-<slug>/ holding figure.py (META and build()) and the
spec.json that build() produces. The build records every file a generator reads, so the
check can confirm each input is committed and notice when one changes.
"""
from __future__ import annotations

import base64
import contextlib
import copy
import functools
import hashlib
import html
import importlib.util
import json
import math
import numbers
import os
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import theme

ROOT = Path(__file__).resolve().parents[2]
VIZ = ROOT / "viz"
FIGURES = VIZ / "figures"
KIT = VIZ / "kit"
LIB = VIZ / "lib"
GALLERY = VIZ / "gallery.html"
OUT = VIZ / ".out"
REPORT = VIZ / "report.toml"
ECHARTS = KIT / "vendor" / "echarts-5.5.1.min.js"
FONT = KIT / "fonts" / "inter-latin-wght-normal.woff2"

# Code outside viz/ that generators depend on: viz/lib/safety.py loads the run list from it.
CODE_DEPS = ["web/build.py"]

DIR_RE = re.compile(r"^([A-Z])(\d{2,3})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
KINDS = ("echarts", "html", "snapshot")
DEFAULT_HEIGHT = 440


class BuildError(Exception):
    pass


@dataclass
class Figure:
    """What a generator's build() returns.

    option  ECharts option. Colours are theme tokens ("@s0"), never hex.
    data    the numbers behind the chart (DataFrame or list of dicts). Feeds the CSV button.
    facts   values for {placeholders} in META title, caption and notes.
    dial    optional control: {"label", "steps": [...], "initial": i, "frames": [partial option, ...]}.
            Each frame is merged over option (top-level keys) when its step is picked.
    height  chart height in px, when it depends on the data (say, one row per model).
            Otherwise META["height"] applies.
    """
    option: dict | None = None
    data: Any = None
    facts: dict = field(default_factory=dict)
    dial: dict | None = None
    height: int | None = None


@dataclass
class FigDir:
    id: str
    slug: str
    path: Path

    @property
    def rel(self) -> str:
        return self.path.relative_to(ROOT).as_posix()

    @property
    def spec_path(self) -> Path:
        return self.path / "spec.json"


# ------------------------------------------------------------------ recording reads

_stack: list[set[str]] = []


def _audit(event: str, args: tuple) -> None:
    if event != "open" or not _stack:
        return
    path, mode = args[0], args[1] if len(args) > 1 else None
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    if isinstance(mode, str) and any(c in mode for c in "wax+"):
        return
    try:
        p = Path(os.fsdecode(path)).resolve()
        rel = p.relative_to(ROOT)
    except (ValueError, OSError):
        return
    if p.suffix in (".py", ".pyc") or rel.parts[0] in (".venv", ".git") or rel.parts[:2] == ("viz", "kit"):
        return
    for s in _stack:
        s.add(rel.as_posix())


sys.addaudithook(_audit)


@contextlib.contextmanager
def recording():
    """Collect the repo files opened for reading inside the block."""
    s: set[str] = set()
    _stack.append(s)
    try:
        yield s
    finally:
        _stack.pop()


def memo(fn):
    """Cache a shared computation across figures in one build.

    The files the first call read are credited to every later caller too, so each figure's
    recorded inputs stay complete. Results are deep-copied, so a figure can't change another's.
    """
    cache: dict = {}

    @functools.wraps(fn)
    def wrapper(*args, **kw):
        key = (args, tuple(sorted(kw.items())))
        if key not in cache:
            with recording() as reads:
                val = fn(*args, **kw)
            cache[key] = (val, frozenset(reads))
        val, reads = cache[key]
        for s in _stack:
            s.update(reads)
        return copy.deepcopy(val)

    return wrapper


# ------------------------------------------------------------------ hashing

def _bytes(p: Path) -> bytes:
    # Line endings normalised so a Windows checkout hashes the same as a Mac one.
    return p.read_bytes().replace(b"\r\n", b"\n")


def file_hash(p: Path) -> str:
    return "sha256:" + hashlib.sha256(_bytes(p)).hexdigest()[:16]


def code_files(fd: FigDir) -> list[Path]:
    files = [fd.path / "figure.py"]
    if (fd.path / "figure.html").exists():
        files.append(fd.path / "figure.html")
    files += sorted(LIB.rglob("*.py")) + [ROOT / d for d in CODE_DEPS]
    return [f for f in files if f.exists()]


def code_hash(fd: FigDir) -> str:
    h = hashlib.sha256()
    for f in code_files(fd):
        h.update(f.relative_to(ROOT).as_posix().encode() + b"\0" + _bytes(f) + b"\0")
    return "sha256:" + h.hexdigest()[:16]


def spec_hash(spec: dict) -> str:
    body = copy.deepcopy(spec)
    body.get("build", {}).pop("spec", None)
    canon = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canon.encode()).hexdigest()[:16]


# ------------------------------------------------------------------ report config and discovery

def report() -> dict:
    cfg = tomllib.loads(REPORT.read_text())
    cfg.setdefault("retired", [])
    ids = [s["id"] for s in cfg["sections"]]
    if "appendix" not in ids:
        cfg["sections"].append({"id": "appendix", "title": "Appendix"})
    return cfg


def discover() -> list[FigDir]:
    out = []
    for p in sorted(FIGURES.iterdir()) if FIGURES.exists() else []:
        if not p.is_dir() or p.name.startswith((".", "_")):
            continue
        m = DIR_RE.match(p.name)
        fid = f"{m.group(1)}{m.group(2)}" if m else p.name.split("-")[0]
        out.append(FigDir(id=fid, slug=m.group(3) if m else p.name, path=p))
    return out


def load_module(fd: FigDir):
    name = f"viz_figure_{fd.id}"
    spec = importlib.util.spec_from_file_location(name, fd.path / "figure.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ cleaning

def clean(x: Any) -> Any:
    """Plain JSON types; floats to 6 significant figures so platforms agree byte for byte."""
    if type(x).__name__ in ("NAType", "NaTType"):
        return None
    if hasattr(x, "item") and not isinstance(x, (str, bytes, dict, list, tuple)) and getattr(x, "ndim", 0) == 0:
        x = x.item()
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if x is None or isinstance(x, (bool, str)):
        return x
    if isinstance(x, numbers.Integral):
        return int(x)
    if isinstance(x, numbers.Real):
        f = float(x)
        if math.isnan(f) or math.isinf(f):
            return None
        return float(f"{f:.6g}")
    raise BuildError(f"can't put a {type(x).__name__} in a spec: {x!r}")


def table(data: Any) -> dict | None:
    if data is None:
        return None
    if hasattr(data, "to_dict") and hasattr(data, "columns"):
        cols = [str(c) for c in data.columns]
        rows = data.astype(object).where(data.notna(), None).values.tolist()
        return {"columns": cols, "rows": clean(rows)}
    if isinstance(data, list) and data and isinstance(data[0], dict):
        cols = list(data[0].keys())
        return {"columns": cols, "rows": clean([[r.get(c) for c in cols] for r in data])}
    raise BuildError("Figure.data must be a DataFrame or a list of dicts")


def fill(text: str, facts: dict, where: str) -> str:
    try:
        return text.format_map(facts)
    except KeyError as e:
        raise BuildError(f"{where} uses {{{e.args[0]}}}, but build() returned no fact with that name") from None
    except (ValueError, IndexError) as e:
        raise BuildError(f"{where}: bad placeholder ({e}). Write literal braces as {{{{ and }}}}") from None


# ------------------------------------------------------------------ build

def build_one(fd: FigDir) -> dict:
    """Run one generator and return its spec (not yet written)."""
    prev = json.loads(fd.spec_path.read_text()) if fd.spec_path.exists() else None
    with recording() as reads:
        mod = load_module(fd)
        meta = dict(getattr(mod, "META", None) or {})
        if not meta:
            raise BuildError(f"{fd.rel}/figure.py has no META")
        kind = meta.get("kind", "echarts")
        if kind not in KINDS:
            raise BuildError(f"{fd.id}: kind must be one of {KINDS}, not {kind!r}")
        if kind == "snapshot":
            if not prev:
                raise BuildError(f"{fd.id} is a snapshot but has no spec.json to keep")
            fig = Figure(option=prev.get("option"), dial=prev.get("dial"), facts=prev.get("facts") or {})
            data = prev.get("data")
        else:
            build = getattr(mod, "build", None)
            fig = build() if build else Figure()
            if not isinstance(fig, Figure):
                raise BuildError(f"{fd.id}: build() must return viz.kit.Figure, not {type(fig).__name__}")
            data = table(fig.data)
    if kind == "echarts" and not fig.option:
        raise BuildError(f"{fd.id}: build() returned no option")
    if kind == "html" and not (fd.path / "figure.html").exists():
        raise BuildError(f"{fd.id}: kind 'html' needs a figure.html next to figure.py")

    facts = clean(fig.facts or {})
    spec = {
        "id": fd.id,
        "kind": kind,
        "title": fill(meta.get("title", ""), facts, f"{fd.id} title"),
        "section": meta.get("section", "appendix"),
        "order": meta.get("order", 100),
        "caption": fill(meta.get("caption", ""), facts, f"{fd.id} caption"),
        "notes": [fill(n, facts, f"{fd.id} note") for n in meta.get("notes", [])],
        "height": int((meta.get("height") or (prev or {}).get("height") or DEFAULT_HEIGHT) if kind == "snapshot"
                      else (fig.height or meta.get("height", DEFAULT_HEIGHT))),
        "author": meta.get("author", ""),
        "source": meta.get("source", ""),
        "path": fd.rel,
        "option": clean(fig.option) if fig.option else None,
        "dial": clean(fig.dial) if fig.dial else None,
        "data": data,
        "facts": facts,
        "build": {
            "inputs": {r: file_hash(ROOT / r) for r in sorted(reads) if not r.startswith(fd.rel + "/spec.json")},
            "code": code_hash(fd),
        },
    }
    spec["build"]["spec"] = spec_hash(spec)
    return spec


def dumps(spec: dict) -> str:
    return json.dumps(spec, indent=1, ensure_ascii=False) + "\n"


def build(ids: list[str] | None = None, quiet: bool = False) -> int:
    figs = discover()
    want = {i.upper() for i in ids} if ids else None
    failures = 0
    for fd in figs:
        if want and fd.id not in want:
            continue
        try:
            spec = build_one(fd)
        except Exception as e:  # report and keep going, so one bad figure doesn't block the rest
            failures += 1
            print(f"  FAIL {fd.id}: {e}", file=sys.stderr)
            continue
        text = dumps(spec)
        old = fd.spec_path.read_text() if fd.spec_path.exists() else None
        if text != old:
            fd.spec_path.write_text(text)
            if not quiet:
                print(f"  wrote {fd.rel}/spec.json")
        elif not quiet:
            print(f"  unchanged {fd.id}")
    if want:
        missing = want - {f.id for f in figs}
        for m in sorted(missing):
            failures += 1
            print(f"  FAIL {m}: no folder viz/figures/{m}-*", file=sys.stderr)
    write_gallery()
    if not quiet:
        print(f"  wrote {GALLERY.relative_to(ROOT)}")
    return failures


# ------------------------------------------------------------------ gallery

def css_vars() -> str:
    t = theme.TOKENS
    pairs = {
        "--page": ("#f4f3ef", "#111110"), "--surface": t["@ink-surface"], "--ink": t["@ink-primary"],
        "--ink2": t["@ink-secondary"], "--muted": t["@ink-muted"], "--grid": t["@ink-grid"], "--axis": t["@ink-axis"],
        "--mid": t["@mid"], "--accent": t["@s0"], "--warn": t["@warning"],
        "--hair": ("rgba(11,11,11,0.09)", "rgba(255,255,255,0.09)"),
        "--hover": ("rgba(11,11,11,0.05)", "rgba(255,255,255,0.07)"),
        "--flag-bg": ("#fdf3dc", "#3a2e12"), "--flag-ink": ("#7a5200", "#f3cf7a"),
    }
    light = "".join(f"{k}:{v[0]};" for k, v in pairs.items())
    dark = "".join(f"{k}:{v[1]};" for k, v in pairs.items())
    return (f":root{{color-scheme:light;{light}}}"
            f"@media (prefers-color-scheme: dark){{:root:not([data-theme=\"light\"]){{color-scheme:dark;{dark}}}}}"
            f":root[data-theme=\"dark\"]{{color-scheme:dark;{dark}}}")


def _e(s: str) -> str:
    return html.escape(s or "", quote=True)


def card(spec: dict, people: dict) -> str:
    fid = spec["id"]
    who = people.get(fid[0], "")
    flags = ""
    if spec["kind"] == "snapshot":
        flags = "<span class='flag' title='Copied from an export. Nobody can rebuild it until its generator is written.'>Snapshot, no generator</span>"
    dial = ""
    if spec.get("dial"):
        d = spec["dial"]
        btns = "".join(f"<button type='button' data-step='{i}' aria-pressed='{str(i == d.get('initial', 0)).lower()}'>{_e(s)}</button>"
                       for i, s in enumerate(d["steps"]))
        dial = f"<div class='dial' role='group' aria-label='{_e(d.get('label', ''))}'><span>{_e(d.get('label', ''))}</span>{btns}</div>"
    if spec["kind"] == "html":
        body = f"<div class='chart html' data-id='{fid}' style='height:{spec['height']}px'><iframe title='{_e(spec['title'])}' loading='lazy'></iframe></div>"
    else:
        body = f"<div class='chart' data-id='{fid}' style='height:{spec['height']}px' role='img' aria-label='{_e(spec['title'])}'></div>"
    notes = ""
    if spec["notes"]:
        items = "".join(f"<li>{_e(n)}</li>" for n in spec["notes"])
        notes = f"<details class='notes'><summary>Notes ({len(spec['notes'])})</summary><ul>{items}</ul></details>"
    inputs = spec["build"]["inputs"]
    src_rows = "".join(f"<li><code>{_e(k)}</code></li>" for k in inputs) or "<li>none recorded</li>"
    source = (f"<details class='src'><summary>Source</summary><p>Generator <code>{_e(spec['path'])}/figure.py</code></p>"
              + (f"<p>{_e(spec['source'])}</p>" if spec.get("source") else "")
              + f"<p>Reads</p><ul>{src_rows}</ul></details>")
    can_export = spec["kind"] != "html"
    actions = ("<button type='button' data-act='copy' class='primary'>Copy image</button>"
               "<button type='button' data-act='png'>PNG</button><button type='button' data-act='svg'>SVG</button>"
               if can_export else "")
    if spec.get("data"):
        actions += "<button type='button' data-act='csv'>CSV</button>"
    return (f"<article class='fig' id='{fid}' data-id='{fid}' data-search='{_e((fid + ' ' + spec['title'] + ' ' + spec['caption']).lower())}'>"
            f"<header class='fig-head'><button type='button' class='chip' data-copy='{fid}' title='Copy ID'>{fid}</button>"
            f"<span class='who'>{_e(who)}</span>{flags}</header>"
            f"<h3>{_e(spec['title'])}</h3>{dial}{body}"
            f"<p class='caption'>{_e(spec['caption'])}</p>"
            f"<footer class='fig-foot'><div class='actions'>{actions}</div>{source}</footer>{notes}</article>")


def write_gallery() -> bool:
    """Write viz/gallery.html if it changed. Returns True if it was rewritten."""
    page = gallery_html()
    if GALLERY.exists() and GALLERY.read_text() == page:
        return False
    GALLERY.write_text(page)
    return True


def gallery_html() -> str:
    cfg = report()
    people = cfg.get("people", {})
    specs = []
    for fd in discover():
        if fd.spec_path.exists():
            s = json.loads(fd.spec_path.read_text())
            if s.get("kind") == "html":
                s["html"] = (fd.path / "figure.html").read_text()
            specs.append(s)
    order = {s["id"]: i for i, s in enumerate(cfg["sections"])}
    specs.sort(key=lambda s: (order.get(s["section"], len(order)), s.get("order", 100), s["id"]))

    sections_html, nav = [], []
    for sec in cfg["sections"]:
        members = [s for s in specs if s["section"] == sec["id"]]
        if not members:
            continue
        nav.append(f"<li><a href='#sec-{sec['id']}'>{_e(sec['title'])}</a><ol>"
                   + "".join(f"<li><a href='#{s['id']}'><b>{s['id']}</b> {_e(s['title'])}</a></li>" for s in members)
                   + "</ol></li>")
        sections_html.append(f"<section class='sec' id='sec-{sec['id']}'><h2>{_e(sec['title'])}"
                             f"<span class='count'>{len(members)}</span></h2>"
                             + "".join(card(s, people) for s in members) + "</section>")
    unknown = [s for s in specs if s["section"] not in order]
    if unknown:
        sections_html.append("<section class='sec' id='sec-unplaced'><h2>Unplaced</h2>"
                             + "".join(card(s, people) for s in unknown) + "</section>")

    font_b64 = base64.b64encode(FONT.read_bytes()).decode()
    payload = {"theme": theme.as_json(), "figures": specs, "font": font_b64}
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
    echarts_js = ECHARTS.read_text()
    js = (KIT / "page" / "gallery.js").read_text()
    for name, src in (("echarts", echarts_js), ("gallery.js", js)):
        if "</script" in src.lower():
            raise BuildError(f"{name} contains </script>, can't inline it")
    snapshots = sum(1 for s in specs if s["kind"] == "snapshot")
    stats = f"{len(specs)} figures" + (f" · {snapshots} snapshots" if snapshots else "")
    vals = {"FONT": font_b64, "VARS": css_vars(), "CSS": (KIT / "page" / "gallery.css").read_text(),
            "NAV": "".join(nav), "SECTIONS": "".join(sections_html), "STATS": _e(stats),
            "ECHARTS": echarts_js, "DATA": data, "JS": js}
    template = (KIT / "page" / "template.html").read_text()
    # One pass over the template, so text inside a value is never treated as a placeholder.
    return re.sub(r"\{\{([A-Z]+)\}\}", lambda m: vals[m.group(1)], template)
