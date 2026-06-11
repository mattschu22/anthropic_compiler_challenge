"""Dependency analysis and VLIW list scheduling for generated kernels."""

from collections import defaultdict
import heapq
import random

from .problem_api import SLOT_LIMITS, VLEN

# ---------------------------
# Dependency model for scheduling
# ---------------------------

def get_read_write_sets(engine, op):
    reads, writes = set(), set()

    if engine == "alu":
        dest = op[1]
        writes.add(dest)
        for src in op[2:]:
            if isinstance(src, int):
                reads.add(src)

    elif engine == "valu":
        op_name = op[0]
        if op_name == "vbroadcast":
            _, dest, src = op
            writes.update(range(dest, dest + VLEN))
            reads.add(src)
        elif op_name == "multiply_add":
            _, dest, a, b, c = op
            writes.update(range(dest, dest + VLEN))
            reads.update(range(a, a + VLEN))
            reads.update(range(b, b + VLEN))
            reads.update(range(c, c + VLEN))
        else:
            _, dest, a, b = op
            writes.update(range(dest, dest + VLEN))
            reads.update(range(a, a + VLEN))
            reads.update(range(b, b + VLEN))

    elif engine == "load":
        op_name = op[0]
        if op_name == "load":
            _, dest, addr = op
            writes.add(dest)
            reads.add(addr)
        elif op_name == "vload":
            _, dest, addr = op
            writes.update(range(dest, dest + VLEN))
            reads.add(addr)
        elif op_name == "load_offset":
            _, dest, addr, offset = op
            writes.add(dest + offset)
            reads.add(addr + offset)
        elif op_name == "const":
            _, dest, _ = op
            writes.add(dest)

    elif engine == "store":
        op_name = op[0]
        if op_name == "store":
            _, addr, src = op
            reads.update([addr, src])
        elif op_name == "vstore":
            _, addr, src = op
            reads.add(addr)
            reads.update(range(src, src + VLEN))

    elif engine == "flow":
        op_name = op[0]
        if op_name == "vselect":
            _, dest, cond, a, b = op
            writes.update(range(dest, dest + VLEN))
            reads.update(range(cond, cond + VLEN))
            reads.update(range(a, a + VLEN))
            reads.update(range(b, b + VLEN))
        elif op_name == "select":
            _, dest, cond, a, b = op
            writes.add(dest)
            reads.update([cond, a, b])
        elif op_name == "add_imm":
            _, dest, a, _imm = op
            writes.add(dest)
            reads.add(a)
        elif op_name == "pause":
            # no scratch deps
            pass

    return reads, writes


def build_dependency_graph(body):
    """
    Build deps using RAW / WAW / WAR on scratch words.

    Each entry in `body` is an (engine, ops) pair where ops is either a single slot tuple or a
    list of slots for that engine for that *single-cycle* instruction bundle.
    """
    instr_info = []
    for engine, ops in body:
        if isinstance(ops, tuple):
            ops = [ops]
        reads, writes = set(), set()
        for op in ops:
            r, w = get_read_write_sets(engine, op)
            reads |= r
            writes |= w
        instr_info.append((engine, ops, reads, writes))

    last_writer = {}
    last_reader = defaultdict(set)

    deps = defaultdict(set)   # i depends on deps[i]
    rev = defaultdict(set)    # i -> successors

    for i, (_eng, _ops, reads, writes) in enumerate(instr_info):
        # RAW
        for a in reads:
            if a in last_writer:
                deps[i].add(last_writer[a])
                rev[last_writer[a]].add(i)
        # WAW
        for a in writes:
            if a in last_writer:
                deps[i].add(last_writer[a])
                rev[last_writer[a]].add(i)
        # WAR
        for a in writes:
            for r in last_reader[a]:
                if r != i:
                    deps[i].add(r)
                    rev[r].add(i)

        # update state
        for a in writes:
            last_writer[a] = i
            last_reader[a] = set()
        for a in reads:
            last_reader[a].add(i)

    return deps, rev


def compute_critical_path(deps, rev, n):
    """
    Unweighted longest-path-to-sink height (topological DP from sinks).
    """
    height = [0] * n
    outdeg = [len(rev[i]) for i in range(n)]
    q = [i for i in range(n) if outdeg[i] == 0]
    qi = 0
    while qi < len(q):
        i = q[qi]
        qi += 1
        for p in deps[i]:
            height[p] = max(height[p], height[i] + 1)
            outdeg[p] -= 1
            if outdeg[p] == 0:
                q.append(p)
    return height


def pipeline_strict(body, load_weight=60, valu_weight=2):
    """
    Greedy list scheduler:
    - preserves dependencies and 1-cycle latency (writes visible next cycle)
    - packs independent engine bundles into the same cycle subject to slot limits

    Heuristic:
    We use two heights:
      - pr: regular critical path (instruction count)
      - prw: weighted critical path that increases priority of LOAD instructions
    and sort ready set by (-prw, -pr).
    """
    if not body:
        return []

    # normalize ops -> list
    norm = []
    for engine, ops in body:
        if isinstance(ops, tuple):
            ops = [ops]
        norm.append((engine, ops))
    body = norm

    deps, rev = build_dependency_graph(body)
    n = len(body)

    pr = compute_critical_path(deps, rev, n)

    # Weighted critical-path heuristic (favor making load ops ready)
    # This tends to create better "skew" across banks/rounds so loads overlap more with compute.
    weights = [1] * n
    for i, (eng, _ops) in enumerate(body):
        if eng == "load":
            weights[i] = load_weight
        elif eng == "valu":
            weights[i] = valu_weight
        else:
            weights[i] = 1

    prw = [0] * n
    outdeg = [len(rev[i]) for i in range(n)]
    q = [i for i in range(n) if outdeg[i] == 0]
    qi = 0
    while qi < len(q):
        i = q[qi]
        qi += 1
        for p in deps[i]:
            prw[p] = max(prw[p], prw[i] + weights[p])
            outdeg[p] -= 1
            if outdeg[p] == 0:
                q.append(p)

    scheduled = [False] * n
    finish = [-1] * n

    ready = set(i for i in range(n) if not deps[i])

    cycles = []
    cur = 0

    while sum(scheduled) < n:
        bundle = defaultdict(list)
        used = defaultdict(int)
        chosen = []

        # Fill this cycle greedily.
        for i in sorted(ready, key=lambda x: (-prw[x], -pr[x], x)):
            eng, ops = body[i]
            k = len(ops)
            if used[eng] + k > SLOT_LIMITS.get(eng, 64):
                continue
            if all(finish[d] < cur for d in deps[i]):
                bundle[eng].extend(ops)
                used[eng] += k
                chosen.append(i)

        if not chosen:
            # In these DAGs this should be rare; emit an empty cycle to preserve latency.
            cycles.append({})
            cur += 1
            continue

        for i in chosen:
            scheduled[i] = True
            ready.remove(i)
            finish[i] = cur
            for s in rev[i]:
                if not scheduled[s] and all(scheduled[d] for d in deps[s]):
                    ready.add(s)

        if bundle:
            cycles.append(dict(bundle))
        cur += 1

    # remove any empty bundles we may have appended
    cycles = [c for c in cycles if c]
    return cycles


# ---------------------------
# Relaxed dependency model + scheduler (WAR is 0-latency)
# ---------------------------

def build_dependency_graph_typed(body):
    """
    Build deps using RAW / WAW / WAR on scratch words, but *type* the edges:

      - deps1: constraints that require at least 1 cycle of separation (RAW, WAW)
      - deps0: constraints that allow same-cycle scheduling (WAR)

    This matches the machine semantics:
      - all reads observe the beginning-of-cycle scratch state
      - all writes commit at end-of-cycle

    Therefore:
      - RAW/WAW must be >= +1 cycle
      - WAR only needs writer to be scheduled in the same-or-later cycle than the reader (0-latency)
    """
    instr_info = []
    for engine, ops in body:
        if isinstance(ops, tuple):
            ops = [ops]
        reads, writes = set(), set()
        for op in ops:
            r, w = get_read_write_sets(engine, op)
            reads |= r
            writes |= w
        instr_info.append((engine, ops, reads, writes))

    last_writer = {}
    last_reader = defaultdict(set)

    deps1 = defaultdict(set)  # RAW + WAW
    deps0 = defaultdict(set)  # WAR
    rev1 = defaultdict(set)
    rev0 = defaultdict(set)

    for i, (_eng, _ops, reads, writes) in enumerate(instr_info):
        # RAW (1-cycle)
        for a in reads:
            if a in last_writer:
                p = last_writer[a]
                deps1[i].add(p)
                rev1[p].add(i)

        # WAW (1-cycle)
        for a in writes:
            if a in last_writer:
                p = last_writer[a]
                deps1[i].add(p)
                rev1[p].add(i)

        # WAR (0-cycle)
        for a in writes:
            for r in last_reader[a]:
                if r != i:
                    deps0[i].add(r)
                    rev0[r].add(i)

        # update state
        for a in writes:
            last_writer[a] = i
            last_reader[a] = set()
        for a in reads:
            last_reader[a].add(i)

    return deps1, deps0, rev1, rev0, instr_info


def compute_critical_path_latency(deps1, deps0, rev1, rev0, n):
    """
    Longest path-to-sink where deps1 edges cost 1 cycle and deps0 edges cost 0 cycles.
    """
    height = [0] * n
    outdeg = [len(rev1[i]) + len(rev0[i]) for i in range(n)]
    q = [i for i in range(n) if outdeg[i] == 0]
    qi = 0
    while qi < len(q):
        i = q[qi]
        qi += 1
        for p in deps1[i]:
            height[p] = max(height[p], height[i] + 1)
            outdeg[p] -= 1
            if outdeg[p] == 0:
                q.append(p)
        for p in deps0[i]:
            height[p] = max(height[p], height[i])  # 0-latency edge
            outdeg[p] -= 1
            if outdeg[p] == 0:
                q.append(p)
    return height


def compute_weighted_priority(deps1, deps0, rev1, rev0, n, weights):
    """
    Weighted longest path-to-sink where:
      - deps1 edges cost 1 cycle, deps0 edges cost 0 cycles
      - node weight = weights[i]
    """
    prw = [0] * n
    outdeg = [len(rev1[i]) + len(rev0[i]) for i in range(n)]
    q = [i for i in range(n) if outdeg[i] == 0]
    qi = 0
    while qi < len(q):
        i = q[qi]
        qi += 1
        for p in deps1[i]:
            prw[p] = max(prw[p], prw[i] + 1 + weights[p])
            outdeg[p] -= 1
            if outdeg[p] == 0:
                q.append(p)
        for p in deps0[i]:
            prw[p] = max(prw[p], prw[i] + 0 + weights[p])
            outdeg[p] -= 1
            if outdeg[p] == 0:
                q.append(p)
    return prw


def pipeline_relaxed(
    body,
    load_weight=60,
    valu_weight=2,
    addr_bonus=4,
    tie_seeds=(),
    bank_map=None,
):
    """Relaxed (WAR=0, RAW=1) list scheduler with *virtual* VALU ops.

    For certain VALU binary ops (e.g. ^, +, -, &, |), we allow an alternate
    physical implementation as 8 per-lane ALU ops. The scheduler uses the ALU
    fallback only when the VALU engine is saturated for the current cycle.

    This gives extra flexibility to pack cycles when VALU is the bottleneck.
    """

    # Reasonable default: a small deterministic multi-start search. The problem
    # is constrained and compile time is not a scoring dimension.
    if not tie_seeds:
        tie_seeds = tuple(range(96))

    # Normalize: ops is always a list.
    body_n = []
    for eng, ops in body:
        if isinstance(ops, tuple):
            ops = [ops]
        body_n.append((eng, ops))
    body = body_n

    deps1, deps0, rev1, rev0, instr_info = build_dependency_graph_typed(body)
    n = len(body)

    # Combined graph for critical-path computations.
    deps = defaultdict(set)
    rev = defaultdict(set)
    for i in range(n):
        for p in deps1.get(i, ()):  # RAW (1-cycle)
            deps[i].add(p)
            rev[p].add(i)
        for p in deps0.get(i, ()):  # WAR/WAW (0-cycle)
            deps[i].add(p)
            rev[p].add(i)

    pr = compute_critical_path(deps, rev, n)

    # Priority weights.
    weights = [1] * n
    for i, (eng, _ops, _r, _w) in enumerate(instr_info):
        if eng == "load":
            weights[i] = load_weight
        elif eng == "valu":
            weights[i] = valu_weight

    # Bonus to prioritize address-gen that unlocks loads.
    if addr_bonus:
        for i in range(n):
            if instr_info[i][0] == "load":
                continue
            if any(instr_info[s][0] == "load" for s in rev1.get(i, ())) or any(
                instr_info[s][0] == "load" for s in rev0.get(i, ())
            ):
                weights[i] += addr_bonus

    # Compute weighted "remaining work" (reverse topological DP).
    prw = [0] * n
    outdeg = [len(rev.get(i, ())) for i in range(n)]
    q = [i for i in range(n) if outdeg[i] == 0]
    qi = 0
    while qi < len(q):
        i = q[qi]
        qi += 1
        for p in deps.get(i, ()):
            v = prw[i] + weights[p]
            if v > prw[p]:
                prw[p] = v
            outdeg[p] -= 1
            if outdeg[p] == 0:
                q.append(p)

    # Successors and initial indegrees.
    succs = [set() for _ in range(n)]
    indeg0 = [0] * n
    for i in range(n):
        preds = set(deps1.get(i, ())) | set(deps0.get(i, ()))
        indeg0[i] = len(preds)
        if i in rev1:
            succs[i].update(rev1[i])
        if i in rev0:
            succs[i].update(rev0[i])

    # Build a per-node ALU fallback for eligible single-slot VALU ops.
    eligible = [False] * n
    alu_alt_ops = [None] * n
    for i, (eng, ops, _r, _w) in enumerate(instr_info):
        if eng != "valu" or len(ops) != 1:
            continue
        op = ops[0]
        if op[0] not in ("^", "+", "-", "&", "|"):
            continue
        if len(op) != 4:
            continue
        # Expect vector bases (contiguous lanes).
        if not (isinstance(op[1], int) and isinstance(op[2], int) and isinstance(op[3], int)):
            continue
        op_name, dest, a, b = op
        eligible[i] = True
        alu_alt_ops[i] = [(op_name, dest + j, a + j, b + j) for j in range(VLEN)]

    def schedule_len(seed: int) -> int:
        rng = random.Random(seed)
        tie = [rng.getrandbits(64) for _ in range(n)]

        indeg = indeg0.copy()
        scheduled = [False] * n
        finish = [-1] * n

        heap = []
        for i in range(n):
            if indeg[i] == 0:
                heapq.heappush(heap, (-prw[i], -pr[i], tie[i], i))

        cur = 0
        remaining = n
        while remaining:
            used = {k: 0 for k in SLOT_LIMITS}
            skipped = []
            did = False

            while heap:
                neg_prw, neg_pr, t, i = heapq.heappop(heap)
                if scheduled[i]:
                    continue

                # deps1 (RAW) must be satisfied with 1-cycle latency.
                ok = True
                for p in deps1.get(i, ()):  # each p must finish < cur
                    fp = finish[p]
                    if fp == -1 or fp >= cur:
                        ok = False
                        break
                if not ok:
                    skipped.append((neg_prw, neg_pr, t, i))
                    continue

                eng, ops = body[i]

                # Choose physical implementation.
                chosen_eng = eng
                chosen_ops = ops
                if eligible[i]:
                    if used["valu"] + len(ops) <= SLOT_LIMITS["valu"]:
                        chosen_eng = "valu"
                        chosen_ops = ops
                    elif used["alu"] + len(alu_alt_ops[i]) <= SLOT_LIMITS["alu"]:
                        chosen_eng = "alu"
                        chosen_ops = alu_alt_ops[i]
                    else:
                        skipped.append((neg_prw, neg_pr, t, i))
                        continue
                else:
                    if used[eng] + len(ops) > SLOT_LIMITS.get(eng, 64):
                        skipped.append((neg_prw, neg_pr, t, i))
                        continue

                used[chosen_eng] += len(chosen_ops)
                scheduled[i] = True
                finish[i] = cur
                remaining -= 1
                did = True

                for s in succs[i]:
                    indeg[s] -= 1
                    if indeg[s] == 0:
                        heapq.heappush(heap, (-prw[s], -pr[s], tie[s], s))

            for item in skipped:
                heapq.heappush(heap, item)

            if not did:
                raise ValueError(f"No schedulable ops at cycle {cur}")
            cur += 1

        return cur

    def schedule_build(seed: int):
        rng = random.Random(seed)
        tie = [rng.getrandbits(64) for _ in range(n)]

        indeg = indeg0.copy()
        scheduled = [False] * n
        finish = [-1] * n

        heap = []
        for i in range(n):
            if indeg[i] == 0:
                heapq.heappush(heap, (-prw[i], -pr[i], tie[i], i))

        cur = 0
        remaining = n
        schedule = []
        while remaining:
            used = {k: 0 for k in SLOT_LIMITS}
            bundle = defaultdict(list)
            skipped = []
            did = False

            while heap:
                neg_prw, neg_pr, t, i = heapq.heappop(heap)
                if scheduled[i]:
                    continue

                ok = True
                for p in deps1.get(i, ()):  # each p must finish < cur
                    fp = finish[p]
                    if fp == -1 or fp >= cur:
                        ok = False
                        break
                if not ok:
                    skipped.append((neg_prw, neg_pr, t, i))
                    continue

                eng, ops = body[i]

                chosen_eng = eng
                chosen_ops = ops
                if eligible[i]:
                    if used["valu"] + len(ops) <= SLOT_LIMITS["valu"]:
                        chosen_eng = "valu"
                        chosen_ops = ops
                    elif used["alu"] + len(alu_alt_ops[i]) <= SLOT_LIMITS["alu"]:
                        chosen_eng = "alu"
                        chosen_ops = alu_alt_ops[i]
                    else:
                        skipped.append((neg_prw, neg_pr, t, i))
                        continue
                else:
                    if used[eng] + len(ops) > SLOT_LIMITS.get(eng, 64):
                        skipped.append((neg_prw, neg_pr, t, i))
                        continue

                used[chosen_eng] += len(chosen_ops)
                bundle[chosen_eng].extend(chosen_ops)
                scheduled[i] = True
                finish[i] = cur
                remaining -= 1
                did = True

                for s in succs[i]:
                    indeg[s] -= 1
                    if indeg[s] == 0:
                        heapq.heappush(heap, (-prw[s], -pr[s], tie[s], s))

            for item in skipped:
                heapq.heappush(heap, item)

            if not did:
                raise ValueError(f"No schedulable ops at cycle {cur}")

            schedule.append(dict(bundle))
            cur += 1

        return schedule

    # Multi-start search: evaluate schedule length only, then build the best.
    best_len = 10**18
    best_seed = None
    for s in tie_seeds:
        l = schedule_len(int(s))
        if l < best_len:
            best_len = l
            best_seed = int(s)

    return schedule_build(best_seed)
# ---------------------------
# Kernel builder
# ---------------------------

def chunk_wide_valu_bundles(body, chunk_size=2):
    """
    Break only *wide* VALU bundles into smaller sub-bundles.

    We intentionally leave ALU/LOAD/STORE multi-slot bundles intact (they usually represent
    tight 2-slot patterns). The main packing problem comes from occasional 5-6 slot VALU
    bundles (mostly vbroadcasts), which can block better interleaving with other VALU work.

    Args:
        body: list[(engine, ops)] where ops is either a tuple (single slot) or list of slots.
        chunk_size: maximum number of VALU slots per produced bundle.

    Returns:
        A new body list with wide VALU bundles split into bundles of size <= chunk_size.
    """
    if not body:
        return body

    out = []
    for engine, ops in body:
        if engine == "valu" and isinstance(ops, list) and len(ops) > 2:
            for i in range(0, len(ops), chunk_size):
                out.append((engine, ops[i : i + chunk_size]))
        else:
            out.append((engine, ops))
    return out
