import { addTitle, addFooter, box, colors, label } from "./common.mjs";

export async function slide14(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Limitations", "The final kernel is fast because it is intentionally specialized; that creates real engineering tradeoffs.", "limitations");

  const items = [
    ["Highly specialized workload", "The generated kernel assumes forest_height=10, rounds=16, batch_size=256, and a stable memory layout. Generalizing it would require a broader code generator."],
    ["Generated code size increases", "Unrolling and specialization remove runtime overhead but produce a larger instruction stream. That is acceptable for this simulator, but real instruction cache behavior could matter."],
    ["Scheduler is heuristic", "The VLIW scheduler uses dependency analysis and priority rules, but it is not an optimal solver and does not prove the best possible packing."],
    ["Scratch allocation is manually tuned", "Temporary banks expose parallelism, but the current allocator is not a full liveness-aware register coloring pass."],
    ["Profiler interpretation is still manual", "Perfetto traces guided the optimization path, but bottleneck classification and goodput metrics are not yet fully automated."]
  ];
  items.forEach((it, i) => {
    const x = i % 2 === 0 ? 60 : 650;
    const y = 150 + Math.floor(i / 2) * 158;
    const w = i === 4 ? 1090 : 520;
    box(slide, ctx, { x, y, w, h: 122 });
    label(slide, ctx, it[0], x + 18, y + 16, w - 36, 24, { size: 18, bold: true, color: i % 2 === 0 ? colors.blue : colors.rose });
    label(slide, ctx, it[1], x + 18, y + 50, w - 42, 54, { size: 13.2, color: colors.ink });
  });

  addFooter(slide, ctx, 14);
  return slide;
}
