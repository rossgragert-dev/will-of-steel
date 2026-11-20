import test from 'node:test';
import assert from 'node:assert/strict';
import {segmentSegmentClosest, sweptBladeContact, sweptBladeBody, bladeKinematics, ContactTelemetry, MISMATCH} from '../animation-contact.js';

const near = (a, b, eps = 1e-6) => assert.ok(Math.abs(a - b) <= eps, `${a} != ${b} (±${eps})`);
const nearV = (a, b, eps = 1e-6) => a.forEach((v, i) => near(v, b[i], eps));
const blade = (base, tip) => ({base, tip});

test('segment closest: crossing segments meet at their midpoints', () => {
  const r = segmentSegmentClosest([-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0]);
  near(r.dist, 0); near(r.s, .5); near(r.t, .5); nearV(r.pointA, [0, 0, 0]); nearV(r.pointB, [0, 0, 0]);
});

test('segment closest: skew segments use the common perpendicular', () => {
  const r = segmentSegmentClosest([-1, 0, 0], [1, 0, 0], [0, -1, .3], [0, 1, .3]);
  near(r.dist, .3); nearV(r.pointA, [0, 0, 0]); nearV(r.pointB, [0, 0, .3]);
});

test('segment closest: parallel overlapping and parallel disjoint segments', () => {
  const r = segmentSegmentClosest([0, 0, 0], [1, 0, 0], [.5, .2, 0], [1.5, .2, 0]);
  near(r.dist, .2);
  const d = segmentSegmentClosest([0, 0, 0], [1, 0, 0], [2, 0, 0], [3, 0, 0]);
  near(d.dist, 1); near(d.s, 1); near(d.t, 0);
});

test('segment closest: endpoint-to-interior and endpoint-to-endpoint cases', () => {
  const r = segmentSegmentClosest([0, 0, 0], [1, 0, 0], [2, -1, 0], [2, 1, 0]);
  near(r.dist, 1); near(r.s, 1); near(r.t, .5);
  const e = segmentSegmentClosest([0, 0, 0], [1, 0, 0], [2, 1, 0], [3, 2, 0]);
  near(e.dist, Math.SQRT2); near(e.s, 1); near(e.t, 0);
  const pt = segmentSegmentClosest([0, 0, 0], [0, 0, 0], [-1, 1, 0], [1, 1, 0]);
  near(pt.dist, 1); near(pt.t, .5);
});

// A fast cut: blade A sweeps 0.6 m in one 1/30 s frame straight through a static blade B.
const B0 = blade([0, -.5, 0], [0, .5, 0]);
const Aprev = blade([-.5, 0, -.3], [.5, 0, -.3]), Acur = blade([-.5, 0, .3], [.5, 0, .3]);

test('swept contact catches a tunnelling blade that discrete end-of-frame checks miss', () => {
  const r2 = .024;
  assert.ok(segmentSegmentClosest(Aprev.base, Aprev.tip, B0.base, B0.tip).dist > r2);
  assert.ok(segmentSegmentClosest(Acur.base, Acur.tip, B0.base, B0.tip).dist > r2);
  // Even with fixed, too-few sub-steps the sign-change test finds the crossing.
  for (const opts of [{}, {adaptive: false, substeps: 1}, {adaptive: false, substeps: 8}]) {
    const c = sweptBladeContact(Aprev, Acur, B0, B0, opts);
    assert.ok(c, 'contact expected for ' + JSON.stringify(opts));
    assert.ok(c.u > .4 && c.u < .5, 'contact time before crossing midpoint: ' + c.u);
    near(c.normal[2], -1, 1e-3); // from B toward A, A approaches from -Z
    near(c.along_a, .5, 1e-3); near(c.along_b, .5, 1e-3);
    near(c.rel_speed, .6 * 30, 1e-6);
    assert.ok(c.depth >= 0 && c.depth <= r2);
  }
});

test('swept contact: no false positive for separated blades and for near misses', () => {
  assert.equal(sweptBladeContact(blade([-.5, 0, 1], [.5, 0, 1]), blade([-.5, 0, 1.2], [.5, 0, 1.2]), B0, B0), null);
  // A passes 3 cm beyond B's tip: the infinite lines cross but the segments never come within 2.4 cm.
  const over = sweptBladeContact(blade([-.5, .53, -.3], [.5, .53, -.3]), blade([-.5, .53, .3], [.5, .53, .3]), B0, B0);
  assert.equal(over, null);
  // Parallel blades 5 cm apart moving together.
  assert.equal(sweptBladeContact(blade([0, 0, 0], [0, 1, 0]), blade([.1, 0, 0], [.1, 1, 0]), blade([.05, 0, 0], [.05, 1, 0]), blade([.15, 0, 0], [.15, 1, 0])), null);
});

test('swept contact reports immediate contact at u=0 and is deterministic', () => {
  const c = sweptBladeContact(blade([-.5, 0, .01], [.5, 0, .01]), blade([-.5, 0, .01], [.5, 0, .01]), B0, B0);
  near(c.u, 0); nearV(c.normal, [0, 0, 1], 1e-9);
  const a = JSON.stringify(sweptBladeContact(Aprev, Acur, B0, B0)), b = JSON.stringify(sweptBladeContact(Aprev, Acur, B0, B0));
  assert.equal(a, b);
});

const BODY = [
  {name: 'head', a: [0, 1.55, 0], b: [0, 1.75, 0], r: .12},
  {name: 'torso', a: [0, .95, 0], b: [0, 1.45, 0], r: .17},
];

test('swept blade-body: earliest capsule wins, misses return null', () => {
  // Horizontal blade sweeping from z=-1 to z=+1 at head height through the head capsule.
  const h = sweptBladeBody(blade([-.5, 1.65, -1], [.5, 1.65, -1]), blade([-.5, 1.65, 1], [.5, 1.65, 1]), BODY);
  assert.equal(h.name, 'head');
  near(h.u, (1 - .132) / 2, 1e-3);
  nearV(h.normal, [0, 0, -1], 1e-3);
  // Diagonal sweep that reaches the torso first.
  const t = sweptBladeBody(blade([-.5, 1.2, -1], [.5, 1.2, -1]), blade([-.5, 1.2, 1], [.5, 1.2, 1]), BODY);
  assert.equal(t.name, 'torso');
  assert.equal(sweptBladeBody(blade([-.5, 1.65, -1], [.5, 1.65, -1]), blade([-.5, 1.65, -.5], [.5, 1.65, -.5]), BODY), null);
  assert.equal(sweptBladeBody(blade([0, 0, 0], [0, 1, 0]), blade([0, 0, 0], [0, 1, 0]), []), null);
});

test('blade kinematics: velocity, speed and edge alignment', () => {
  const k = bladeKinematics({base: [0, 0, 0], tip: [0, 1, 0]}, {base: [0, 0, 0], tip: [.1, 1, 0], edge_dir: [1, 0, 0]}, .1);
  nearV(k.velocity_tip, [1, 0, 0]); near(k.speed_tip, 1); near(k.edge_alignment, 1); nearV(k.velocity_mid, [.5, 0, 0]);
  const flat = bladeKinematics({base: [0, 0, 0], tip: [0, 1, 0]}, {base: [0, 0, 0], tip: [.1, 1, 0], edge_dir: [0, 0, 1]}, .1);
  near(flat.edge_alignment, 0);
  assert.equal(bladeKinematics({base: [0, 0, 0], tip: [0, 1, 0]}, {base: [0, 0, 0], tip: [0, 1, 0]}, .1).edge_alignment, null);
});

// ---- Telemetry scenarios (30 fps, synthetic) --------------------------------------------------------------
const FAR = blade([-.5, 0, 2], [.5, 0, 2]);           // attacker blade far from everything
const DEF = blade([0, -.5, 0], [0, .5, 0]);            // defender blade (vertical at origin)
const CROSS = blade([-.5, 0, 0], [.5, 0, 0]);          // attacker blade crossing the defender blade
const IN_HEAD = blade([-.5, 1.65, 0], [.5, 1.65, 0]);  // attacker blade through the defender's head capsule
const BODY_AWAY = [{name: 'head', a: [0, 1.55, 5], b: [0, 1.75, 5], r: .12}];

function run(script, frames = 40, opts = {}) {
  const tel = new ContactTelemetry({bodyCapsules: opts.body || BODY_AWAY, ...opts});
  for (let i = 0; i < frames; i++) {
    const t = i / 30, s = script(i, t) || {};
    tel.ingest({t, attacker: {blade: s.a || FAR, phase: 'attack', clip: 'synthetic'}, defender: {blade: s.d || DEF, phase: 'hold', body: s.body},
      combatEvents: s.ev || []});
  }
  return tel.finish();
}
const only = (summary, category) => {
  for (const k of MISMATCH) assert.equal(summary.mismatches[k], k === category ? 1 : 0, `${k} count in ${JSON.stringify(summary.mismatches)}`);
};

test('telemetry: dedupes a contiguous contact into one episode; cooldown separates episodes', () => {
  const one = run(i => (i >= 10 && i < 16 ? {a: CROSS, ev: i === 10 ? [{type: 'clash'}] : []} : {}));
  assert.equal(one.blade_contacts, 1); assert.equal(one.mismatch_total, 0); assert.equal(one.pending, 0);
  // Gap of 2 frames (66 ms) is within the default 150 ms cooldown -> still one episode.
  const gap = run(i => (i === 10 || i === 11 || i === 14 ? {a: CROSS, ev: i === 10 ? [{type: 'clash'}] : []} : {}));
  assert.equal(gap.blade_contacts, 1);
  // Gap of 10 frames -> two episodes, each needing its own clash.
  const two = run(i => (i === 10 || i === 21 ? {a: CROSS, ev: [{type: 'parry'}]} : {}));
  assert.equal(two.blade_contacts, 2); assert.equal(two.mismatch_total, 0);
  const tight = run(i => (i === 10 || i === 14 ? {a: CROSS, ev: i === 10 ? [{type: 'clash'}] : []} : {}), 40, {cooldown_s: .05});
  assert.equal(tight.blade_contacts, 2); only(tight, 'visible_intersection_without_clash');
});

test('telemetry: clean exchange produces no mismatch', () => {
  const s = run(i => {
    if (i === 10) return {a: CROSS, ev: [{type: 'parry'}]};
    if (i === 25) return {a: IN_HEAD, ev: [{type: 'enemyHit'}]};
    return {};
  }, 50, {body: BODY});
  assert.equal(s.mismatch_total, 0); assert.equal(s.blade_contacts, 1); assert.equal(s.body_contacts, 1);
});

test('telemetry: damage_without_contact', () => {
  only(run(i => (i === 10 ? {ev: [{type: 'playerHit'}]} : {})), 'damage_without_contact');
});

test('telemetry: visible_intersection_without_clash', () => {
  only(run(i => (i === 10 ? {a: CROSS} : {})), 'visible_intersection_without_clash');
});

test('telemetry: parry_success_while_separated reports the separation', () => {
  const tel = new ContactTelemetry({bodyCapsules: BODY_AWAY});
  for (let i = 0; i < 30; i++) tel.ingest({t: i / 30, attacker: {blade: FAR}, defender: {blade: DEF}, combatEvents: i === 10 ? [{type: 'parry'}] : []});
  only(tel.finish(), 'parry_success_while_separated');
  const m = tel.mismatches[0];
  assert.equal(m.event_type, 'parry'); near(m.min_separation_m, 2, 1e-9);
});

test('telemetry: blade_through_body', () => {
  only(run(i => (i === 10 ? {a: IN_HEAD} : {}), 40, {body: BODY}), 'blade_through_body');
});

test('telemetry: hit_reaction_timing early and late, not when within tolerance', () => {
  const late = new ContactTelemetry({bodyCapsules: BODY});
  for (let i = 0; i < 40; i++) late.ingest({t: i / 30, attacker: {blade: i === 10 ? IN_HEAD : FAR}, defender: {blade: DEF},
    combatEvents: i === 13 ? [{type: 'enemyHit', time: 13 / 30}] : []});
  only(late.finish(), 'hit_reaction_timing');
  const m = late.mismatches[0];
  assert.equal(m.timing, 'late'); assert.ok(m.delta_ms > 50 && m.delta_ms <= 110, String(m.delta_ms));
  const early = run(i => (i === 7 ? {ev: [{type: 'enemyHit'}]} : i === 10 ? {a: IN_HEAD} : {}), 40, {body: BODY});
  only(early, 'hit_reaction_timing');
  const ok = run(i => (i === 10 ? {a: IN_HEAD, ev: [{type: 'enemyHit'}]} : {}), 40, {body: BODY});
  assert.equal(ok.mismatch_total, 0);
});

test('telemetry: fast tunnelling cut is still one contact (swept, not discrete)', () => {
  const s = run(i => (i === 10 ? {a: blade([-.5, 0, -.3], [.5, 0, -.3])} : i === 11 ? {a: blade([-.5, 0, .3], [.5, 0, .3]), ev: [{type: 'clash'}]} : {}));
  assert.equal(s.blade_contacts, 1); assert.equal(s.mismatch_total, 0);
});

test('telemetry is deterministic and does not mutate its inputs', () => {
  const states = [];
  for (let i = 0; i < 30; i++) states.push({t: i / 30, attacker: {blade: i === 10 ? IN_HEAD : i === 15 ? CROSS : FAR, phase: 'attack'},
    defender: {blade: DEF, phase: 'hold'}, combatEvents: i === 20 ? [{type: 'playerHit'}] : []});
  const frozen = JSON.stringify(states);
  const go = () => { const t = new ContactTelemetry({bodyCapsules: BODY}); for (const s of states) t.ingest(s); t.finish(); return JSON.stringify(t.events); };
  assert.equal(go(), go());
  assert.equal(JSON.stringify(states), frozen);
});
