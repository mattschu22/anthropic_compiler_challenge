"""Generate compact Perfetto-style lane views for optimization checkpoints."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "cycles.csv"
TRACE_DIR = RESULTS / "traces"
OUT_DIR = RESULTS / "trace_visuals"

ENGINE_ORDER = [
    ("alu", 12, "#2563eb"),
    ("valu", 6, "#7c3aed"),
    ("load", 2, "#0f766e"),
    ("store", 2, "#dc2626"),
    ("flow", 1, "#f59e0b"),
]

STAGE_NOTES = {
    "00_baseline": "Mostly one scalar lane at a time; memory and branch work dominate.",
    "01_test_contract": "Final pass removes index update/store work; still scalar and memory-backed.",
    "02_scratch_indices": "Index memory traffic drops; compute lanes remain mostly serialized.",
    "03_fixed_layout": "Pointer/header work shrinks; trace still shows scalar execution.",
    "04_unroll": "Control overhead drops, but execution is still scalar-width.",
    "05_vectorize": "VALU lanes become active as eight inputs move together.",
    "06_tree_cache": "Load pressure falls on shallow tree depths.",
    "07_streaming_io": "Value address updates become a small streaming pattern.",
    "08_temp_banks": "Independent work is exposed and locally packed before global scheduling.",
    "09_vliw_schedule": "Many engine lanes fill together after dependency-aware scheduling.",
    "10_final_refinements": "Scheduler polish improves packing and shifts some VALU work to ALU.",
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


def _load_trace(path: Path):
    text = path.read_text()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # The original take-home simulator writes a comma after every event and
        # then closes the array. Perfetto accepts that trace shape through the
        # bundled watcher, so keep files untouched and parse leniently here.
        last_comma = text.rfind(",")
        last_bracket = text.rfind("]")
        if last_comma == -1 or last_bracket == -1 or last_comma > last_bracket:
            raise
        if text[last_comma + 1 : last_bracket].strip():
            raise
        return json.loads(text[:last_comma] + text[last_bracket:])


def summarize_trace(path: Path, bins: int = 280):
    data = _load_trace(path)
    tid_to_lane = {}
    lane_events = defaultdict(list)
    op_counts = defaultdict(int)
    max_ts = 0

    for event in data:
        if event.get("pid") != 0:
            continue
        if event.get("ph") == "M" and event.get("name") == "thread_name":
            name = event.get("args", {}).get("name", "")
            if "-" not in name:
                continue
            engine, slot = name.split("-", 1)
            if engine in {e[0] for e in ENGINE_ORDER}:
                tid_to_lane[event.get("tid")] = (engine, int(slot))
            continue
        if event.get("ph") != "X":
            continue
        dur = int(event.get("dur", 0))
        if dur <= 0:
            continue
        lane = tid_to_lane.get(event.get("tid"))
        if lane is None:
            continue
        ts = int(event.get("ts", 0))
        max_ts = max(max_ts, ts + dur)
        lane_events[lane].append((ts, dur, event.get("name", "")))
        op_counts[lane[0]] += 1

    max_ts = max(max_ts, 1)
    lane_bins = {}
    for lane, events in lane_events.items():
        values = [0] * bins
        for ts, dur, _name in events:
            start = min(bins - 1, int(ts * bins / max_ts))
            end = min(bins - 1, max(start, int((ts + dur) * bins / max_ts)))
            for i in range(start, end + 1):
                values[i] += 1
        lane_bins[lane] = values

    engine_util = {}
    for engine, slots, _color in ENGINE_ORDER:
        engine_util[engine] = op_counts[engine] / (max_ts * slots)

    return {
        "cycles": max_ts,
        "lane_bins": lane_bins,
        "op_counts": op_counts,
        "engine_util": engine_util,
        "bins": bins,
    }


def write_trace_svg(row, summary, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    width = 1280
    top = 132
    left = 150
    right = 44
    lane_h = 12
    lane_gap = 3
    engine_gap = 14
    timeline_w = width - left - right
    lane_count = sum(slots for _engine, slots, _color in ENGINE_ORDER)
    height = top + lane_count * (lane_h + lane_gap) + engine_gap * len(ENGINE_ORDER) + 112

    cycles = int(row["cycles"])
    speedup = float(row["speedup"])
    note = STAGE_NOTES.get(row["id"], row.get("claim", ""))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        f'<text x="34" y="42" font-family="Arial, sans-serif" font-size="25" font-weight="700" fill="#111827">{_esc(row["stage"])}. {_esc(row["name"])}</text>',
        f'<text x="34" y="68" font-family="Arial, sans-serif" font-size="14" fill="#475569">{cycles:,} cycles · {speedup:.2f}x over baseline</text>',
        f'<text x="34" y="92" font-family="Arial, sans-serif" font-size="14" fill="#334155">{_esc(note)}</text>',
        f'<line x1="{left}" y1="{top - 12}" x2="{left + timeline_w}" y2="{top - 12}" stroke="#cbd5e1" stroke-width="1"/>',
        f'<text x="{left}" y="{top - 18}" font-family="Arial, sans-serif" font-size="11" fill="#64748b">0</text>',
        f'<text x="{left + timeline_w}" y="{top - 18}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#64748b">{cycles:,} cycles</text>',
        f'<text x="34" y="{top - 18}" font-family="Arial, sans-serif" font-size="11" font-weight="700" fill="#64748b">engine lanes</text>',
    ]

    y = top
    bins = summary["bins"]
    bin_w = timeline_w / bins
    for engine, slots, color in ENGINE_ORDER:
        util = summary["engine_util"].get(engine, 0.0)
        # Vertically center the engine label against its block of slot lanes.
        block_h = slots * (lane_h + lane_gap) - lane_gap
        label_cy = y + block_h / 2
        parts.append(
            f'<text x="34" y="{label_cy + 1:.1f}" font-family="Arial, sans-serif" font-size="13" font-weight="700" fill="#111827">{engine.upper()}</text>'
        )
        parts.append(
            f'<text x="{left - 12}" y="{label_cy + 1:.1f}" text-anchor="end" font-family="Arial, sans-serif" font-size="11" fill="#64748b">{util * 100:.0f}%</text>'
        )
        for slot in range(slots):
            lane_y = y + slot * (lane_h + lane_gap)
            parts.append(
                f'<rect x="{left}" y="{lane_y}" width="{timeline_w}" height="{lane_h}" fill="#e2e8f0"/>'
            )
            values = summary["lane_bins"].get((engine, slot), [])
            if values:
                max_v = max(values) or 1
                run_start = None
                run_alpha = 0.0
                last_alpha = None
                for i, value in enumerate(values + [0]):
                    alpha = 0.0 if value == 0 else 0.28 + 0.62 * math.sqrt(value / max_v)
                    alpha_key = round(alpha, 2)
                    if value and run_start is None:
                        run_start = i
                        run_alpha = alpha
                        last_alpha = alpha_key
                    elif value and alpha_key == last_alpha:
                        continue
                    else:
                        if run_start is not None:
                            x = left + run_start * bin_w
                            w = max(1.0, (i - run_start) * bin_w)
                            parts.append(
                                f'<rect x="{x:.1f}" y="{lane_y}" width="{w:.1f}" height="{lane_h}" fill="{color}" opacity="{run_alpha:.2f}"/>'
                            )
                        run_start = i if value else None
                        run_alpha = alpha
                        last_alpha = alpha_key if value else None
        y += slots * (lane_h + lane_gap) + engine_gap

    # Compact utilization strip for slide scanning.
    strip_y = height - 68
    x = 34
    for engine, _slots, color in ENGINE_ORDER:
        util = summary["engine_util"].get(engine, 0.0)
        parts.extend(
            [
                f'<rect x="{x}" y="{strip_y}" width="130" height="8" fill="#e2e8f0"/>',
                f'<rect x="{x}" y="{strip_y}" width="{130 * min(util, 1):.1f}" height="8" fill="{color}"/>',
                f'<text x="{x}" y="{strip_y + 26}" font-family="Arial, sans-serif" font-size="11" fill="#334155">{engine} {util * 100:.1f}%</text>',
            ]
        )
        x += 160

    parts.extend(
        [
            f'<text x="34" y="{height - 18}" font-family="Arial, sans-serif" font-size="11" fill="#64748b">Derived from { _esc(Path(row["trace"]).name) }; full trace remains Perfetto-compatible.</text>',
            "</svg>",
        ]
    )
    out_path.write_text("\n".join(parts))
    return out_path


def write_all():
    rows = _load_rows()
    outputs = []
    for row in rows:
        trace = row.get("trace")
        if not trace:
            continue
        summary = summarize_trace(Path(trace))
        outputs.append(write_trace_svg(row, summary, OUT_DIR / f"{row['id']}.svg"))
    return outputs


def main():
    outputs = write_all()
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
