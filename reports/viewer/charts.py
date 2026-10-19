"""SVG charts for reports. Each function returns an SVG string.

Colours come from CSS variables in theme.css, so the same SVG works in light and dark mode.
A chart's colour is set by wrapping it in an element with class s1, s2 or s3 (Figure and
Panel do this). Hover text lives in data-tip attributes, read by app.js.
"""
from .components import esc, fmt_auroc

SURFACE_GAP = 2
BAR_RADIUS = 4


def _fmt(x: float) -> str:
    return f"{x:.1f}".rstrip("0").rstrip(".") if x != int(x) else str(int(x))


def _round_top_bar(x: float, y: float, w: float, h: float) -> str:
    """A bar with a rounded top and a square base."""
    r = min(BAR_RADIUS, w / 2, h)
    return (f"M{x:.1f},{y + h:.1f} L{x:.1f},{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} "
            f"L{x + w - r:.1f},{y:.1f} Q{x + w:.1f},{y:.1f} {x + w:.1f},{y + r:.1f} L{x + w:.1f},{y + h:.1f} Z")


def score_histogram(name: str, honest: list[float], attack: list[float], ymax: int = 30) -> str:
    """Counts of runs per suspicion score (0.0 to 1.0 in steps of 0.1).

    Honest runs are gray bars, attack runs are coloured bars, side by side in each bin.
    """
    w, h = 320, 190
    left, right, top, bottom = 34, 8, 22, 34
    pw, ph = w - left - right, h - top - bottom
    head = ymax * 1.15  # headroom so the count above the tallest bar fits
    bins = [round(i / 10, 1) for i in range(11)]
    slot = pw / len(bins)
    bar_w = min(10.0, (slot - 3 - SURFACE_GAP) / 2)
    y = lambda count: top + ph - ph * count / head

    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" '
             f'aria-label="Score counts for {esc(name)}: honest runs and attack runs">']
    for tick in range(0, ymax + 1, 10):
        cls = "axis" if tick == 0 else "grid"
        parts.append(f'<line class="{cls}" x1="{left}" x2="{w - right}" y1="{y(tick):.1f}" y2="{y(tick):.1f}"/>')
        parts.append(f'<text class="muted" x="{left - 6}" y="{y(tick) + 4:.1f}" text-anchor="end">{tick}</text>')
    for i, b in enumerate(bins):
        n_honest = sum(round(s, 1) == b for s in honest)
        n_attack = sum(round(s, 1) == b for s in attack)
        cx = left + slot * i + slot / 2
        for count, cls, dx in ((n_honest, "bar-honest", -bar_w - SURFACE_GAP / 2), (n_attack, "bar-attack", SURFACE_GAP / 2)):
            if count:
                bh = ph * count / head
                parts.append(f'<path class="{cls}" d="{_round_top_bar(cx + dx, y(count), bar_w, bh)}"/>')
                if count >= 10:  # label only the tall bars; the tooltip and table carry the rest
                    parts.append(f'<text class="val" x="{cx + dx + bar_w / 2:.1f}" y="{y(count) - 4:.1f}" text-anchor="middle">{count}</text>')
        if i % 2 == 0:
            parts.append(f'<text class="muted" x="{cx:.1f}" y="{h - 18}" text-anchor="middle">{_fmt(b)}</text>')
        tip = f"Score {_fmt(b)}|honest runs: {n_honest}|attack runs: {n_attack}"
        parts.append(f'<rect class="hit" x="{left + slot * i:.1f}" y="{top}" width="{slot:.1f}" height="{ph}" data-tip="{esc(name)} · {esc(tip)}"/>')
    parts.append(f'<text class="muted" x="{w - right}" y="{h - 3}" text-anchor="end">suspicion score</text>')
    parts.append(f'<text class="muted" x="{left - 6}" y="{top - 8}" text-anchor="end">runs</text>')
    parts.append("</svg>")
    return "".join(parts)


def safety_lines(name: str, budgets: list[float], raw: list[float], stripped: list[float], unreliable_below: float,
                 first_label: str = "raw", second_label: str = "stripped") -> str:
    """Safety (0 to 1) at each audit budget for two variants of one monitor.

    The first variant is a solid line with filled dots, the second is dashed with hollow dots.
    The gray band marks budgets that threshold on less than one whole honest run.
    """
    w, h = 320, 215
    left, right, top, bottom = 34, 64, 18, 44
    pw, ph = w - left - right, h - top - bottom
    slot = pw / len(budgets)
    x = lambda i: left + slot * i + slot / 2
    y = lambda v: top + ph - ph * v

    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="Safety by audit budget for {esc(name)}">']
    n_band = sum(b < unreliable_below for b in budgets)
    if n_band:
        parts.append(f'<rect class="band" x="{left}" y="{top}" width="{slot * n_band:.1f}" height="{ph}"/>')
        parts.append(f'<text class="muted" x="{left + slot * n_band / 2:.1f}" y="{top + ph - 7}" text-anchor="middle" style="font-size:10px">too few honest runs</text>')
    for tick in (0, 0.5, 1.0):
        cls = "axis" if tick == 0 else "grid"
        parts.append(f'<line class="{cls}" x1="{left}" x2="{w - right}" y1="{y(tick):.1f}" y2="{y(tick):.1f}"/>')
        parts.append(f'<text class="muted" x="{left - 6}" y="{y(tick) + 4:.1f}" text-anchor="end">{tick:g}</text>')
    for i, b in enumerate(budgets):
        parts.append(f'<text class="muted" x="{x(i):.1f}" y="{h - 26}" text-anchor="middle" style="font-size:10px">{_fmt(b)}%</text>')
    parts.append(f'<text class="muted" x="{left + pw / 2:.1f}" y="{h - 8}" text-anchor="middle">audit budget</text>')
    parts.append(f'<text class="muted" x="{left - 6}" y="{top - 6}" text-anchor="end">safety</text>')

    for values, dashed in ((raw, False), (stripped, True)):
        pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
        parts.append(f'<polyline class="line{" dashed" if dashed else ""}" points="{pts}"/>')
    for values, hollow in ((raw, False), (stripped, True)):
        for i, v in enumerate(values):
            parts.append(f'<circle class="pt{" hollow" if hollow else ""}" cx="{x(i):.1f}" cy="{y(v):.1f}" r="{4 if not hollow else 3.5}"/>')

    # Direct labels at the right end, nudged apart if the two lines finish close together.
    ys = [y(raw[-1]), y(stripped[-1])]
    if abs(ys[0] - ys[1]) < 13:
        mid = (ys[0] + ys[1]) / 2
        ys = [mid - 7, mid + 7] if ys[0] <= ys[1] else [mid + 7, mid - 7]
    for label, ly in ((first_label, ys[0]), (second_label, ys[1])):
        parts.append(f'<text x="{x(len(budgets) - 1) + 10:.1f}" y="{ly + 4:.1f}">{esc(label)}</text>')

    for i, b in enumerate(budgets):
        tip = f"{_fmt(b)}% audit budget|{first_label}: {raw[i]:.2f}|{second_label}: {stripped[i]:.2f}"
        if b < unreliable_below:
            tip += "|few honest runs, treat with care"
        parts.append(f'<g class="hitg"><line class="xhair" x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{top}" y2="{top + ph}"/>'
                     f'<rect class="hit" x="{left + slot * i:.1f}" y="{top}" width="{slot:.1f}" height="{ph}" data-tip="{esc(name)} · {esc(tip)}"/></g>')
    parts.append("</svg>")
    return "".join(parts)


def dumbbell(rows: list[tuple[str, str, float, float]], first_label: str = "raw", second_label: str = "stripped",
             xmin: float = 0.5, xmax: float = 1.0, baseline_note: str = "0.5 = guessing") -> str:
    """One row per item: a filled dot for the first value, a hollow dot for the second, joined by a bar.

    rows: (label, colour slot, first value, second value).
    """
    row_h = 54
    w, left, right, top = 640, 150, 40, 30
    h = top + row_h * len(rows) + 30
    pw = w - left - right
    x = lambda v: left + pw * (v - xmin) / (xmax - xmin)

    parts = [f'<svg class="chart" viewBox="0 0 {w} {h}" role="img" aria-label="{esc(first_label)} and {esc(second_label)} values per monitor">']
    ticks = [xmin + i * 0.1 for i in range(int(round((xmax - xmin) / 0.1)) + 1)]
    for t in ticks:
        parts.append(f'<line class="grid" x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top - 8}" y2="{h - 28}"/>')
        parts.append(f'<text class="muted" x="{x(t):.1f}" y="{h - 12}" text-anchor="middle">{t:.1f}</text>')
    parts.append(f'<text class="muted" x="{x(xmin):.1f}" y="{top - 14}" text-anchor="start">{esc(baseline_note)}</text>')
    for i, (label, slot, first, second) in enumerate(rows):
        cy = top + row_h * i + row_h / 2
        lo, hi = sorted((first, second))
        parts.append(f'<g class="{esc(slot)}"><circle class="mark" cx="14" cy="{cy:.1f}" r="5"/>'
                     f'<text class="val" x="28" y="{cy + 4:.1f}">{esc(label)}</text>'
                     f'<line class="link" x1="{x(lo):.1f}" x2="{x(hi):.1f}" y1="{cy:.1f}" y2="{cy:.1f}"/>'
                     f'<circle class="pt" cx="{x(first):.1f}" cy="{cy:.1f}" r="7"/>'
                     f'<circle class="pt hollow" cx="{x(second):.1f}" cy="{cy:.1f}" r="6.5"/>')
        right_val, left_val = (first, second) if first >= second else (second, first)
        parts.append(f'<text class="val" x="{x(right_val) + 14:.1f}" y="{cy + 4:.1f}">{fmt_auroc(right_val)}</text>'
                     f'<text class="val" x="{x(left_val) - 14:.1f}" y="{cy + 4:.1f}" text-anchor="end">{fmt_auroc(left_val)}</text>')
        tip = f"{label}|{first_label}: {first:.3f}|{second_label}: {second:.3f}|change: {second - first:+.3f}"
        parts.append(f'<rect class="hit" x="0" y="{cy - row_h / 2:.1f}" width="{w}" height="{row_h}" data-tip="{esc(tip)}"/></g>')
    parts.append("</svg>")
    return "".join(parts)
