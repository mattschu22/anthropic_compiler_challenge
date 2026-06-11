"""Per-engine machine utilization across the optimization ladder.

The line chart in ``chart.py`` shows *that* cycles fell. This chart shows *why*:
each engine's busy fraction over the same fixed workload, so the two structural
unlocks become visible. VALU goes from idle to active at stage 5 (SIMD), and
every engine jumps together at stage 9 (dependency-aware VLIW scheduling).
"""

from __future__ import annotations

import csv
from pathlib import Path

from .trace_visuals import ENGINE_ORDER, summarize_trace


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "cycles.csv"
SVG_PATH = RESULTS / "charts" / "utilization_ladder.svg"

# Reuse the same phase framing as the cycle chart so the two slides line up.
PHASES = [
    (0, 2, "Remove work", "#dbeafe"),
    (2, 4, "Specialize", "#dcfce7"),
    (4, 8, "Expose parallelism", "#fef3c7"),
    (8, 10, "Schedule machine", "#ede9fe"),
]

ENGINE_LABEL = {
    "alu": "ALU",
    "valu": "VALU",
    "load": "Load",
    "store": "Store",
    "flow": "Flow",
}


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _load_rows():
    with CSV_PATH.open() as f:
        return list(csv.DictReader(f))


def _collect_util(rows):
    """Return {engine: [util_per_stage]} as percentages."""
    series = {engine: [] for engine, _slots, _color in ENGINE_ORDER}
    for row in rows:
        summary = summarize_trace(Path(row["trace"]))
        for engine, _slots, _color in ENGINE_ORDER:
            series[engine].append(summary["engine_util"].get(engine, 0.0) * 100.0)
    return series


def write_svg(rows, series, path: Path = SVG_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1280
    height = 720
    left = 92
    right = 150  # room for end-of-line engine labels
    top = 116
    bottom = 132
    chart_w = width - left - right
    chart_h = height - top - bottom

    n = len(rows)
    y_max = 100.0

    def x_for(i: int) -> float:
        if n == 1:
            return left + chart_w / 2
        return left + chart_w * i / (n - 1)

    def y_for(pct: float) -> float:
        return top + chart_h * (1 - pct / y_max)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="36" y="46" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#111827">Machine Utilization Across the Ladder</text>',
        '<text x="36" y="72" font-family="Arial, sans-serif" font-size="15" fill="#475569">Per-engine busy fraction · same fixed workload · the same two rungs that drop cycles also fill the machine</text>',
    ]

    # Phase bands behind the plot.
    for start, end, label, fill in PHASES:
        x1 = x_for(start)
        x2 = x_for(end)
        parts.extend(
            [
                f'<rect x="{x1:.1f}" y="{top - 26}" width="{x2 - x1:.1f}" height="{chart_h + 36}" fill="{fill}" opacity="0.48"/>',
                f'<text x="{(x1 + x2) / 2:.1f}" y="{top - 10}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#334155">{_esc(label)}</text>',
            ]
        )

    # Axes and horizontal grid at 0/25/50/75/100%.
    parts.extend(
        [
            f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
        ]
    )
    for pct in (0, 25, 50, 75, 100):
        y = y_for(pct)
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{pct}%</text>',
            ]
        )
    parts.append(
        f'<text x="24" y="{top + chart_h / 2:.1f}" transform="rotate(-90 24 {top + chart_h / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">engine busy fraction</text>'
    )

    # One line per engine, drawn in ENGINE_ORDER so ALU/VALU sit on top.
    end_labels = []
    for engine, _slots, color in ENGINE_ORDER:
        values = series[engine]
        pts = [(x_for(i), y_for(v)) for i, v in enumerate(values)]
        point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(
            f'<polyline points="{point_attr}" fill="none" stroke="{color}" stroke-width="3" stroke-linejoin="round" stroke-linecap="round" opacity="0.95"/>'
        )
        for x, y in pts:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="{color}" stroke="#f8fafc" stroke-width="1.4"/>'
            )
        end_labels.append((pts[-1][1], engine, color, values[-1]))

    # De-overlap the end-of-line labels, then draw them in the right margin.
    end_labels.sort()
    min_gap = 18
    for i in range(1, len(end_labels)):
        prev_y = end_labels[i - 1][0]
        if end_labels[i][0] - prev_y < min_gap:
            end_labels[i] = (prev_y + min_gap, *end_labels[i][1:])
    label_x = left + chart_w + 12
    for y, engine, color, value in end_labels:
        parts.append(
            f'<text x="{label_x:.1f}" y="{y + 4:.1f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="{color}">{_esc(ENGINE_LABEL[engine])} {value:.0f}%</text>'
        )

    # Stage tick labels along the x axis.
    for i, row in enumerate(rows):
        x = x_for(i)
        parts.append(
            f'<text x="{x:.1f}" y="{top + chart_h + 22}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#111827">{_esc(row["stage"])}</text>'
        )
    parts.append(
        f'<text x="{left + chart_w / 2:.1f}" y="{top + chart_h + 46}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">checkpoint</text>'
    )

    # Two interpretive callouts on the structural unlocks.
    box_w = 196
    box_h = 32
    for idx, anchor_engine, title, sub, dx, dy in (
        (5, "valu", "SIMD turns VALU on", "8 inputs per vector op", 18, -128),
        (9, "alu", "VLIW fills every engine", "cross-engine packing", -box_w - 14, -box_h - 18),
    ):
        x = x_for(idx)
        # Anchor on the engine this rung most directly affects.
        y = y_for(series[anchor_engine][idx])
        bx = x + dx
        by = y + dy
        anchor_y = by + box_h / 2 if dy > 0 else by + box_h
        parts.extend(
            [
                f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{bx + (8 if dx > 0 else box_w - 8):.1f}" y2="{anchor_y:.1f}" stroke="#64748b" stroke-width="1.2"/>',
                f'<rect x="{bx:.1f}" y="{by:.1f}" width="{box_w}" height="{box_h}" rx="5" fill="#ffffff" stroke="#cbd5e1"/>',
                f'<text x="{bx + 12:.1f}" y="{by + 14:.1f}" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">{_esc(title)}</text>',
                f'<text x="{bx + 12:.1f}" y="{by + 27:.1f}" font-family="Arial, sans-serif" font-size="11" fill="#475569">{_esc(sub)}</text>',
            ]
        )

    parts.extend(
        [
            f'<text x="36" y="{height - 24}" font-family="Arial, sans-serif" font-size="13" fill="#64748b">Source: optimization_ladder/results/traces/*.json (busy engine-slots ÷ available engine-slots)</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts))
    return path


def main():
    rows = _load_rows()
    series = _collect_util(rows)
    out = write_svg(rows, series)
    print(out)


if __name__ == "__main__":
    main()
