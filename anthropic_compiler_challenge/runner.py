"""Local benchmark and tuning helpers for the optimized kernel."""

from .kernel_builder import KernelBuilder
from .problem_api import Machine, N_CORES, Tree, Input, build_mem_image, reference_kernel2

def do_kernel_test(
    forest_height: int,
    rounds: int,
    batch_size: int,
    *,
    unroll: int = 32,
    parallel_banks: int = 28,
    load_weight: int = -1,
    valu_weight: int = -1,
    addr_bonus: int = 2,
    inplace_gather: bool = True,
    use_tmp3: bool = False,
    streaming_io: bool = True,
    cache_depth3: bool = True,
    depth3_banks: int = 13,
    tmp3_banks: int | None = 18,
    depth3_use_alu_masks: bool = False,
    trace: bool = False,
    seed: int = 123,
    verbose: bool = False,
) -> int:
    """
    Convenience runner for local iteration.

    Returns total machine cycles (init + compute).
    """
    import random

    random.seed(seed)
    forest = Tree.generate(forest_height)
    inp = Input.generate(forest, batch_size, rounds)
    mem = build_mem_image(forest, inp)

    kb = KernelBuilder()
    kb.build_kernel(
        forest.height,
        len(forest.values),
        len(inp.indices),
        rounds,
        unroll=unroll,
        parallel_banks=parallel_banks,
        load_weight=load_weight,
        valu_weight=valu_weight,
        addr_bonus=addr_bonus,
        inplace_gather=inplace_gather,
        use_tmp3=use_tmp3,
        streaming_io=streaming_io,
        cache_depth3=cache_depth3,
        depth3_banks=depth3_banks,
        depth3_use_alu_masks=depth3_use_alu_masks,
        tmp3_banks=tmp3_banks,
    )

    value_trace: dict[Any, int] = {}
    machine = Machine(
        mem,
        kb.instrs,
        kb.debug_info(),
        n_cores=N_CORES,
        value_trace=value_trace,
        trace=trace,
    )

    for _i, ref_mem in enumerate(reference_kernel2(mem, value_trace)):
        machine.run()
        inp_values_p = ref_mem[6]
        assert (
            machine.mem[inp_values_p : inp_values_p + len(inp.values)]
            == ref_mem[inp_values_p : inp_values_p + len(inp.values)]
        )

    if verbose:
        print(
            f"cycles: {machine.cycle} "
            f"(unroll={unroll} banks={parallel_banks} "
            f"lw={load_weight} vw={valu_weight} ab={addr_bonus} "
            f"inplace={inplace_gather} tmp3={use_tmp3} streamIO={streaming_io} "
            f"cacheD3={cache_depth3} d3b={depth3_banks} aluD3={depth3_use_alu_masks})"
            )
    return machine.cycle


def hyperparameter_search(seed: int = 123, max_tests: int | None = None) -> None:
    """Scratch-safe hyperparameter search.

    This is a small grid/random search over the knobs that materially affect schedule packing.
    It is intentionally not exhaustive (the design space is huge and scheduling is expensive).

    Arguments:
      seed: RNG seed for deterministic Tree/Input generation.
      max_tests: if set, stop after this many tested configs (useful for quick iteration).
    """
    forest_height = 10
    rounds = 16
    batch_size = 256

    # Focus around the known-good region.
    parallel_banks_space = [24, 25, 26]
    depth3_banks_space = [12, 13, 14, 15]
    tmp3_banks_space = [None, 12, 13, 14, 15, 16, 17, 18, 19]
    load_weight_space = [-6, -5, -4, -3, -2, -1, 0]
    addr_bonus_space = [-2, -1, 0, 1]
    valu_weight_space = [0]

    best_cycles = 10**9
    best_cfg = None
    tested = 0

    for parallel_banks in parallel_banks_space:
        for depth3_banks in depth3_banks_space:
            for tmp3_banks in tmp3_banks_space:
                # If specified, enforce that any bank used for depth-3 selection has v_tmp3.
                if tmp3_banks is not None and tmp3_banks < depth3_banks:
                    continue
                if tmp3_banks is not None and tmp3_banks > parallel_banks:
                    continue

                for load_weight in load_weight_space:
                    for valu_weight in valu_weight_space:
                        for addr_bonus in addr_bonus_space:
                            if max_tests is not None and tested >= max_tests:
                                print("Tested", tested, "configs")
                                print("Best:", best_cycles, "cycles, cfg:", best_cfg)
                                return

                            try:
                                cycles = do_kernel_test(
                                    forest_height,
                                    rounds,
                                    batch_size,
                                    unroll=32,
                                    parallel_banks=parallel_banks,
                                    load_weight=load_weight,
                                    valu_weight=valu_weight,
                                    addr_bonus=addr_bonus,
                                    inplace_gather=True,
                                    use_tmp3=False,
                                    streaming_io=True,
                                    cache_depth3=True,
                                    depth3_banks=depth3_banks,
                                    tmp3_banks=tmp3_banks,
                                    depth3_use_alu_masks=False,
                                    trace=False,
                                    seed=seed,
                                    verbose=False,
                                )
                            except AssertionError:
                                continue

                            tested += 1
                            if cycles < best_cycles:
                                best_cycles = cycles
                                best_cfg = dict(
                                    unroll=32,
                                    parallel_banks=parallel_banks,
                                    load_weight=load_weight,
                                    valu_weight=valu_weight,
                                    addr_bonus=addr_bonus,
                                    inplace_gather=True,
                                    use_tmp3=False,
                                    streaming_io=True,
                                    cache_depth3=True,
                                    depth3_banks=depth3_banks,
                                    tmp3_banks=tmp3_banks,
                                    depth3_use_alu_masks=True,
                                )
                                print("NEW BEST:", best_cycles, "cycles", best_cfg)

    print("Tested", tested, "configs")
    print("Best:", best_cycles, "cycles, cfg:", best_cfg)
def test_kernel_cycles():
    # Optimized configuration for the grading case (matches the defaults).
    cycles = do_kernel_test(
        10,
        16,
        256,
        unroll=32,
        parallel_banks=28,
        load_weight=-1,
        valu_weight=-1,
        addr_bonus=2,
        inplace_gather=True,
        use_tmp3=False,
        streaming_io=True,
        cache_depth3=True,
        depth3_banks=13,
        tmp3_banks=18,
        depth3_use_alu_masks=False,
        trace=False,
        seed=123,
    )
    print("cycles:", cycles)
    assert cycles <= 1195, f"Too slow: {cycles} cycles"

if __name__ == "__main__":
    # Run the optimized configuration for the grading case
    print(do_kernel_test(10, 16, 256, trace=True))

    # Uncomment to run a small sweep:
    # hyperparameter_search()
