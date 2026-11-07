"""Colour tokens. Figures name colours by token ("@s0", "@ink-primary"), never by hex.

Each token maps to (light, dark). The gallery swaps them when the theme changes, so one spec
works in both modes. The categorical slots are the colour-blind-checked reference palette the
team's pages already use, in their validated order. Slots 0-2 pass the all-pairs check, which
is why a figure gets at most three colours plus grey.

Token forms a spec may use:
    "@s0"            a token
    "@s0/0.15"       the same colour at 15% opacity
    "@goodbad:0.8"   a point on a scale, 0 to 1 (see SCALES)
Tokens also work inside function strings (renderItem, formatter): they are replaced before the
function is compiled.
"""
from __future__ import annotations

import re

TOKENS: dict[str, tuple[str, str]] = {
    # Categorical, fixed order. Use them in this order; never cycle past @s7.
    "@s0": ("#2a78d6", "#3987e5"),  # blue
    "@s1": ("#eb6834", "#d95926"),  # orange
    "@s2": ("#1baf7a", "#199e70"),  # aqua
    "@s3": ("#eda100", "#c98500"),  # yellow
    "@s4": ("#e87ba4", "#d55181"),  # magenta
    "@s5": ("#008300", "#008300"),  # green
    "@s6": ("#6250d6", "#9085e9"),  # violet
    "@s7": ("#e34948", "#e66767"),  # red
    # Status. Only when the colour means good / warning / serious / critical.
    "@good": ("#0ca30c", "#0ca30c"),
    "@warning": ("#fab219", "#fab219"),
    "@serious": ("#ec835a", "#ec835a"),
    "@critical": ("#d03b3b", "#d03b3b"),
    # Ink and chrome.
    "@ink-primary": ("#0b0b0b", "#f0efec"),
    "@ink-secondary": ("#52514e", "#c3c2b7"),
    "@ink-muted": ("#898781", "#898781"),
    "@ink-grid": ("#e8e7e1", "#2a2a28"),
    "@ink-axis": ("#c3c2b7", "#3d3d39"),
    "@ink-surface": ("#fcfcfb", "#1a1a19"),
    "@mid": ("#f0efec", "#383835"),
    # Marks that give context but aren't the story.
    "@context": ("#c4c2ba", "#4f4e49"),
    "@context-strong": ("#9c9a92", "#77756e"),
    # Text placed on a fill.
    "@on-strong": ("#ffffff", "#ffffff"),   # on @s0, @s6, @s7, @critical
    "@on-bright": ("#1a1a19", "#1a1a19"),   # on @warning and @s3, which stay bright in dark mode
    "@on-pale": ("#0b0b0b", "#f0efec"),     # on scale cells (@goodbad, @seq) and @context
    # Diverging red arm and sequential blue, from the reference palette.
    "@div-r1": ("#f0a8a8", "#7a2626"),
    "@div-r2": ("#e07676", "#a33030"),
    "@div-r3": ("#d03b3b", "#c94444"),
    "@div-r4": ("#9c2020", "#e07676"),
    "@seq100": ("#cde2fb", "#0d366b"),
    "@seq150": ("#b7d3f6", "#104281"),
    "@seq200": ("#9ec5f4", "#184f95"),
    "@seq250": ("#86b6ef", "#1c5cab"),
    "@seq300": ("#6da7ec", "#256abf"),
    "@seq350": ("#5598e7", "#2a78d6"),
    "@seq400": ("#3987e5", "#3987e5"),
    "@seq450": ("#2a78d6", "#5598e7"),
    "@seq500": ("#256abf", "#6da7ec"),
    "@seq550": ("#1c5cab", "#86b6ef"),
    "@seq600": ("#184f95", "#9ec5f4"),
    "@seq650": ("#104281", "#b7d3f6"),
    "@seq700": ("#0d366b", "#cde2fb"),
}

# Continuous scales for table cells: "@name:x" with x from 0 to 1. Light-mode stops are pale so
# @on-pale text stays readable; dark-mode stops are deep for the same reason.
SCALES: dict[str, dict[str, list[str]]] = {
    # 0 = worst of the field, 1 = best. Cells always carry their number, so colour is never alone.
    "goodbad": {"light": ["#f3a99d", "#f1ebdb", "#93d4ae"], "dark": ["#7c2f28", "#353229", "#1e6444"]},
    # Plain magnitude, pale to mid blue.
    "seq": {"light": ["#eef4fc", "#a9cbf4"], "dark": ["#1c2735", "#24589a"]},
}

# Each model keeps one colour in every figure. Anything not listed is @context grey.
ENTITY: dict[str, str] = {
    "sonnet55": "@s0",
    "haiku55": "@s1",
    "haiku45": "@s1",   # same family as Haiku 5.5; draw it hollow to tell them apart
    "glm53": "@s2",
    "opus55": "@s6",
}


def entity(model: str) -> str:
    """The token for a model's colour."""
    return ENTITY.get(model, "@context")


TOKEN_RE = re.compile(r"@[a-z][a-z0-9-]*(?::-?[0-9.]+)?(?:/[0-9.]+)?")
_FORM = re.compile(r"^(@[a-z][a-z0-9-]*)(?::(-?[0-9.]+))?(?:/([0-9.]+))?$")


def known(token: str) -> bool:
    """True if a token string is one the gallery can resolve."""
    m = _FORM.match(token)
    if not m:
        return False
    name, x, _ = m.groups()
    if x is not None:
        return name[1:] in SCALES
    return name in TOKENS


def as_json() -> dict:
    return {"tokens": {k: list(v) for k, v in TOKENS.items()}, "scales": SCALES}
