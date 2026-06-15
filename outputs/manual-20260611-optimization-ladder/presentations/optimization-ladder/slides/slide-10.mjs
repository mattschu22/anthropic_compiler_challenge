import { addTitle, addFooter, bulletList, colors, image, metric } from "./common.mjs";

export async function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Bottleneck Analysis: Memory Pressure Moves To Hot Tree Nodes", "After SIMD, the remaining gains come from reducing repeated memory work and regularizing I/O.", "memory");

  await image(slide, ctx, "charts/tree_cache_heatmap.png", 42, 145, 380, 420, "Tree cache heatmap");
  await image(slide, ctx, "trace_visuals/05_tree_cache.png", 450, 145, 360, 210, "Tree caching trace");
  await image(slide, ctx, "trace_visuals/06_streaming_io.png", 450, 382, 360, 210, "Streaming IO trace");

  metric(slide, ctx, "12,285 -> 11,856", "cache hot upper tree levels", 850, 152, 290, 90, colors.amber);
  metric(slide, ctx, "11,856 -> 11,825", "stream value address updates", 850, 264, 290, 90, colors.amber);

  bulletList(slide, ctx, [
    "Upper tree nodes are reused by many inputs. The root is touched by every input; reuse halves each depth.",
    "Caching shallow nodes replaces repeated gathers with scratch/vector selects.",
    "Streaming value I/O makes address generation a compact moving-pointer pattern.",
    "Narrative role: Perfetto shifts the question from 'can I vectorize?' to 'what resource is binding now?'"
  ], 850, 392, 320, { size: 13.5, gap: 48, bulletColor: colors.amber });

  addFooter(slide, ctx, 10);
  return slide;
}
