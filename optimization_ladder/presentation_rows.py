"""Presentation-facing optimization ladder rows."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "cycles.csv"

def load_raw_rows(path: Path = CSV_PATH) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f))


def load_presentation_rows(path: Path = CSV_PATH) -> list[dict[str, str]]:
    """Return rows for the revised slide narrative."""

    return load_raw_rows(path)
