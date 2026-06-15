"""Bottleneck visuals for the optimization ladder.

The cycle chart shows *that* cycles fell; the utilization chart shows the
machine filling up. These four charts answer "what was actually limiting each
rung" and show that the binding constraint *moves*:

    serialization  ->  memory/load  ->  scheduling  ->  VALU throughput

All numbers are derived from the emitted-kernel traces so issue density is
self-consistent (ops/cycle == 1.0 for the scalar rungs). Baseline therefore
uses its equivalent scalar-kernel trace, matching trace_visuals.py.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from .presentation_rows import load_presentation_rows
from .trace_visuals import ENGINE_ORDER, summarize_trace


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "cycles.csv"
CHARTS = RESULTS / "charts"

PEAK = sum(slots for _e, slots, _c in ENGINE_ORDER)  # 23 issue slots / cycle
ENGINE_SLOTS = {e: s for e, s, _c in ENGINE_ORDER}
ENGINE_COLOR = {e: c for e, _s, c in ENGINE_ORDER}
ENGINE_LABEL = {"alu": "ALU", "valu": "VALU", "load": "Load", "store": "Store", "flow": "Flow"}

PHASES = [
    (0, 1, "Remove work", "#dbeafe"),
    (1, 2, "Specialize", "#dcfce7"),
    (2, 3, "Vectorize", "#fef3c7"),
    (3, 5, "Schedule + temps", "#ede9fe"),
    (5, 7, "Cache + tune", "#ccfbf1"),
]

# Bottleneck regimes: (first_stage, last_stage, name, sub, color).
REGIMES = [
    (0, 2, "Serialized", "scalar issue width", "#64748b"),
    (3, 3, "Vectorized", "SIMD active", "#0f766e"),
    (4, 4, "False deps", "one temp namespace", "#f59e0b"),
    (5, 5, "Temp-banked", "parallel work exposed", "#2563eb"),
    (6, 7, "VALU throughput", "cache and tune", "#7c3aed"),
]


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _load_rows():
    return load_presentation_rows(CSV_PATH)


def collect(rows):
    """Per-stage machine-behavior data from the traces."""
    data = []
    for row in rows:
        summary = summarize_trace(Path(row["trace"]))
        oc = summary["op_counts"]
        cyc = summary["cycles"]
        engine_ops = {e: oc.get(e, 0) for e in ENGINE_SLOTS}
        total = sum(engine_ops.values())
        data.append(
            {
                "stage": int(row["stage"]),
                "name": row["name"],
                "cycles": cyc,
                "ops": total,
                "opc": total / cyc,
                "engine_ops": engine_ops,
                "engine_opc": {e: engine_ops[e] / cyc for e in ENGINE_SLOTS},
            }
        )
    return data


def _header(parts, title, subtitle):
    parts.extend(
        [
            f'<text x="36" y="46" font-family="Arial, sans-serif" font-size="28" font-weight="700" fill="#111827">{_esc(title)}</text>',
            f'<text x="36" y="72" font-family="Arial, sans-serif" font-size="15" fill="#475569">{_esc(subtitle)}</text>',
        ]
    )


def _phase_bands(parts, x_for, top, chart_h):
    # Phase backdrop behind the plot, with the label lifted into its own tag
    # chip above the plot so it never covers near-top data markers.
    for start, end, label, fill in PHASES:
        x1 = x_for(start)
        x2 = x_for(end)
        parts.extend(
            [
                f'<rect x="{x1:.1f}" y="{top:.1f}" width="{x2 - x1:.1f}" height="{chart_h + 10:.1f}" fill="{fill}" opacity="0.48"/>',
                f'<rect x="{x1:.1f}" y="{top - 48}" width="{x2 - x1:.1f}" height="22" fill="{fill}" opacity="0.7"/>',
                f'<text x="{(x1 + x2) / 2:.1f}" y="{top - 33}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#334155">{_esc(label)}</text>',
            ]
        )


def _stage_axis(parts, data, x_for, top, chart_h):
    for d in data:
        x = x_for(d["stage"])
        parts.append(
            f'<text x="{x:.1f}" y="{top + chart_h + 22}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#111827">{d["stage"]}</text>'
        )
    parts.append(
        f'<text x="{x_for(0) + (x_for(len(data) - 1) - x_for(0)) / 2:.1f}" y="{top + chart_h + 46}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">checkpoint</text>'
    )


def _regime_for(stage):
    for first, last, name, _sub, color in REGIMES:
        if first <= stage <= last:
            return name, color
    return "", "#94a3b8"


# --------------------------------------------------------------------------- #
# Chart 1: issue density vs. machine peak
# --------------------------------------------------------------------------- #
def issue_density_svg(data, path):
    width, height = 1280, 720
    left, right, top, bottom = 92, 60, 136, 132
    chart_w = width - left - right
    chart_h = height - top - bottom
    n = len(data)
    pad = 36  # inset so edge bars sit inside the plot, clear of the y-axis
    inner = chart_w - 2 * pad

    def x_for(i):
        return left + pad + inner * i / (n - 1)

    def y_for(v):
        return top + chart_h * (1 - v / PEAK)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
    ]
    _header(
        parts,
        "Issue Density vs. Machine Peak",
        "Ops issued per cycle vs. the 23-slot peak",
    )
    _phase_bands(parts, x_for, top, chart_h)

    # Grid + y labels.
    for v in (0, 5, 10, 15, 20):
        y = y_for(v)
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{v}</text>',
            ]
        )
    parts.append(
        f'<text x="24" y="{top + chart_h / 2:.1f}" transform="rotate(-90 24 {top + chart_h / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">ops issued per cycle</text>'
    )

    # Bars.
    bar_w = (inner / (n - 1)) * 0.56
    for d in data:
        x = x_for(d["stage"])
        _name, color = _regime_for(d["stage"])
        y = y_for(d["opc"])
        bh = top + chart_h - y
        parts.append(
            f'<rect x="{x - bar_w / 2:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" rx="2" fill="{color}" opacity="0.9"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{y - 6:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#111827">{d["opc"]:.1f}</text>'
        )

    # Axes.
    parts.extend(
        [
            f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
        ]
    )
    # Peak ceiling line.
    yp = y_for(PEAK)
    parts.extend(
        [
            f'<line x1="{left}" y1="{yp:.1f}" x2="{left + chart_w}" y2="{yp:.1f}" stroke="#dc2626" stroke-width="1.6" stroke-dasharray="7 4"/>',
            f'<text x="{left + chart_w - 6:.1f}" y="{yp + 18:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#dc2626">peak issue width = {PEAK} ops/cycle</text>',
        ]
    )

    _stage_axis(parts, data, x_for, top, chart_h)

    # Callout on the false-dependency break.
    vliw_stage = 5
    pre_stage = 4
    d_vliw = data[vliw_stage]
    x9 = x_for(vliw_stage)
    y9 = y_for(d_vliw["opc"])
    pre_pct = data[pre_stage]["opc"] / PEAK * 100.0
    post_pct = d_vliw["opc"] / PEAK * 100.0
    parts.extend(
        [
            f'<rect x="{x9 - 250:.1f}" y="{y9 - 18:.1f}" width="196" height="34" rx="5" fill="#ffffff" stroke="#cbd5e1"/>',
            f'<text x="{x9 - 240:.1f}" y="{y9 - 3:.1f}" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">Temp banks: {data[pre_stage]["opc"]:.1f} → {d_vliw["opc"]:.1f} ops/cyc</text>',
            f'<text x="{x9 - 240:.1f}" y="{y9 + 11:.1f}" font-family="Arial, sans-serif" font-size="11" fill="#475569">{pre_pct:.0f}% → {post_pct:.0f}% of peak issue width</text>',
            f'<line x1="{x9 - 54:.1f}" y1="{y9 - 1:.1f}" x2="{x9 - bar_w / 2:.1f}" y2="{y9:.1f}" stroke="#64748b" stroke-width="1.2"/>',
        ]
    )

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


# --------------------------------------------------------------------------- #
# Chart 2: shifting-bottleneck band
# --------------------------------------------------------------------------- #
def shifting_bottleneck_svg(data, path):
    width, height = 1280, 460
    left, right, top = 92, 60, 150
    chart_w = width - left - right
    n = len(data)

    def x_for(i):
        return left + chart_w * i / (n - 1)

    band_y = top
    band_h = 92

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
    ]
    _header(
        parts,
        "The Bottleneck Keeps Moving",
        "The binding constraint at each rung",
    )

    # Phase labels above the band, aligned to the cycle/utilization charts.
    for start, end, label, fill in PHASES:
        x1 = x_for(start)
        x2 = x_for(end)
        parts.extend(
            [
                f'<rect x="{x1:.1f}" y="{band_y - 24}" width="{x2 - x1:.1f}" height="18" fill="{fill}" opacity="0.55"/>',
                f'<text x="{(x1 + x2) / 2:.1f}" y="{band_y - 11}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#334155">{_esc(label)}</text>',
            ]
        )

    half = (x_for(1) - x_for(0)) / 2
    for first, last, name, sub, color in REGIMES:
        x1 = x_for(first) - half
        x2 = x_for(last) + half
        cx = (x1 + x2) / 2
        # Representative ops/cycle range for this regime.
        opcs = [d["opc"] for d in data if first <= d["stage"] <= last]
        lo, hi = min(opcs), max(opcs)
        metric = f"{lo:.1f} ops/cyc" if abs(hi - lo) < 0.05 else f"{lo:.1f} → {hi:.1f} ops/cyc"
        box_w = x2 - x1
        # Size each text row so it fits inside its box (single-rung regimes are
        # checkpoint wide, so a fixed font would overflow into neighbors).
        name_fs = max(11, min(18, (box_w - 16) / (0.62 * len(name))))
        metric_fs = max(11, min(13, (box_w - 16) / (0.5 * len(metric))))
        parts.extend(
            [
                f'<rect x="{x1:.1f}" y="{band_y:.1f}" width="{box_w:.1f}" height="{band_h}" rx="6" fill="{color}" opacity="0.16" stroke="{color}" stroke-width="1.5"/>',
                f'<text x="{cx:.1f}" y="{band_y + 30:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{name_fs:.1f}" font-weight="700" fill="{color}">{_esc(name)}</text>',
                f'<text x="{cx:.1f}" y="{band_y + 52:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#334155">{_esc(sub)}</text>',
                f'<text x="{cx:.1f}" y="{band_y + 76:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="{metric_fs:.1f}" font-weight="700" fill="#111827">{_esc(metric)}</text>',
            ]
        )

    # Transition arrows between regimes, labeled with the unlocking rung.
    transitions = [
        (2, 3, "vectorize"),
        (4, 5, "temp banks"),
        (5, 6, "tree cache"),
    ]
    arrow_y = band_y + band_h + 30
    parts.append(
        '<defs><marker id="arr" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto">'
        '<path d="M0,0 L7,3 L0,6 Z" fill="#475569"/></marker></defs>'
    )
    for a, b, label in transitions:
        xa = x_for(a) + half
        parts.extend(
            [
                f'<line x1="{xa - 26:.1f}" y1="{arrow_y:.1f}" x2="{xa + 26:.1f}" y2="{arrow_y:.1f}" stroke="#475569" stroke-width="1.6" marker-end="url(#arr)"/>',
                f'<text x="{xa:.1f}" y="{arrow_y + 20:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-style="italic" fill="#475569">{_esc(label)}</text>',
            ]
        )

    # Stage ruler under the band.
    ruler_y = arrow_y + 44
    parts.append(
        f'<line x1="{left}" y1="{ruler_y:.1f}" x2="{left + chart_w}" y2="{ruler_y:.1f}" stroke="#cbd5e1" stroke-width="1"/>'
    )
    for d in data:
        x = x_for(d["stage"])
        parts.extend(
            [
                f'<circle cx="{x:.1f}" cy="{ruler_y:.1f}" r="3" fill="#94a3b8"/>',
                f'<text x="{x:.1f}" y="{ruler_y + 20:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#111827">{d["stage"]}</text>',
            ]
        )
    parts.append(
        f'<text x="{left + chart_w / 2:.1f}" y="{ruler_y + 42:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">checkpoint</text>'
    )

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


# --------------------------------------------------------------------------- #
# Chart 3: work vs. time
# --------------------------------------------------------------------------- #
def work_vs_time_svg(data, path):
    width, height = 1280, 720
    left, right, top, bottom = 100, 150, 136, 132
    chart_w = width - left - right
    chart_h = height - top - bottom
    n = len(data)

    values = [d["ops"] for d in data] + [d["cycles"] for d in data]
    min_log = math.floor(math.log10(min(values)))
    max_log = math.ceil(math.log10(max(values)))

    def x_for(i):
        return left + chart_w * i / (n - 1)

    def y_for(v):
        lv = math.log10(v)
        return top + chart_h * (max_log - lv) / (max_log - min_log)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
    ]
    _header(
        parts,
        "Work vs. Time",
        "Total ops issued (work) vs. cycles (time)",
    )
    _phase_bands(parts, x_for, top, chart_h)

    for exponent in range(min_log, max_log + 1):
        v = 10 ** exponent
        y = y_for(v)
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{v:,}</text>',
            ]
        )
    parts.extend(
        [
            f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
            f'<text x="26" y="{top + chart_h / 2:.1f}" transform="rotate(-90 26 {top + chart_h / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">count, log scale</text>',
        ]
    )

    ops_pts = [(x_for(d["stage"]), y_for(d["ops"])) for d in data]
    cyc_pts = [(x_for(d["stage"]), y_for(d["cycles"])) for d in data]

    # Shade the gap between work and time = scheduling gain.
    gap = (
        " ".join(f"{x:.1f},{y:.1f}" for x, y in ops_pts)
        + " "
        + " ".join(f"{x:.1f},{y:.1f}" for x, y in reversed(cyc_pts))
    )
    parts.append(f'<polygon points="{gap}" fill="#0f766e" opacity="0.10"/>')

    for pts, color, label in (
        (ops_pts, "#7c3aed", "ops issued (work)"),
        (cyc_pts, "#1d4ed8", "cycles (time)"),
    ):
        attr = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        parts.append(
            f'<polyline points="{attr}" fill="none" stroke="{color}" stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        for x, y in pts:
            parts.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{color}" stroke="#f8fafc" stroke-width="1.5"/>'
            )
        ex, ey = pts[-1]
        parts.append(
            f'<text x="{ex + 10:.1f}" y="{ey + 4:.1f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="{color}">{_esc(label)}</text>'
        )

    _stage_axis(parts, data, x_for, top, chart_h)

    # Annotations.
    # 1) coincident scalar region.
    x2 = x_for(1)
    parts.extend(
        [
            f'<text x="{x2:.1f}" y="{y_for(data[1]["ops"]) - 12:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" fill="#334155">ops = cycles (1 op/cycle)</text>',
        ]
    )
    # 2) work-flat / cycles-falling region. Park the box in the open gap to the
    # right of the schedule stage -- between the flat work line and the falling
    # cycles line -- so it never sits on top of either line or its markers.
    schedule_stage = 5
    prior_stage = 4
    xm = x_for(schedule_stage)
    ym = (
        y_for(data[schedule_stage]["ops"]) + y_for(data[schedule_stage]["cycles"])
    ) / 2
    box_x = xm + 24
    box_y = ym - 17
    cycle_ratio = data[prior_stage]["cycles"] / data[schedule_stage]["cycles"]
    parts.extend(
        [
            f'<rect x="{box_x:.1f}" y="{box_y:.1f}" width="210" height="34" rx="5" fill="#ffffff" stroke="#cbd5e1"/>',
            f'<text x="{box_x + 10:.1f}" y="{box_y + 15:.1f}" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#111827">false deps fixed, {cycle_ratio:.1f}x fewer cycles</text>',
            f'<text x="{box_x + 10:.1f}" y="{box_y + 27:.1f}" font-family="Arial, sans-serif" font-size="11" fill="#0f766e">more parallel issue from similar work</text>',
        ]
    )

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


# --------------------------------------------------------------------------- #
# Chart 4: per-stage op composition (100% stacked)
# --------------------------------------------------------------------------- #
def op_composition_svg(data, path):
    width, height = 1280, 720
    left, right, top, bottom = 92, 60, 164, 132
    chart_w = width - left - right
    chart_h = height - top - bottom
    n = len(data)
    pad = 36  # inset so edge bars sit inside the plot, clear of the y-axis
    inner = chart_w - 2 * pad

    def x_for(i):
        return left + pad + inner * i / (n - 1)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
    ]
    _header(
        parts,
        "Composition of Issued Work",
        "Share of issued ops by engine",
    )

    # Bars are always full height (100% stacked), so the ops/cycle magnitude
    # gets its own row above the plot, with the phase label lifted into its own
    # tag chip a row higher still, clear of both the bars and the ops/cyc row.
    for start, end, label, fill in PHASES:
        x1 = x_for(start)
        x2 = x_for(end)
        parts.extend(
            [
                f'<rect x="{x1:.1f}" y="{top:.1f}" width="{x2 - x1:.1f}" height="{chart_h + 10:.1f}" fill="{fill}" opacity="0.48"/>',
                f'<rect x="{x1:.1f}" y="{top - 60}" width="{x2 - x1:.1f}" height="22" fill="{fill}" opacity="0.7"/>',
                f'<text x="{(x1 + x2) / 2:.1f}" y="{top - 45}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" font-weight="700" fill="#334155">{_esc(label)}</text>',
            ]
        )
    parts.append(
        f'<text x="{left - 12}" y="{top - 9}" text-anchor="end" font-family="Arial, sans-serif" font-size="10.5" fill="#64748b">ops/cyc</text>'
    )

    for pct in (0, 25, 50, 75, 100):
        y = top + chart_h * (1 - pct / 100)
        parts.extend(
            [
                f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" stroke="#e2e8f0" stroke-width="1"/>',
                f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#64748b">{pct}%</text>',
            ]
        )
    parts.append(
        f'<text x="24" y="{top + chart_h / 2:.1f}" transform="rotate(-90 24 {top + chart_h / 2:.1f})" text-anchor="middle" font-family="Arial, sans-serif" font-size="13" fill="#475569">share of issued ops</text>'
    )

    bar_w = (inner / (n - 1)) * 0.56
    for d in data:
        x = x_for(d["stage"])
        total = d["ops"] or 1
        y_cursor = top + chart_h
        for engine, _slots, color in ENGINE_ORDER:
            share = d["engine_ops"][engine] / total
            seg_h = chart_h * share
            if seg_h <= 0:
                continue
            parts.append(
                f'<rect x="{x - bar_w / 2:.1f}" y="{y_cursor - seg_h:.1f}" width="{bar_w:.1f}" height="{seg_h:.1f}" fill="{color}" opacity="0.92"/>'
            )
            y_cursor -= seg_h
        # Total ops/cycle above the bar so magnitude isn't lost.
        parts.append(
            f'<text x="{x:.1f}" y="{top - 9:.1f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#111827">{d["opc"]:.1f}</text>'
        )

    parts.extend(
        [
            f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" stroke="#334155" stroke-width="1.2"/>',
        ]
    )

    _stage_axis(parts, data, x_for, top, chart_h)

    # Legend.
    lx = left
    ly = height - 54
    for engine, _slots, color in ENGINE_ORDER:
        parts.extend(
            [
                f'<rect x="{lx:.1f}" y="{ly:.1f}" width="14" height="14" rx="2" fill="{color}"/>',
                f'<text x="{lx + 20:.1f}" y="{ly + 12:.1f}" font-family="Arial, sans-serif" font-size="13" fill="#334155">{_esc(ENGINE_LABEL[engine])}</text>',
            ]
        )
        lx += 120

    parts.append("</svg>")
    path.write_text("\n".join(parts))
    return path


def write_all():
    rows = _load_rows()
    data = collect(rows)
    CHARTS.mkdir(parents=True, exist_ok=True)
    return [
        issue_density_svg(data, CHARTS / "issue_density.svg"),
        shifting_bottleneck_svg(data, CHARTS / "shifting_bottleneck.svg"),
        work_vs_time_svg(data, CHARTS / "work_vs_time.svg"),
        op_composition_svg(data, CHARTS / "op_composition.svg"),
    ]


def main():
    for p in write_all():
        print(p)


if __name__ == "__main__":
    main()
