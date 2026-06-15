"""Run optimization-ladder checkpoints and record presentation-ready results."""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
from pathlib import Path
from typing import Any

from anthropic_compiler_challenge.problem_api import (
    Input,
    Machine,
    N_CORES,
    Tree,
    build_mem_image,
    reference_kernel2,
)

from .builders import (
    build_banked_vector_kernel,
    build_index_memory_kernel,
    build_optimized_kernel,
    build_scalar_scratch_kernel,
    build_scheduled_vector_ladder_kernel,
    build_vector_ladder_kernel,
)


BASELINE_CYCLES = 147_734
ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "configs"
RESULTS_DIR = ROOT / "results"


def _load_config(checkpoint: str | Path) -> dict[str, Any]:
    path = Path(checkpoint)
    if path.exists():
        config_path = path
    else:
        matches = sorted(CONFIG_DIR.glob(f"{checkpoint}*.json"))
        if not matches:
            matches = sorted(p for p in CONFIG_DIR.glob("*.json") if p.stem == checkpoint)
        if not matches:
            raise FileNotFoundError(f"no checkpoint config matched {checkpoint!r}")
        if len(matches) > 1:
            names = ", ".join(p.name for p in matches)
            raise ValueError(f"checkpoint {checkpoint!r} is ambiguous: {names}")
        config_path = matches[0]

    with config_path.open() as f:
        cfg = json.load(f)
    cfg["_config_path"] = str(config_path)
    return cfg


def _build_kernel(cfg: dict[str, Any], forest: Tree, inp: Input):
    kind = cfg["kind"]
    kwargs = dict(cfg.get("builder_args", {}))
    common = (forest.height, len(forest.values), len(inp.indices), inp.rounds)

    if kind == "index_memory":
        return build_index_memory_kernel(*common, **kwargs)
    if kind == "scalar_scratch":
        return build_scalar_scratch_kernel(*common, **kwargs)
    if kind == "vector_ladder":
        return build_vector_ladder_kernel(*common, **kwargs)
    if kind == "scheduled_vector_ladder":
        return build_scheduled_vector_ladder_kernel(*common, **kwargs)
    if kind == "banked_vector":
        return build_banked_vector_kernel(*common, **kwargs)
    if kind == "optimized":
        return build_optimized_kernel(*common, **kwargs)
    raise ValueError(f"unknown checkpoint kind={kind!r}")


def _close_trace(machine: Machine):
    if machine.trace is None:
        return
    machine.trace.write("]")
    machine.trace.close()
    machine.trace = None


def _run_machine_checkpoint(
    cfg: dict[str, Any],
    *,
    seed: int,
    trace: bool,
) -> dict[str, Any]:
    workload = cfg.get("workload", {})
    forest_height = int(workload.get("forest_height", 10))
    rounds = int(workload.get("rounds", 16))
    batch_size = int(workload.get("batch_size", 256))

    random.seed(seed)
    forest = Tree.generate(forest_height)
    inp = Input.generate(forest, batch_size, rounds)
    mem = build_mem_image(forest, inp)
    kb = _build_kernel(cfg, forest, inp)

    trace_path = None
    old_cwd = None
    if trace:
        trace_dir = RESULTS_DIR / "traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        trace_path = trace_dir / f"{cfg['id']}.json"
        old_cwd = Path.cwd()
        os.chdir(trace_dir)
        scratch_trace = trace_dir / "trace.json"
        if scratch_trace.exists():
            scratch_trace.unlink()

    try:
        machine = Machine(mem, kb.instrs, kb.debug_info(), n_cores=N_CORES, trace=trace)
        machine.enable_pause = False
        machine.enable_debug = False
        machine.run()
        _close_trace(machine)
    finally:
        if old_cwd is not None:
            os.chdir(old_cwd)

    if trace and trace_path is not None:
        scratch_trace = trace_path.parent / "trace.json"
        if scratch_trace.exists():
            if trace_path.exists():
                trace_path.unlink()
            scratch_trace.rename(trace_path)

    for ref_mem in reference_kernel2(mem):
        pass
    inp_values_p = ref_mem[6]
    correct = (
        machine.mem[inp_values_p : inp_values_p + len(inp.values)]
        == ref_mem[inp_values_p : inp_values_p + len(inp.values)]
    )
    if not correct:
        raise AssertionError(f"incorrect output for checkpoint {cfg['id']}")

    cycles = machine.cycle
    return {
        "id": cfg["id"],
        "stage": cfg["stage"],
        "name": cfg["name"],
        "claim": cfg["claim"],
        "kind": cfg["kind"],
        "cycles": cycles,
        "speedup": BASELINE_CYCLES / cycles,
        "instructions": len(kb.instrs),
        "correct": correct,
        "trace": str(trace_path) if trace_path is not None else "",
        "config": cfg["_config_path"],
    }


def run_checkpoint(
    checkpoint: str | Path,
    *,
    seed: int = 123,
    trace: bool = False,
) -> dict[str, Any]:
    """Run one checkpoint by id/stem/path and return a result row."""

    cfg = _load_config(checkpoint)
    if cfg["kind"] == "reported_baseline":
        trace_path = ""
        trace_cycles = ""
        instructions = ""
        if trace:
            trace_cfg = dict(cfg)
            trace_cfg["kind"] = cfg.get("trace_kind", "index_memory")
            trace_cfg["builder_args"] = dict(
                cfg.get("trace_builder_args", {"skip_final_index_store": False})
            )
            trace_row = _run_machine_checkpoint(trace_cfg, seed=seed, trace=True)
            trace_path = trace_row["trace"]
            trace_cycles = trace_row["cycles"]
            instructions = trace_row["instructions"]
        return {
            "id": cfg["id"],
            "stage": cfg["stage"],
            "name": cfg["name"],
            "claim": cfg["claim"],
            "kind": cfg["kind"],
            "cycles": BASELINE_CYCLES,
            "speedup": 1.0,
            "instructions": instructions,
            "correct": True,
            "trace": trace_path,
            "trace_cycles": trace_cycles,
            "config": cfg["_config_path"],
        }
    return _run_machine_checkpoint(cfg, seed=seed, trace=trace)


def run_all(
    *,
    seed: int = 123,
    trace_ids: set[str] | None = None,
    write_csv: bool = True,
) -> list[dict[str, Any]]:
    """Run all checkpoint configs in stage order."""

    trace_ids = trace_ids or set()
    rows = []
    for config_path in sorted(CONFIG_DIR.glob("*.json")):
        cfg = _load_config(config_path)
        rows.append(
            run_checkpoint(
                config_path,
                seed=seed,
                trace=("all" in trace_ids or cfg["id"] in trace_ids),
            )
        )

    rows.sort(key=lambda row: int(row["stage"]))
    if write_csv:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        csv_path = RESULTS_DIR / "cycles.csv"
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "stage",
                    "id",
                    "name",
                    "cycles",
                    "speedup",
                    "instructions",
                    "correct",
                    "kind",
                    "trace",
                    "trace_cycles",
                    "claim",
                    "config",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
    return rows


def _print_rows(rows: list[dict[str, Any]]):
    print("stage,id,cycles,speedup,name")
    for row in rows:
        print(
            f"{row['stage']},{row['id']},{row['cycles']},"
            f"{float(row['speedup']):.2f},{row['name']}"
        )


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", nargs="?", help="checkpoint id/stem/path")
    parser.add_argument("--all", action="store_true", help="run every checkpoint")
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--trace", action="append", default=[], help="checkpoint id to trace")
    parser.add_argument("--no-csv", action="store_true", help="do not write results/cycles.csv")
    args = parser.parse_args(argv)

    if args.all:
        rows = run_all(seed=args.seed, trace_ids=set(args.trace), write_csv=not args.no_csv)
    elif args.checkpoint:
        rows = [
            run_checkpoint(
                args.checkpoint,
                seed=args.seed,
                trace=("all" in set(args.trace) or args.checkpoint in set(args.trace)),
            )
        ]
    else:
        parser.error("provide a checkpoint or --all")
    _print_rows(rows)


if __name__ == "__main__":
    main()
