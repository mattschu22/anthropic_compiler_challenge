# Test Contract Analysis

The `01_test_contract` checkpoint now skips both final-round index updates and
final index stores with a separate final value-only pass.

The speedup is still modest because the test contract only helps after the last
round has computed the final value. The kernel still needs index values through
round 15 to choose each round's tree node, so this checkpoint cannot remove
index loads or the intermediate index stores yet.

Measured with seed `123`:

| Case | Cycles | Static instructions | Static slots |
| --- | ---: | ---: | --- |
| Equivalent scalar baseline trace kernel | 135,257 | 62 | `load=27, alu=30, flow=3, store=2` |
| Tuned test-contract checkpoint | 133,463 | 90 | `load=30, alu=53, flow=4, store=3` |

Compared with the equivalent scalar machine baseline, this saves `1,794`
cycles:

```text
135,257 - 133,463 = 1,794 cycles
```

The chart shows a larger drop from `147,734` to `133,463` because stage 0 uses
the supplied benchmark number, while the traceable scalar machine baseline is
`135,257` cycles.

The larger index-memory win arrives at `02_scratch_indices`, where live index
state leaves memory for the whole run rather than only becoming irrelevant after
the final value has already been computed.
