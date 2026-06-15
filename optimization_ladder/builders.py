"""Checkpoint builders for the cumulative optimization ladder.

These builders are intentionally separate from the submission ``KernelBuilder``.
They trade peak performance for clear, runnable checkpoints that support the
presentation narrative.
"""

from __future__ import annotations

from dataclasses import dataclass

from anthropic_compiler_challenge.kernel_builder import KernelBuilder
from anthropic_compiler_challenge.problem_api import DebugInfo, SCRATCH_SIZE, VLEN
from anthropic_compiler_challenge.scheduler import (
    chunk_wide_valu_bundles,
    pipeline_relaxed,
    pipeline_strict,
)


HASH_CONSTS = {
    "h0": 0x7ED55D16,
    "h1": 0xC761C23C,
    "h2": 0x165667B1,
    "h3": 0xD3A2646C,
    "h4": 0xFD7046C5,
    "h5": 0xB55A4F09,
    "m0": 0x1001,
    "m2": 0x21,
    "m4": 0x9,
}


class MiniKernelBuilder:
    """Small helper for readable checkpoint kernels."""

    def __init__(self):
        self.instrs = []
        self.scratch = {}
        self.scratch_debug = {}
        self.scratch_ptr = 0
        self.const_map = {}

    def debug_info(self):
        return DebugInfo(scratch_map=self.scratch_debug)

    def alloc(self, name=None, length=1):
        addr = self.scratch_ptr
        if name is not None:
            self.scratch[name] = addr
            self.scratch_debug[addr] = (name, length)
        self.scratch_ptr += length
        assert self.scratch_ptr <= SCRATCH_SIZE
        return addr

    def add(self, engine, slot_or_slots):
        if isinstance(slot_or_slots, list):
            slots = slot_or_slots
        else:
            slots = [slot_or_slots]
        self.instrs.append({engine: slots})

    def const(self, val, name=None):
        key = int(val) % (2**32)
        if key not in self.const_map:
            addr = self.alloc(name)
            self.add("load", ("const", addr, key))
            self.const_map[key] = addr
        return self.const_map[key]

    def patch_flow(self, instr_idx, slot):
        self.instrs[instr_idx]["flow"][0] = slot

    def schedule(self, mode: str, *, load_weight: int = -1, valu_weight: int = -1):
        """Replace the sequential instruction stream with a VLIW schedule."""

        if mode == "none":
            return

        body = []
        for instr in self.instrs:
            for engine, ops in instr.items():
                body.append((engine, ops))
        body = chunk_wide_valu_bundles(body, chunk_size=2)

        if mode == "strict":
            sched = pipeline_strict(
                body,
                load_weight=load_weight,
                valu_weight=valu_weight,
            )
        elif mode == "relaxed":
            sched = pipeline_relaxed(
                body,
                load_weight=load_weight,
                valu_weight=valu_weight,
                addr_bonus=2,
                bank_map={},
            )
        else:
            raise ValueError(f"unknown schedule mode {mode!r}")

        assert sched, "expected non-empty scheduled program"
        sched[0].setdefault("flow", []).append(("pause",))
        sched[-1].setdefault("flow", []).append(("pause",))
        self.instrs = sched


@dataclass(frozen=True)
class Workload:
    forest_height: int
    n_nodes: int
    batch_size: int
    rounds: int

    @property
    def forest_values_p(self):
        return 7

    @property
    def inp_indices_p(self):
        return self.forest_values_p + self.n_nodes

    @property
    def inp_values_p(self):
        return self.inp_indices_p + self.batch_size


def _scalar_hash(kb: MiniKernelBuilder, val, tmp1, tmp2, c):
    kb.add("alu", ("*", val, val, c["m0"]))
    kb.add("alu", ("+", val, val, c["h0"]))

    kb.add("alu", (">>", tmp1, val, c["shift_19"]))
    kb.add("alu", ("^", tmp2, val, c["h1"]))
    kb.add("alu", ("^", val, tmp1, tmp2))

    kb.add("alu", ("*", val, val, c["m2"]))
    kb.add("alu", ("+", val, val, c["h2"]))

    kb.add("alu", ("+", tmp1, val, c["h3"]))
    kb.add("alu", ("<<", tmp2, val, c["shift_9"]))
    kb.add("alu", ("^", val, tmp1, tmp2))

    kb.add("alu", ("*", val, val, c["m4"]))
    kb.add("alu", ("+", val, val, c["h4"]))

    kb.add("alu", (">>", tmp1, val, c["shift_16"]))
    kb.add("alu", ("^", tmp2, val, c["h5"]))
    kb.add("alu", ("^", val, tmp1, tmp2))


def _scalar_update_idx(kb: MiniKernelBuilder, idx, val, tmp1, bit, cond, c, *, wrap=True):
    kb.add("alu", ("&", bit, val, c["one"]))
    kb.add("alu", ("*", idx, idx, c["two"]))
    kb.add("alu", ("+", idx, idx, c["one"]))
    kb.add("alu", ("+", idx, idx, bit))
    if wrap:
        kb.add("alu", ("<", cond, idx, c["n_nodes"]))
        kb.add("flow", ("select", idx, cond, idx, c["zero"]))


def _scalar_consts(kb: MiniKernelBuilder, workload: Workload):
    c = {
        "zero": kb.const(0, "c0"),
        "one": kb.const(1, "c1"),
        "two": kb.const(2, "c2"),
        "shift_19": kb.const(19, "shift_19"),
        "shift_9": kb.const(9, "shift_9"),
        "shift_16": kb.const(16, "shift_16"),
        "n_nodes": kb.const(workload.n_nodes, "n_nodes"),
    }
    for name, val in HASH_CONSTS.items():
        c[name] = kb.const(val, name)
    return c


def build_index_memory_kernel(
    forest_height: int,
    n_nodes: int,
    batch_size: int,
    rounds: int,
    *,
    skip_final_index_store: bool = True,
):
    """Scalar loop kernel that still uses index memory between rounds."""

    workload = Workload(forest_height, n_nodes, batch_size, rounds)
    kb = MiniKernelBuilder()
    c = _scalar_consts(kb, workload)

    mem0 = kb.const(0, "mem_rounds_addr")
    mem1 = kb.const(1, "mem_n_nodes_addr")
    mem2 = kb.const(2, "mem_batch_addr")
    mem4 = kb.const(4, "mem_forest_ptr_addr")
    mem5 = kb.const(5, "mem_index_ptr_addr")
    mem6 = kb.const(6, "mem_value_ptr_addr")

    rounds_s = kb.alloc("rounds")
    n_nodes_s = kb.alloc("runtime_n_nodes")
    batch_s = kb.alloc("batch_size")
    forest_p = kb.alloc("forest_values_p")
    indices_p = kb.alloc("inp_indices_p")
    values_p = kb.alloc("inp_values_p")
    round_i = kb.alloc("round_i")
    batch_i = kb.alloc("batch_i")
    idx_addr = kb.alloc("idx_addr")
    val_addr = kb.alloc("val_addr")
    node_addr = kb.alloc("node_addr")
    idx = kb.alloc("idx")
    val = kb.alloc("val")
    node_val = kb.alloc("node_val")
    tmp1 = kb.alloc("tmp1")
    tmp2 = kb.alloc("tmp2")
    bit = kb.alloc("bit")
    cond = kb.alloc("cond")
    regular_rounds = kb.alloc("regular_rounds")

    kb.add("load", ("load", rounds_s, mem0))
    kb.add("load", ("load", n_nodes_s, mem1))
    kb.add("load", ("load", batch_s, mem2))
    kb.add("load", ("load", forest_p, mem4))
    kb.add("load", ("load", indices_p, mem5))
    kb.add("load", ("load", values_p, mem6))
    def emit_input_body(*, update_and_store_idx: bool):
        kb.add("alu", ("+", idx_addr, indices_p, batch_i))
        kb.add("alu", ("+", val_addr, values_p, batch_i))
        kb.add("load", ("load", idx, idx_addr))
        kb.add("load", ("load", val, val_addr))
        kb.add("alu", ("+", node_addr, forest_p, idx))
        kb.add("load", ("load", node_val, node_addr))
        kb.add("alu", ("^", val, val, node_val))
        _scalar_hash(kb, val, tmp1, tmp2, c)
        if update_and_store_idx:
            _scalar_update_idx(kb, idx, val, tmp1, bit, cond, {**c, "n_nodes": n_nodes_s})
        kb.add("store", ("store", val_addr, val))
        if update_and_store_idx:
            kb.add("store", ("store", idx_addr, idx))

    if skip_final_index_store:
        # Run rounds 0..rounds-2 normally, then a separate final value-only pass.
        kb.add("alu", ("-", regular_rounds, rounds_s, c["one"]))
        kb.add("alu", ("+", round_i, c["zero"], c["zero"]))
        round_loop = len(kb.instrs)
        kb.add("alu", ("+", batch_i, c["zero"], c["zero"]))
        batch_loop = len(kb.instrs)
        emit_input_body(update_and_store_idx=True)
        kb.add("alu", ("+", batch_i, batch_i, c["one"]))
        kb.add("alu", ("<", cond, batch_i, batch_s))
        kb.add("flow", ("cond_jump", cond, batch_loop))
        kb.add("alu", ("+", round_i, round_i, c["one"]))
        kb.add("alu", ("<", cond, round_i, regular_rounds))
        kb.add("flow", ("cond_jump", cond, round_loop))

        kb.add("alu", ("+", batch_i, c["zero"], c["zero"]))
        final_batch_loop = len(kb.instrs)
        emit_input_body(update_and_store_idx=False)
        kb.add("alu", ("+", batch_i, batch_i, c["one"]))
        kb.add("alu", ("<", cond, batch_i, batch_s))
        kb.add("flow", ("cond_jump", cond, final_batch_loop))
    else:
        kb.add("alu", ("+", round_i, c["zero"], c["zero"]))
        round_loop = len(kb.instrs)
        kb.add("alu", ("+", batch_i, c["zero"], c["zero"]))
        batch_loop = len(kb.instrs)
        emit_input_body(update_and_store_idx=True)
        kb.add("alu", ("+", batch_i, batch_i, c["one"]))
        kb.add("alu", ("<", cond, batch_i, batch_s))
        kb.add("flow", ("cond_jump", cond, batch_loop))
        kb.add("alu", ("+", round_i, round_i, c["one"]))
        kb.add("alu", ("<", cond, round_i, rounds_s))
        kb.add("flow", ("cond_jump", cond, round_loop))
    return kb


def build_scalar_scratch_kernel(
    forest_height: int,
    n_nodes: int,
    batch_size: int,
    rounds: int,
    *,
    fixed_layout: bool,
    unroll_rounds: bool,
):
    """Scalar kernel with per-input indices kept in scratch."""

    workload = Workload(forest_height, n_nodes, batch_size, rounds)
    kb = MiniKernelBuilder()
    c = _scalar_consts(kb, workload)

    if fixed_layout:
        forest_p = kb.const(workload.forest_values_p, "forest_values_p")
        values_p = kb.const(workload.inp_values_p, "inp_values_p")
    else:
        mem4 = kb.const(4, "mem_forest_ptr_addr")
        mem6 = kb.const(6, "mem_value_ptr_addr")
        forest_p = kb.alloc("forest_values_p")
        values_p = kb.alloc("inp_values_p")
        kb.add("load", ("load", forest_p, mem4))
        kb.add("load", ("load", values_p, mem6))

    idx_slots = [kb.alloc(f"idx_{i}") for i in range(batch_size)]
    val_addr = kb.alloc("val_addr")
    node_addr = kb.alloc("node_addr")
    val = kb.alloc("val")
    node_val = kb.alloc("node_val")
    tmp1 = kb.alloc("tmp1")
    tmp2 = kb.alloc("tmp2")
    bit = kb.alloc("bit")
    cond = kb.alloc("cond")

    for idx in idx_slots:
        kb.add("alu", ("+", idx, c["zero"], c["zero"]))

    def emit_input_step(input_i: int, round_i: int | None):
        idx = idx_slots[input_i]
        if fixed_layout:
            value_addr = kb.const(workload.inp_values_p + input_i, f"val_addr_{input_i}")
        else:
            off = kb.const(input_i, f"input_off_{input_i}")
            kb.add("alu", ("+", val_addr, values_p, off))
            value_addr = val_addr

        kb.add("load", ("load", val, value_addr))
        kb.add("alu", ("+", node_addr, forest_p, idx))
        kb.add("load", ("load", node_val, node_addr))
        kb.add("alu", ("^", val, val, node_val))
        _scalar_hash(kb, val, tmp1, tmp2, c)
        kb.add("store", ("store", value_addr, val))

        if round_i is None:
            _scalar_update_idx(kb, idx, val, tmp1, bit, cond, c, wrap=True)
            return

        if round_i == rounds - 1:
            return
        depth = round_i % (forest_height + 1)
        if depth == forest_height:
            kb.add("alu", ("+", idx, c["zero"], c["zero"]))
        else:
            _scalar_update_idx(kb, idx, val, tmp1, bit, cond, c, wrap=False)

    if unroll_rounds:
        for r in range(rounds):
            for i in range(batch_size):
                emit_input_step(i, r)
    else:
        round_ctr = kb.alloc("round_i")
        rounds_s = kb.const(rounds, "rounds")
        kb.add("alu", ("+", round_ctr, c["zero"], c["zero"]))
        round_loop = len(kb.instrs)
        for i in range(batch_size):
            emit_input_step(i, None)
        kb.add("alu", ("+", round_ctr, round_ctr, c["one"]))
        kb.add("alu", ("<", cond, round_ctr, rounds_s))
        kb.add("flow", ("cond_jump", cond, round_loop))

    return kb


def _vector_consts(kb: MiniKernelBuilder, workload: Workload):
    c = _scalar_consts(kb, workload)
    c.update(
        {
            "forest_p": kb.const(workload.forest_values_p, "forest_values_p"),
            "values_p": kb.const(workload.inp_values_p, "inp_values_p"),
        }
    )
    vectors = {}
    for scalar_name, vector_name in (
        ("zero", "v_zero"),
        ("one", "v_ones"),
        ("two", "v_twos"),
        ("forest_p", "v_forest_p"),
        ("h0", "hash_hex_0"),
        ("h1", "hash_hex_1"),
        ("h2", "hash_hex_2"),
        ("h3", "hash_hex_3"),
        ("h4", "hash_hex_4"),
        ("h5", "hash_hex_5"),
        ("m0", "hash_mul_0"),
        ("m2", "hash_mul_2"),
        ("m4", "hash_mul_4"),
    ):
        vectors[vector_name] = kb.alloc(vector_name, VLEN)
        kb.add("valu", ("vbroadcast", vectors[vector_name], c[scalar_name]))
    return c, vectors


def _vector_hash(kb: MiniKernelBuilder, val, tmp1, tmp2, v, c):
    kb.add("valu", ("multiply_add", val, val, v["hash_mul_0"], v["hash_hex_0"]))

    kb.add("alu", [((">>", tmp1 + i, val + i, c["shift_19"])) for i in range(4)])
    kb.add("alu", [((">>", tmp1 + i, val + i, c["shift_19"])) for i in range(4, 8)])
    kb.add("valu", ("^", tmp2, val, v["hash_hex_1"]))
    kb.add("valu", ("^", val, tmp1, tmp2))

    kb.add("valu", ("multiply_add", val, val, v["hash_mul_2"], v["hash_hex_2"]))

    kb.add("valu", ("+", tmp1, val, v["hash_hex_3"]))
    kb.add("alu", [(("<<", tmp2 + i, val + i, c["shift_9"])) for i in range(4)])
    kb.add("alu", [(("<<", tmp2 + i, val + i, c["shift_9"])) for i in range(4, 8)])
    kb.add("valu", ("^", val, tmp1, tmp2))

    kb.add("valu", ("multiply_add", val, val, v["hash_mul_4"], v["hash_hex_4"]))

    kb.add("alu", [((">>", tmp1 + i, val + i, c["shift_16"])) for i in range(4)])
    kb.add("alu", [((">>", tmp1 + i, val + i, c["shift_16"])) for i in range(4, 8)])
    kb.add("valu", ("^", tmp2, val, v["hash_hex_5"]))
    kb.add("valu", ("^", val, tmp1, tmp2))


def _load_cached_nodes(kb: MiniKernelBuilder, workload: Workload, count: int):
    nodes = []
    for i in range(count):
        addr = kb.const(workload.forest_values_p + i, f"node_addr_{i}")
        scalar = kb.alloc(f"node_scalar_{i}")
        vec = kb.alloc(f"node_vec_{i}", VLEN)
        kb.add("load", ("load", scalar, addr))
        kb.add("valu", ("vbroadcast", vec, scalar))
        nodes.append(vec)
    return nodes


def _cached_node_select(kb: MiniKernelBuilder, idx, node_val, tmp1, tmp2, nodes, v, c, depth):
    if depth == 0:
        return nodes[0]
    if depth == 1:
        kb.add("valu", ("-", tmp1, idx, v["v_ones"]))
        kb.add("flow", ("vselect", node_val, tmp1, nodes[2], nodes[1]))
        return node_val
    if depth == 2:
        kb.add("valu", ("+", tmp1, idx, v["v_ones"]))
        kb.add("valu", ("&", tmp2, tmp1, v["v_ones"]))
        kb.add("valu", ("&", tmp1, tmp1, v["v_twos"]))
        kb.add("flow", ("vselect", node_val, tmp2, nodes[4], nodes[3]))
        kb.add("flow", ("vselect", tmp2, tmp2, nodes[6], nodes[5]))
        kb.add("flow", ("vselect", node_val, tmp1, tmp2, node_val))
        return node_val

    kb.add("valu", ("+", node_val, nodes[7], v["v_zero"]))
    for node_idx in range(8, 15):
        node_const = c.get(f"c{node_idx}")
        if node_const is None:
            node_const = kb.const(node_idx, f"c{node_idx}")
            c[f"c{node_idx}"] = node_const
        kb.add("alu", [("==", tmp1 + i, idx + i, node_const) for i in range(VLEN)])
        kb.add("flow", ("vselect", node_val, tmp1, nodes[node_idx], node_val))
    return node_val


def build_vector_ladder_kernel(
    forest_height: int,
    n_nodes: int,
    batch_size: int,
    rounds: int,
    *,
    cache_tree: bool,
    cache_depth3: bool = False,
    streaming_io: bool,
):
    """Single-bank vector checkpoint used before the tuned final builder."""

    workload = Workload(forest_height, n_nodes, batch_size, rounds)
    kb = MiniKernelBuilder()
    c, v = _vector_consts(kb, workload)

    tmp_v_idx = kb.alloc("tmp_v_idx", VLEN)
    tmp_v_val = kb.alloc("tmp_v_val", VLEN)
    tmp_v_node_val = kb.alloc("tmp_v_node_val", VLEN)
    tmp_v_addr = kb.alloc("tmp_v_addr", VLEN)
    v_tmp1 = kb.alloc("v_tmp1", VLEN)
    v_tmp2 = kb.alloc("v_tmp2", VLEN)
    io_val_p = c["values_p"] if streaming_io else None
    cached_node_count = 15 if cache_tree and cache_depth3 else 7
    cached_nodes = _load_cached_nodes(kb, workload, cached_node_count) if cache_tree else []

    num_batches = batch_size // VLEN
    for batch in range(num_batches):
        if streaming_io:
            val_addr = io_val_p
        else:
            val_addr = kb.const(workload.inp_values_p + batch * VLEN, f"value_vec_addr_{batch}")

        kb.add("load", ("vload", tmp_v_val, val_addr))
        kb.add("valu", ("vbroadcast", tmp_v_idx, c["zero"]))

        for r in range(rounds):
            depth = r % (forest_height + 1)
            if cache_tree and (depth <= 2 or (cache_depth3 and depth == 3)):
                node_src = _cached_node_select(
                    kb, tmp_v_idx, tmp_v_node_val, v_tmp1, v_tmp2, cached_nodes, v, c, depth
                )
            else:
                kb.add("valu", ("+", tmp_v_addr, tmp_v_idx, v["v_forest_p"]))
                for lane in range(0, VLEN, 2):
                    kb.add(
                        "load",
                        [
                            ("load_offset", tmp_v_node_val, tmp_v_addr, lane),
                            ("load_offset", tmp_v_node_val, tmp_v_addr, lane + 1),
                        ],
                    )
                node_src = tmp_v_node_val

            kb.add("valu", ("^", tmp_v_val, tmp_v_val, node_src))
            _vector_hash(kb, tmp_v_val, v_tmp1, v_tmp2, v, c)

            if r == rounds - 1:
                continue
            if depth == forest_height:
                kb.add("valu", ("-", tmp_v_idx, tmp_v_idx, tmp_v_idx))
            else:
                kb.add("valu", ("&", v_tmp1, tmp_v_val, v["v_ones"]))
                kb.add("valu", ("multiply_add", tmp_v_idx, tmp_v_idx, v["v_twos"], v["v_ones"]))
                kb.add("valu", ("+", tmp_v_idx, tmp_v_idx, v_tmp1))

        if streaming_io and batch != num_batches - 1:
            kb.instrs.append(
                {
                    "store": [("vstore", val_addr, tmp_v_val)],
                    "flow": [("add_imm", io_val_p, io_val_p, VLEN)],
                }
            )
        else:
            kb.add("store", ("vstore", val_addr, tmp_v_val))

    return kb


def build_scheduled_vector_ladder_kernel(
    forest_height: int,
    n_nodes: int,
    batch_size: int,
    rounds: int,
    *,
    cache_tree: bool,
    cache_depth3: bool = False,
    streaming_io: bool,
    schedule_mode: str,
    load_weight: int = -1,
    valu_weight: int = -1,
):
    """Vector checkpoint with dependency-aware scheduling but one temp namespace."""

    kb = build_vector_ladder_kernel(
        forest_height,
        n_nodes,
        batch_size,
        rounds,
        cache_tree=cache_tree,
        cache_depth3=cache_depth3,
        streaming_io=streaming_io,
    )
    kb.schedule(schedule_mode, load_weight=load_weight, valu_weight=valu_weight)
    return kb


def build_banked_vector_kernel(
    forest_height: int,
    n_nodes: int,
    batch_size: int,
    rounds: int,
    *,
    cache_tree: bool,
    cache_depth3: bool = False,
    streaming_io: bool = True,
    parallel_banks: int = 28,
    unroll: int = 32,
    schedule_mode: str = "strict",
    load_weight: int = -1,
    valu_weight: int = -1,
):
    """Vector checkpoint with multiple temporary banks.

    This keeps the readable vector-ladder semantics but processes a group of
    vector batches together. ``parallel_banks`` controls how many independent
    temporary namespaces are available to the scheduler.
    """

    workload = Workload(forest_height, n_nodes, batch_size, rounds)
    kb = MiniKernelBuilder()
    c, v = _vector_consts(kb, workload)

    num_batches = batch_size // VLEN
    group_size = min(unroll, num_batches)

    tmp_v_idx = [kb.alloc(f"tmp_v_idx_{i}", VLEN) for i in range(group_size)]
    tmp_v_val = [kb.alloc(f"tmp_v_val_{i}", VLEN) for i in range(group_size)]

    bank_count = max(1, min(parallel_banks, group_size))
    banks = []
    for i in range(bank_count):
        banks.append(
            {
                "tmp_v_node_val": kb.alloc(f"tmp_v_node_val_b{i}", VLEN),
                "tmp_v_addr": kb.alloc(f"tmp_v_addr_b{i}", VLEN),
                "v_tmp1": kb.alloc(f"v_tmp1_b{i}", VLEN),
                "v_tmp2": kb.alloc(f"v_tmp2_b{i}", VLEN),
            }
        )

    io_val_p = kb.alloc("io_val_p") if streaming_io else None
    cached_node_count = 15 if cache_tree and cache_depth3 else 7
    cached_nodes = _load_cached_nodes(kb, workload, cached_node_count) if cache_tree else []

    def load_values(active: int, batch_group: int):
        if streaming_io:
            kb.add("flow", ("add_imm", io_val_p, c["values_p"], batch_group * VLEN))
            for b in range(active):
                kb.add("load", ("vload", tmp_v_val[b], io_val_p))
                if b != active - 1:
                    kb.add("flow", ("add_imm", io_val_p, io_val_p, VLEN))
        else:
            for b in range(active):
                batch = batch_group + b
                val_addr = kb.const(workload.inp_values_p + batch * VLEN, f"value_vec_addr_{batch}")
                kb.add("load", ("vload", tmp_v_val[b], val_addr))

        for b in range(active):
            kb.add("valu", ("vbroadcast", tmp_v_idx[b], c["zero"]))

    def store_values(active: int, batch_group: int):
        if streaming_io:
            kb.add("flow", ("add_imm", io_val_p, c["values_p"], batch_group * VLEN))
            for b in range(active):
                kb.add("store", ("vstore", io_val_p, tmp_v_val[b]))
                if b != active - 1:
                    kb.add("flow", ("add_imm", io_val_p, io_val_p, VLEN))
        else:
            for b in range(active):
                batch = batch_group + b
                val_addr = kb.const(workload.inp_values_p + batch * VLEN, f"value_vec_addr_{batch}")
                kb.add("store", ("vstore", val_addr, tmp_v_val[b]))

    for batch_group in range(0, num_batches, group_size):
        active = min(group_size, num_batches - batch_group)
        load_values(active, batch_group)

        for r in range(rounds):
            depth = r % (forest_height + 1)

            for bs in range(0, active, bank_count):
                be = min(active, bs + bank_count)

                for bb in range(bs, be):
                    bank = banks[bb - bs]
                    if cache_tree and (depth <= 2 or (cache_depth3 and depth == 3)):
                        node_src = _cached_node_select(
                            kb,
                            tmp_v_idx[bb],
                            bank["tmp_v_node_val"],
                            bank["v_tmp1"],
                            bank["v_tmp2"],
                            cached_nodes,
                            v,
                            c,
                            depth,
                        )
                    else:
                        kb.add("valu", ("+", bank["tmp_v_addr"], tmp_v_idx[bb], v["v_forest_p"]))
                        for lane in range(0, VLEN, 2):
                            kb.add(
                                "load",
                                [
                                    ("load_offset", bank["tmp_v_node_val"], bank["tmp_v_addr"], lane),
                                    ("load_offset", bank["tmp_v_node_val"], bank["tmp_v_addr"], lane + 1),
                                ],
                            )
                        node_src = bank["tmp_v_node_val"]

                    kb.add("valu", ("^", tmp_v_val[bb], tmp_v_val[bb], node_src))

                for bb in range(bs, be):
                    bank = banks[bb - bs]
                    _vector_hash(kb, tmp_v_val[bb], bank["v_tmp1"], bank["v_tmp2"], v, c)

                    if r == rounds - 1:
                        continue
                    if depth == forest_height:
                        kb.add("valu", ("-", tmp_v_idx[bb], tmp_v_idx[bb], tmp_v_idx[bb]))
                    else:
                        kb.add("valu", ("&", bank["v_tmp1"], tmp_v_val[bb], v["v_ones"]))
                        kb.add(
                            "valu",
                            ("multiply_add", tmp_v_idx[bb], tmp_v_idx[bb], v["v_twos"], v["v_ones"]),
                        )
                        kb.add("valu", ("+", tmp_v_idx[bb], tmp_v_idx[bb], bank["v_tmp1"]))

        store_values(active, batch_group)

    kb.schedule(schedule_mode, load_weight=load_weight, valu_weight=valu_weight)
    return kb


def build_optimized_kernel(
    forest_height: int,
    n_nodes: int,
    batch_size: int,
    rounds: int,
    **kwargs,
):
    kb = KernelBuilder()
    kb.build_kernel(forest_height, n_nodes, batch_size, rounds, **kwargs)
    return kb
