// Merge per-character clip metadata (written by tools/blender/build_animations.py) into the index the animation lab
// and tests read. Never overwrites: fails if the output exists.
// Usage: node tools/validation/build-clip-index.mjs <aldren_clips_vX.json> <william_clips_vY.json> <out clips_index_vNNN.json>
import {readFileSync, writeFileSync, existsSync} from 'node:fs';
const [aPath, wPath, out] = process.argv.slice(2);
if (!aPath || !wPath || !out) { console.error('usage: build-clip-index <aldren.json> <william.json> <out.json>'); process.exit(2); }
if (existsSync(out)) { console.error('refusing to overwrite ' + out); process.exit(1); }
const A = JSON.parse(readFileSync(aPath, 'utf8')), W = JSON.parse(readFileSync(wPath, 'utf8'));
const index = {
  version: out.match(/_(v\d+)\.json$/)?.[1] ?? 'v001', fps: A.fps,
  sources: {aldren: aPath, william: wPath},
  engagement: A.engagement,
  characters: {
    aldren: {model: A.model, clips_glb: A.clips_glb, clips_glb_sha256: A.glb_sha256, view: 'third_person'},
    william: {model: W.model, clips_glb: W.clips_glb, clips_glb_sha256: W.glb_sha256, view: 'first_person'},
  },
  weapon: A.weapon,
  authoring: A.authoring,
  clips: {...A.clips, ...W.clips},
};
writeFileSync(out, JSON.stringify(index, null, 1), {flag: 'wx'});
console.log(`wrote ${out}: ${Object.keys(index.clips).length} clips`);
