import { addTitle, addFooter, box, bulletList, colors, label, pill } from "./common.mjs";

export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Problem Description: Batched Binary Tree Traversal", "Each input repeatedly walks a perfect binary tree and updates its value through a hash pipeline.", "problem");

  box(slide, ctx, { x: 52, y: 150, w: 360, h: 420 });
  label(slide, ctx, "Fixed workload", 76, 174, 220, 26, { size: 21, bold: true });
  bulletList(slide, ctx, [
    "forest_height = 10: a perfect binary tree with 2,047 nodes.",
    "batch_size = 256: 256 independent inputs are processed together.",
    "rounds = 16: each input takes 16 tree steps.",
    "Depth sequence is deterministic: 0,1,2,3,4,5,6,7,8,9,10,0,1,2,3,4.",
  ], 78, 222, 286, { size: 14, gap: 56, bulletColor: colors.green });

  box(slide, ctx, { x: 462, y: 150, w: 690, h: 420 });
  label(slide, ctx, "One round of reference behavior", 486, 174, 320, 28, { size: 21, bold: true });
  const steps = [
    ["1", "Read current node index"],
    ["2", "Read tree node value"],
    ["3", "Hash input_value ^ node_value"],
    ["4", "Use hash parity to choose left/right child"],
    ["5", "Update value and current index"],
  ];
  steps.forEach((s, i) => {
    const x = 500 + i * 122;
    const y = 252 + (i % 2) * 84;
    ctx.addShape(slide, { x, y, w: 86, h: 64, fill: i % 2 ? "#ecfeff" : "#eff6ff", line: { fill: colors.faint, width: 1 } });
    label(slide, ctx, s[0], x + 8, y + 8, 20, 20, { size: 16, bold: true, color: colors.blue });
    label(slide, ctx, s[1], x + 8, y + 30, 70, 28, { size: 9.5, color: colors.ink });
    if (i < steps.length - 1) label(slide, ctx, "->", x + 91, y + 22, 30, 20, { size: 18, bold: true, color: colors.muted });
  });
  pill(slide, ctx, "Correctness target: final values match reference", 518, 452, 330, colors.green);
  pill(slide, ctx, "Optimization target: fewer simulator cycles", 870, 452, 260, colors.blue);

  addFooter(slide, ctx, 3);
  return slide;
}
