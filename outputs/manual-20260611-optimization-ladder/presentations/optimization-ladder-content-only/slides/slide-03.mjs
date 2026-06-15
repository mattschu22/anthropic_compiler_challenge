import { addTitle, addSubtitle, addBullets, addPlaceholder } from "./common.mjs";

export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  addTitle(slide, ctx, "Problem Description: Batched Binary Tree Traversal");
  addSubtitle(slide, ctx, "Each input repeatedly walks a perfect binary tree and updates its value through a hash pipeline.");
  addBullets(slide, ctx, [
    "Workload constants: forest_height = 10, rounds = 16, batch_size = 256.",
    "A perfect binary tree of height 10 has 2,047 nodes.",
    "Each input maintains a current value and a current tree index.",
    "One round: read current index, read tree node value, compute myhash(input_value ^ node_value), choose left or right child from hash parity, then update value and index.",
    "The depth sequence is deterministic: 0,1,2,3,4,5,6,7,8,9,10,0,1,2,3,4.",
    "Correctness target: final values must match the reference implementation."
  ], 70, 150, 1060, 16, 34);
  addPlaceholder(slide, ctx, "PowerPoint diagram: clean concept diagram with depth-10 binary tree on left, one highlighted input path, and one-round dataflow on right: value + index -> node lookup -> hash -> branch bit -> next index/value.");
  return slide;
}
