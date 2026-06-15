"""Rasterize every generated chart/trace SVG to PNG for the slide deck.

The chart modules build SVG markup (the natural format for hand-authored
vector graphics), but the presentation embeds PNGs -- they render identically
across PowerPoint/Keynote/Google Slides, whereas SVG support in PPTX is
inconsistent. This converts each SVG under results/charts and
results/trace_visuals to a sibling .png at 2x scale for crisp slides.

Requires `rsvg-convert` (librsvg) on PATH.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SVG_DIRS = [RESULTS / "charts", RESULTS / "trace_visuals"]
SCALE = 2  # 2x raster for retina-crisp slides


def convert_all(scale: int = SCALE) -> list[Path]:
    if shutil.which("rsvg-convert") is None:
        raise RuntimeError(
            "rsvg-convert not found on PATH. Install librsvg "
            "(macOS: brew install librsvg)."
        )

    outputs: list[Path] = []
    for svg_dir in SVG_DIRS:
        if not svg_dir.is_dir():
            continue
        for svg in sorted(svg_dir.glob("*.svg")):
            png = svg.with_suffix(".png")
            subprocess.run(
                ["rsvg-convert", "-z", str(scale), str(svg), "-o", str(png)],
                check=True,
            )
            outputs.append(png)
    return outputs


def main():
    for png in convert_all():
        print(png)


if __name__ == "__main__":
    main()
