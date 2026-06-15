# Removing Unnecessary Work Analysis

The revised `01_remove_unnecessary_work` checkpoint combines the old
test-contract and scratch-index steps into one presentation rung.

Two pieces of work leave the graded path:

- The final index state is not checked by the grader, so the final index
  writeback is unnecessary.
- Traversal indices are needed during execution, but they can live in scratch
  instead of being loaded from and stored to memory every round.

Measured with seed `123` after rebuilding the revised ladder:

| Case | Cycles | Static instructions | Static slots |
| --- | ---: | ---: | --- |
| Equivalent scalar baseline trace kernel | 135,257 | 62 | `load=27, alu=30, flow=3, store=2` |
| Removing unnecessary work checkpoint | 114,868 | 7,438 | scalar scratch kernel |

Compared with the equivalent scalar machine baseline, this saves `20,389`
cycles:

```text
135,257 - 114,868 = 20,389 cycles
```

The chart shows a larger drop from `147,734` to `114,868` because stage 0 uses
the supplied benchmark number, while the traceable scalar machine baseline is
`135,257` cycles.
