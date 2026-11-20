// Validates the v0.4.0 animation clip contract (assets/v0.4.0/animations/clips_index_v003.json) when it exists.
// Until the clips are authored every test skips with 'clips not generated yet'. Read-only: never writes files.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {parseGLB} from '../tools/validation/inspect-glb.mjs';

const ROOT = resolve(fileURLToPath(new URL('..', import.meta.url)));
const INDEX = resolve(ROOT, 'assets/v0.4.0/animations/clips_index_v003.json');
const have = existsSync(INDEX);
const idx = have ? JSON.parse(readFileSync(INDEX, 'utf8')) : null;
const SKIP = 'clips not generated yet';
const T = (name, fn) => test(name, t => (have ? fn(t) : t.skip(SKIP)));

const EXPECTED = ['aldren_idle_ready', 'aldren_attack_head', 'aldren_attack_upper_left', 'aldren_attack_upper_right', 'aldren_parry_head',
  'aldren_deflect_head', 'william_idle_ready', 'william_attack_head', 'william_attack_upper_left', 'william_attack_upper_right',
  'william_parry_head', 'william_deflect_head'];
const PHASE_ORDER = {
  idle: ['prepare', 'windup', 'attack', 'follow_through', 'recovery'],
  attack: ['prepare', 'windup', 'attack', 'follow_through', 'recovery'],
  parry: ['raise', 'hold', 'recover'], deflect: ['impact', 'absorb', 'settle'],
};
const ARM_CHAIN = /^(clavicle|upperarm|upperarm_twist|forearm|forearm_twist|hand)_(l|r)$/;
const clips = () => Object.entries(idx.clips || {});
const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
const glbCache = new Map();
function glb(rel) {
  if (!glbCache.has(rel)) glbCache.set(rel, parseGLB(readFileSync(resolve(ROOT, rel))).json);
  return glbCache.get(rel);
}

T('all 12 expected clips are present and named by the pattern', () => {
  const names = Object.keys(idx.clips || {});
  for (const n of EXPECTED) assert.ok(names.includes(n), 'missing clip ' + n);
  for (const n of names) assert.match(n, /^(aldren|william)_(idle|attack|parry|deflect)_[a-z_]+$/);
  for (const [n, c] of clips()) {
    assert.equal(c.character, n.split('_')[0], n + ' character');
    assert.equal(c.kind, n.split('_')[1], n + ' kind');
    assert.equal(c.animation, n, n + ' animation name');
    assert.ok(idx.characters?.[c.character], n + ' unknown character');
  }
});

T('fps is 30, engagement distances are declared and durations match frame ranges', () => {
  assert.equal(idx.fps, 30);
  const e = idx.engagement;
  assert.ok(e && [e.guard_distance_m, e.contact_distance_m, e.attack_step_m].every(v => Number.isFinite(v) && v > 0), 'engagement block');
  for (const [n, c] of clips()) {
    assert.ok(Number.isInteger(c.frame_start) && Number.isInteger(c.frame_end) && c.frame_end > c.frame_start, n + ' frame range');
    const expect = (c.frame_end - c.frame_start) / idx.fps;
    assert.ok(Math.abs(c.duration_s - expect) <= .5 / idx.fps, `${n} duration ${c.duration_s} vs ${(c.frame_end - c.frame_start)}/${idx.fps}`);
  }
});

T('phases are ordered, non-overlapping and inside [frame_start, frame_end]', () => {
  for (const [n, c] of clips()) {
    const order = PHASE_ORDER[c.kind];
    assert.ok(order, n + ' unknown kind ' + c.kind);
    const keys = Object.keys(c.phases || {});
    for (const k of keys) assert.ok(order.includes(k), `${n}: phase '${k}' not allowed for ${c.kind}`);
    if (c.kind !== 'idle') assert.ok(keys.length > 0, n + ' has no phases');
    let last = c.frame_start;
    for (const k of order) {
      if (!c.phases?.[k]) continue;
      const [a, b] = c.phases[k];
      assert.ok(a <= b, `${n}.${k} reversed`);
      assert.ok(a >= c.frame_start && b <= c.frame_end, `${n}.${k} [${a},${b}] outside clip`);
      assert.ok(a >= last, `${n}.${k} starts at ${a} before previous phase end ${last}`);
      last = b;
    }
  }
});

T('attack contact frames lie in [0.45, 0.80] of the clip, match contact_normalized and sit on the attack/follow-through boundary', () => {
  for (const [n, c] of clips()) {
    if (c.kind === 'parry' || c.kind === 'deflect') {
      // Defensive clips carry expected_contact_frame (impact window start); contact_frame is null for them.
      assert.equal(c.contact_frame ?? null, null, n + ' contact_frame must be null');
      assert.ok(Number.isInteger(c.expected_contact_frame) && c.expected_contact_frame >= c.frame_start && c.expected_contact_frame <= c.frame_end,
        n + ' expected_contact_frame');
      continue;
    }
    if (c.kind !== 'attack') { assert.equal(c.contact_frame ?? null, null, n); continue; }
    assert.ok(Number.isInteger(c.contact_frame), n + ' contact_frame');
    const ratio = c.contact_frame / c.frame_end;
    assert.ok(ratio >= .45 && ratio <= .80, `${n} contact ${c.contact_frame}/${c.frame_end}=${ratio.toFixed(3)} outside [0.45, 0.80]`);
    assert.ok(Number.isFinite(c.contact_normalized) && Math.abs(c.contact_normalized - ratio) <= .01,
      `${n} contact_normalized ${c.contact_normalized} vs ${ratio.toFixed(3)}`);
    const atk = c.phases.attack, fol = c.phases.follow_through;
    assert.ok(atk && fol, n + ' needs attack and follow_through phases');
    assert.ok(c.contact_frame >= atk[0] && c.contact_frame <= fol[1], `${n} contact outside attack..follow_through`);
    const edge = Math.min(Math.abs(c.contact_frame - atk[1]), Math.abs(c.contact_frame - fol[0]));
    assert.ok(edge <= 2, `${n} contact ${c.contact_frame} is ${edge} frames from the attack/follow boundary`);
  }
});

T('samples are complete and aligned with frames', () => {
  for (const [n, c] of clips()) {
    const s = c.samples; assert.ok(s && Array.isArray(s.frames) && s.frames.length >= 2, n + ' samples.frames');
    const L = s.frames.length;
    for (let i = 1; i < L; i++) assert.ok(s.frames[i] > s.frames[i - 1], n + ' frames increasing');
    assert.ok(s.frames[0] >= c.frame_start && s.frames[L - 1] <= c.frame_end, n + ' sample frames inside clip');
    for (const k of ['blade_base', 'blade_mid', 'blade_tip', 'edge_dir', 'grip_error_mm', 'elbow_deg_l', 'elbow_deg_r']) {
      assert.ok(Array.isArray(s[k]) && s[k].length === L, `${n}.samples.${k} length`);
    }
    for (const k of ['blade_base', 'blade_mid', 'blade_tip', 'edge_dir']) for (const v of s[k]) assert.ok(v.length === 3 && v.every(Number.isFinite), `${n}.${k}`);
    for (const k of ['foot_l', 'foot_r']) if (s[k] != null) assert.equal(s[k].length, L, `${n}.${k} length`);
    if (c.camera_advance_m != null) assert.ok(Array.isArray(c.camera_advance_m) && c.camera_advance_m.length === L && c.camera_advance_m.every(Number.isFinite),
      n + ' camera_advance_m must be one finite value per sample frame');
  }
});

T('looping clips close: first and last blade samples within 5 mm', () => {
  for (const [n, c] of clips()) {
    if (!c.loop) continue;
    const s = c.samples, L = s.frames.length;
    for (const k of ['blade_base', 'blade_mid', 'blade_tip']) {
      const d = dist(s[k][0], s[k][L - 1]) * 1000;
      assert.ok(d <= 5, `${n}.${k} loop seam ${d.toFixed(2)} mm`);
    }
  }
});

T('two-handed grip error is at most 5 mm and elbows stay within [0, 150] degrees', () => {
  for (const [n, c] of clips()) {
    const s = c.samples;
    const g = Math.max(...s.grip_error_mm);
    assert.ok(g <= 5, `${n} grip error ${g} mm`);
    for (const k of ['elbow_deg_l', 'elbow_deg_r']) for (const a of s[k]) assert.ok(a >= 0 && a <= 150, `${n}.${k} ${a}`);
  }
});

T('root motion is declared in place and Ser Aldren feet do not slide while planted', () => {
  for (const [n, c] of clips()) {
    assert.equal(c.root_motion?.mode, 'in_place', n + ' root_motion.mode');
    if (c.character !== 'aldren') continue;
    const s = c.samples;
    assert.ok(s.foot_l && s.foot_r, n + ' aldren clips need foot samples');
    for (const k of ['foot_l', 'foot_r']) {
      // Planted episode: consecutive samples with foot height < 0.03 m. Horizontal drift within each <= 10 mm.
      let start = -1;
      const check = (a, b) => {
        let worst = 0;
        for (let i = a; i <= b; i++) for (let j = i + 1; j <= b; j++) {
          worst = Math.max(worst, Math.hypot(s[k][j][0] - s[k][i][0], s[k][j][2] - s[k][i][2]));
        }
        assert.ok(worst * 1000 <= 10, `${n}.${k} slides ${(worst * 1000).toFixed(1)} mm while planted (frames ${s.frames[a]}-${s.frames[b]})`);
      };
      for (let i = 0; i <= s[k].length; i++) {
        const planted = i < s[k].length && s[k][i][1] < .03;
        if (planted && start < 0) start = i;
        if (!planted && start >= 0) { check(start, i - 1); start = -1; }
      }
    }
  }
});

T('referenced GLBs exist and parse; each clips GLB animates its character with compatible node names', () => {
  for (const f of [idx.weapon.model, ...Object.values(idx.characters).flatMap(c => [c.model, c.clips_glb])]) {
    assert.ok(existsSync(resolve(ROOT, f)), 'missing ' + f);
    glb(f);
  }
  for (const [id, ch] of Object.entries(idx.characters)) {
    const model = glb(ch.model), anim = glb(ch.clips_glb);
    const modelNames = new Set(model.nodes.map(n => n.name));
    const names = new Set((anim.animations || []).map(a => a.name));
    for (const [n, c] of clips()) if (c.character === id) assert.ok(names.has(c.animation), `${ch.clips_glb} lacks animation ${c.animation}`);
    for (const a of anim.animations || []) for (const ch2 of a.channels) {
      const node = anim.nodes[ch2.target.node]?.name;
      assert.ok(modelNames.has(node), `${a.name} animates '${node}', which is not in ${ch.model}`);
    }
  }
  const sock = glb(idx.characters.aldren.model).nodes.map(n => n.name);
  for (const s of [idx.weapon.socket, idx.weapon.off_hand_socket]) assert.ok(sock.includes(s), 'aldren lacks socket ' + s);
  const sw = glb(idx.weapon.model).nodes.map(n => n.name);
  for (const s of ['hand_primary', 'hand_secondary', 'blade_base', 'blade_mid', 'blade_tip']) assert.ok(sw.includes(s), 'sword lacks ' + s);
});

T('Ser Aldren and William clip GLBs share identical arm-chain bone names', () => {
  const chain = rel => glb(rel).nodes.map(n => n.name).filter(n => ARM_CHAIN.test(n)).sort();
  const a = chain(idx.characters.aldren.clips_glb), w = chain(idx.characters.william.clips_glb);
  assert.ok(a.length >= 8, 'aldren arm chain: ' + a.join(','));
  assert.deepEqual(a, w);
});
