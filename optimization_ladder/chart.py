"""Create a marked line chart from optimization-ladder cycle results."""

from __future__ import annotations

import csv
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "cycles.csv"
SVG_PATH = RESULTS / "charts" / "optimization_ladder.svg"

PHASES = [
    (0, 2, "Remove work", "#dbeafe"),
    (2, 4, "Specialize", "#dcfce7"),
    (4, 8, "Expose parallelism", "#fef3c7"),
    (8, 10, "Schedule machine", "#ede9fe"),
]


def _load_rows():
    with CSV_PATH.open() as f:
        rows = list(csv.DictReader(f))
    return rows


def _esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_svg(rows, path: Path = SVG_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 1280
    height = 720
    left = 92
    right = 56
    top = 98
    bottom = 150
    chart_w = width - left - right
    chart_h = height - top - bottom

    cycles = [int(r["cycles"]) for r in rows]
    min_log = math.floor(math.log10(min(cycles)))
    max_log = math.ceil(math.log10(max(cycles)))

    def x_for(i: int) -> float:
        if len(rows) == 1:
            return left + chart_w / 2
        return left + chart_w * i / (len(rows) - 1)

    def y_for(value: int) -> float:
        v = math.log10(value)
        return top + chart_h * (max_log - v) / (max_log - min_log)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="36" y="46" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#111827">Optimization Ladder</text>',
        '<text x="36" y="74" font-family="Arial, sans-serif" font-size="15" fill="#475569">Cumulative checkpoints · log-scaled cycles · fixed 10/16/256 workload</text>',
        '<text x="1132" y="46" text-anchor="end" font-family="Arial, sans-serif" font-size="14" fill="#475569">final speedup</text>',
        '<text x="1228" y="46" text-anchor="end" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#0f766e">124.8x</text>',
    ]

    # Phase bands behind the plot.
    for start, end, label, fill in PHASES:
        x1 = x_for(start)
        x2 = x_for(end)
        parts.extend(
            [
                f'<rect x="{x1:.1f}" y="{top - 34}" width="{x2 - x1:.1f}" height="{chart_h + 44}" fill="{fill}" opacity="0.48"/>',
                f'<text x="{(x1 + x2) / 2:.1f}" y="{top - 15}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#334155">{_esc(label)}</text>',
            ]
        )

    # Axes and log grid.
    parts.extend(
        [
            f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
        ]
    )
    for exponent in range(min_log, max_log + 1):
        value = 10**exponent
        y = y_for(value)
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{value:,}</text>',
            ]
        )
    parts.append(
        f'<text x="24" y="{top + chart_h / 2:.1f}" transform="rotate(-90 24 {top + chart_h / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">cycles, log scale</text>'
    )

    points = [(x_for(i), y_for(int(row["cycles"]))) for i, row in enumerate(rows)]
    point_attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area_attr = (
        f"{left:.1f},{top + chart_h:.1f} "
        + point_attr
        + f" {left + chart_w:.1f},{top + chart_h:.1f}"
    )
    parts.append(
        f'<polygon points="{area_attr}" fill="#bfdbfe" opacity="0.28"/>'
    )
    parts.append(
        f'<polyline points="{point_attr}" fill="none" stroke="#1d4ed8" stroke-width="3.6" stroke-linejoin="round" stroke-linecap="round"/>'
    )

    for idx, (row, (x, y)) in enumerate(zip(rows, points)):
        value = int(row["cycles"])
        marker_fill = "#0f766e" if idx >= 9 else "#2563eb"
        if idx == 8:
            marker_fill = "#f59e0b"
        parts.extend(
            [
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6.5" fill="{marker_fill}" stroke="#f8fafc" stroke-width="2"/>',
                f'<text x="{x:.1f}" y="{top + chart_h + 26}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#111827">{_esc(row["stage"])}</text>',
                f'<text x="{x:.1f}" y="{y - 12:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#111827">{value:,}</text>',
            ]
        )

    # Callouts for the two largest narrative inflection points.
    for idx, label, dx, dy in (
        (5, "SIMD: 8 lanes per vector", -106, -54),
        (9, "VLIW packing fills slots", -156, -48),
    ):
        x, y = points[idx]
        tx = x + dx
        ty = y + dy
        parts.extend(
            [
                f'<line x1="{x:.1f}" y1="{y - 8:.1f}" x2="{tx + 120:.1f}" y2="{ty + 16:.1f}" stroke="#64748b" stroke-width="1"/>',
                f'<rect x="{tx:.1f}" y="{ty:.1f}" width="206" height="30" rx="4" fill="#ffffff" stroke="#cbd5e1"/>',
                f'<text x="{tx + 10:.1f}" y="{ty + 20:.1f}" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">{_esc(label)}</text>',
            ]
        )

    # Legend-style checkpoint names. Kept below the plot so the line stays readable.
    legend_y = top + chart_h + 54
    col_w = chart_w / 4
    for idx, row in enumerate(rows):
        col = idx % 4
        line = idx // 4
        x = left + col * col_w
        y = legend_y + line * 22
        parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" font-size="12" fill="#334155">{_esc(row["stage"])}. {_esc(row["name"])}</text>'
        )

    parts.extend(
        [
            f'<text x="36" y="{height - 32}" font-family="Arial, sans-serif" font-size="13" fill="#64748b">Source: optimization_ladder/results/cycles.csv</text>',
            "</svg>",
        ]
    )
    path.write_text("\n".join(parts))
    return path


def main():
    rows = _load_rows()
    out = write_svg(rows)
    print(out)


if __name__ == "__main__":
    main()
