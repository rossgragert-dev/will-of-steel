// Motion-quality tests for the v0.4.0 fencing clips (clips_index_v003.json). Skips if clips are not generated.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';

const INDEX = 'assets/v0.4.0/animations/clips_index_v003.json';
const have = existsSync(INDEX);
const idx = have ? JSON.parse(readFileSync(INDEX, 'utf8')) : null;
const clips = have ? idx.clips : {};
const sub = (a, b) => a.map((v, i) => v - b[i]);
const len = v => Math.hypot(...v);
const dot = (a, b) => a.reduce((s, v, i) => s + v * b[i], 0);
const unit = v => { const n = len(v); return v.map(x => x / n); };
const skip = t => { if (!have) { t.skip('clips not generated yet'); return true; } return false; };
const attacks = () => Object.entries(clips).filter(([, c]) => c.kind === 'attack');

test('true edge leads the cut at contact (edge aligned with blade travel)', t => {
  if (skip(t)) return;
  for (const [name, c] of attacks()) {
    const s = c.samples, f = c.contact_frame;
    // travel of the percussion point (65 % along the blade) across the contact frame
    const p = k => s.blade_base[k].map((v, i) => v + (s.blade_tip[k][i] - v) * 0.65);
    const travel = unit(sub(p(f + 1), p(f - 1)));
    const blade = unit(sub(s.blade_tip[f], s.blade_base[f]));
    const perp = unit(sub(travel, blade.map(x => x * dot(travel, blade))));
    const align = dot(unit(s.edge_dir[f]), perp);
    assert.ok(align > 0.5, `${name}: true edge alignment ${align.toFixed(2)} at contact`);
  }
});

test('blade tip speed stays human (<= 24 m/s) with no single-frame spikes', t => {
  if (skip(t)) return;
  for (const [name, c] of Object.entries(clips)) {
    const s = c.samples, fps = c.fps;
    const step = s.frames.slice(1).map((_, i) => len(sub(s.blade_tip[i + 1], s.blade_tip[i])));
    const peak = Math.max(...step) * fps;
    assert.ok(peak <= 24, `${name}: peak tip speed ${peak.toFixed(1)} m/s`);
    for (let i = 1; i < step.length - 1; i++) {
      const nb = Math.max(step[i - 1], step[i + 1]);
      if (step[i] > 0.15) assert.ok(step[i] <= 1.6 * nb + 0.05, `${name}: spike at frame ${i + 1} (${(step[i] * 1000).toFixed(0)} mm vs ${(nb * 1000).toFixed(0)} mm)`);
    }
  }
});

test('transitions: attacks and parries start and end in the ready pose; deflect starts at the parry hold', t => {
  if (skip(t)) return;
  for (const who of ['aldren', 'william']) {
    const ready = clips[`${who}_idle_ready`].samples;
    const r0 = {base: ready.blade_base[0], tip: ready.blade_tip[0]};
    for (const kind of ['attack_head', 'attack_upper_left', 'attack_upper_right', 'parry_head']) {
      const s = clips[`${who}_${kind}`].samples, n = s.frames.length - 1;
      for (const [label, k] of [['start', 0], ['end', n]]) {
        const d = Math.max(len(sub(s.blade_base[k], r0.base)), len(sub(s.blade_tip[k], r0.tip)));
        assert.ok(d < 0.005, `${who}_${kind} ${label} differs from ready by ${(d * 1000).toFixed(1)} mm`);
      }
    }
    const parry = clips[`${who}_parry_head`], defl = clips[`${who}_deflect_head`].samples;
    const hold = parry.phases.hold[0] + 1;
    const d = len(sub(defl.blade_tip[0], parry.samples.blade_tip[hold]));
    assert.ok(d < 0.005, `${who} deflect start vs parry hold: ${(d * 1000).toFixed(1)} mm`);
    const dEnd = len(sub(defl.blade_tip.at(-1), parry.samples.blade_tip[hold]));
    assert.ok(dEnd < 0.005, `${who} deflect settles back to the parry hold: ${(dEnd * 1000).toFixed(1)} mm`);
  }
});

test('interruption: every attack frame keeps a valid two-handed grip (safe point to blend into deflect/recovery)', t => {
  if (skip(t)) return;
  for (const [name, c] of attacks()) {
    const s = c.samples;
    s.frames.forEach((f, i) => {
      assert.ok(s.grip_error_mm[i] <= 3, `${name} f${f}: grip ${s.grip_error_mm[i]} mm`);
      assert.ok(Math.max(s.elbow_deg_l[i], s.elbow_deg_r[i]) <= 150, `${name} f${f}: elbow over-fold`);
    });
  }
});

test('attack phases: windup precedes contact, contact precedes follow-through, recovery ends the clip', t => {
  if (skip(t)) return;
  for (const [name, c] of attacks()) {
    const p = c.phases;
    assert.ok(p.windup[1] <= c.contact_frame && c.contact_frame <= p.follow_through[0] + 0, `${name}: contact inside attack->follow boundary`);
    assert.equal(p.recovery[1], c.frame_end, `${name}: recovery ends at the last frame`);
    assert.ok(c.duration_s >= 1.0 && c.duration_s <= 2.0, `${name}: duration ${c.duration_s}s`);
  }
});

test('weapon attachment convention is declared and consistent', t => {
  if (skip(t)) return;
  assert.equal(idx.weapon.socket, 'weapon_r');
  assert.equal(idx.weapon.off_hand_socket, 'grip_l');
  assert.match(idx.weapon.convention, /\+Y blade/);
  assert.match(idx.weapon.convention, /\+Z true edge/);
  for (const [name, c] of Object.entries(clips)) {
    const s = c.samples;
    for (let i = 0; i < s.frames.length; i++) {
      const L = len(sub(s.blade_tip[i], s.blade_base[i]));
      assert.ok(Math.abs(L - 0.92) < 0.002, `${name} f${i}: blade length ${L.toFixed(3)} (sword must stay rigidly attached)`);
    }
  }
});

test('GLB keyframe timing matches the metadata (duration = frame_end / fps for every exported animation)', async t => {
  if (skip(t)) return;
  const {parseGLB} = await import('../tools/validation/inspect-glb.mjs');
  for (const [who, ch] of Object.entries(idx.characters)) {
    const {json} = parseGLB(readFileSync(ch.clips_glb));
    for (const [name, c] of Object.entries(clips).filter(([, c]) => c.character === who)) {
      const anim = json.animations.find(a => a.name === c.animation);
      assert.ok(anim, `${name}: animation missing from ${ch.clips_glb}`);
      const tmax = Math.max(...anim.samplers.map(s => json.accessors[s.input].max[0]));
      assert.ok(Math.abs(tmax - c.duration_s) <= 1 / c.fps + 1e-6, `${name}: GLB duration ${tmax.toFixed(3)} s vs metadata ${c.duration_s} s`);
    }
  }
});

test('reach corrections are smooth (no sword teleporting)', t => {
  if (skip(t)) return;
  for (const [name, c] of Object.entries(clips)) {
    const r = c.samples.reach_correction_mm;
    for (let i = 1; i < r.length; i++) assert.ok(Math.abs(r[i] - r[i - 1]) <= 40, `${name} f${i}: correction jump ${(r[i] - r[i - 1]).toFixed(1)} mm`);
  }
});
