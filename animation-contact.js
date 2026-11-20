// Will of Steel v0.4.0 — animation contact geometry and shadow-mode telemetry.
// Pure ES module: no DOM, no Three.js, no randomness. NOT imported by the game. combat.js stays authoritative;
// nothing here can change combat state. Vectors are plain [x, y, z] arrays in metres (any consistent world frame).
// Blades are {base:[x,y,z], tip:[x,y,z]} (optionally mid / edge_dir). Times are seconds.

const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const len = a => Math.hypot(a[0], a[1], a[2]);
const lerp = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
const clamp01 = x => (x < 0 ? 0 : x > 1 ? 1 : x);
const unit = (v, fallback = [0, 1, 0]) => { const n = len(v); return n > 1e-9 ? mul(v, 1 / n) : fallback.slice(); };
const EPS = 1e-12;

export const DEFAULT_BLADE_RADIUS = 0.012;

/** Closest points between segments p0-p1 (A) and q0-q1 (B). s, t are normalized params on A and B. */
export function segmentSegmentClosest(p0, p1, q0, q1) {
  const d1 = sub(p1, p0), d2 = sub(q1, q0), r = sub(p0, q0);
  const a = dot(d1, d1), e = dot(d2, d2), f = dot(d2, r);
  let s, t;
  if (a <= EPS && e <= EPS) { s = 0; t = 0; }
  else if (a <= EPS) { s = 0; t = clamp01(f / e); }
  else {
    const c = dot(d1, r);
    if (e <= EPS) { t = 0; s = clamp01(-c / a); }
    else {
      const b = dot(d1, d2), denom = a * e - b * b;
      // Parallel segments (denom ~ 0): pick s = 0 and let the clamping below find the matching t.
      s = denom > EPS * a * e ? clamp01((b * f - c * e) / denom) : 0;
      t = (b * s + f) / e;
      if (t < 0) { t = 0; s = clamp01(-c / a); }
      else if (t > 1) { t = 1; s = clamp01((b - c) / a); }
    }
  }
  const pointA = add(p0, mul(d1, s)), pointB = add(q0, mul(d2, t));
  return { dist: len(sub(pointA, pointB)), s, t, pointA, pointB };
}

const lerpBlade = (p, c, u) => ({ base: lerp(p.base, c.base, u), tip: lerp(p.tip, c.tip, u) });
const maxTravel = (p, c) => Math.max(len(sub(c.base, p.base)), len(sub(c.tip, p.tip)));

function adaptiveSteps(base, travel, radius) {
  // Guarantee sub-steps no longer than one contact radius, bounded for cost.
  const need = radius > 0 ? Math.ceil(travel / radius) : base;
  return Math.max(1, Math.min(256, Math.max(base, need)));
}

/**
 * Continuous blade-vs-blade contact over one step. Blades are linearly interpolated (endpoints) between the
 * previous and current frame. Detects (a) distance <= radius at any sub-step and (b) blades passing through
 * each other between sub-steps (sign change of the separation along the common normal), so fast blades cannot
 * tunnel. Returns null or {u, point, normal (unit, B -> A), depth, along_a, along_b, rel_speed, dist}.
 * along_a / along_b are normalized positions (0 = base, 1 = tip). rel_speed is m/s using opts.dt (default 1/30).
 */
export function sweptBladeContact(prevA, curA, prevB, curB, opts = {}) {
  const radius = opts.radius ?? ((opts.radiusA ?? DEFAULT_BLADE_RADIUS) + (opts.radiusB ?? DEFAULT_BLADE_RADIUS));
  const dt = opts.dt ?? 1 / 30;
  prevA = prevA || curA; prevB = prevB || curB;
  const travel = maxTravel(prevA, curA) + maxTravel(prevB, curB);
  const n = opts.adaptive === false ? Math.max(1, opts.substeps ?? 8) : adaptiveSteps(opts.substeps ?? 8, travel, radius);
  let refNormal = null;
  const sample = u => {
    const A = lerpBlade(prevA, curA, u), B = lerpBlade(prevB, curB, u);
    const res = segmentSegmentClosest(A.base, A.tip, B.base, B.tip);
    let nrm = cross(sub(A.tip, A.base), sub(B.tip, B.base));
    const nl = len(nrm);
    let signed = null;
    if (nl > 1e-9) {
      nrm = mul(nrm, 1 / nl);
      if (refNormal && dot(nrm, refNormal) < 0) nrm = mul(nrm, -1);
      // Only meaningful when the closest points are interior on both segments (the lines' closest points).
      const interior = res.s > 1e-6 && res.s < 1 - 1e-6 && res.t > 1e-6 && res.t < 1 - 1e-6;
      if (interior) signed = dot(sub(res.pointA, res.pointB), nrm);
    }
    return { u, A, B, res, nrm: nl > 1e-9 ? nrm : null, signed };
  };
  const inContact = smp => smp.res.dist <= radius;
  let prev = sample(0);
  refNormal = prev.nrm;
  if (inContact(prev)) return finish(prev, prev, prevA, curA, prevB, curB, radius, dt);
  for (let i = 1; i <= n; i++) {
    const cur = sample(i / n);
    if (cur.nrm) refNormal = cur.nrm;
    if (inContact(cur)) return finish(refine(prev, cur, sample, inContact), prev, prevA, curA, prevB, curB, radius, dt);
    if (prev.signed !== null && cur.signed !== null && prev.signed * cur.signed < 0) {
      // Tunnelled between sub-steps: bisect on the sign of the separation to find the crossing.
      let lo = prev, hi = cur;
      for (let k = 0; k < 40; k++) {
        const mid = sample((lo.u + hi.u) / 2);
        if (inContact(mid)) return finish(refine(lo, mid, sample, inContact), prev, prevA, curA, prevB, curB, radius, dt);
        if (mid.signed === null) break;
        if (mid.signed * lo.signed > 0) lo = mid; else hi = mid;
      }
    }
    prev = cur;
  }
  return null;
}

function refine(outside, inside, sample, test) {
  let lo = outside, hi = inside;
  for (let k = 0; k < 30; k++) {
    const mid = sample((lo.u + hi.u) / 2);
    if (test(mid)) hi = mid; else lo = mid;
  }
  return hi;
}

function finish(hit, before, prevA, curA, prevB, curB, radius, dt) {
  const { res } = hit;
  let normal = sub(res.pointA, res.pointB);
  if (len(normal) > 1e-9) normal = unit(normal);
  else if (before.signed !== null && before.nrm) normal = mul(before.nrm, before.signed >= 0 ? 1 : -1);
  else normal = unit(sub(res.pointA, res.pointB), [0, 1, 0]);
  const vel = (p, c, s) => mul(sub(lerp(c.base, c.tip, s), lerp(p.base, p.tip, s)), 1 / dt);
  const relSpeed = len(sub(vel(prevA, curA, res.s), vel(prevB, curB, res.t)));
  return {
    u: hit.u, point: lerp(res.pointA, res.pointB, 0.5), normal, depth: Math.max(0, radius - res.dist), dist: res.dist,
    along_a: res.s, along_b: res.t, rel_speed: relSpeed,
  };
}

/**
 * Continuous blade-vs-body test. capsules: [{name, a:[x,y,z], b:[x,y,z], r}] (static during the step).
 * Returns the earliest hit {name, u, point (on blade), normal (unit, capsule axis -> blade), depth, along} or null.
 */
export function sweptBladeBody(prevBlade, curBlade, capsules, opts = {}) {
  if (!capsules || !capsules.length) return null;
  const bladeR = opts.bladeRadius ?? DEFAULT_BLADE_RADIUS;
  prevBlade = prevBlade || curBlade;
  const minR = Math.min(...capsules.map(c => c.r)) + bladeR;
  const n = opts.adaptive === false ? Math.max(1, opts.substeps ?? 8) : adaptiveSteps(opts.substeps ?? 8, maxTravel(prevBlade, curBlade), minR);
  const test = (u, cap) => {
    const B = lerpBlade(prevBlade, curBlade, u);
    const res = segmentSegmentClosest(B.base, B.tip, cap.a, cap.b);
    return { res, hit: res.dist <= cap.r + bladeR };
  };
  let best = null;
  for (const cap of capsules) {
    let prevU = 0;
    for (let i = 0; i <= n; i++) {
      const u = i / n;
      if (!test(u, cap).hit) { prevU = u; continue; }
      let lo = prevU, hi = u;
      if (i > 0) for (let k = 0; k < 30; k++) { const m = (lo + hi) / 2; if (test(m, cap).hit) hi = m; else lo = m; }
      else hi = 0;
      if (!best || hi < best.u) {
        const { res } = test(hi, cap);
        best = { name: cap.name, u: hi, point: res.pointA, normal: unit(sub(res.pointA, res.pointB)),
          depth: Math.max(0, cap.r + bladeR - res.dist), along: res.s };
      }
      break;
    }
  }
  return best;
}

/** Blade point velocities between two frames. edge_alignment = cos(edge_dir, tip velocity direction) or null. */
export function bladeKinematics(prev, cur, dt) {
  dt = dt > 0 ? dt : 1 / 30;
  const mid = b => b.mid || lerp(b.base, b.tip, 0.5);
  const velocity_tip = mul(sub(cur.tip, prev.tip), 1 / dt);
  const velocity_mid = mul(sub(mid(cur), mid(prev)), 1 / dt);
  const speed_tip = len(velocity_tip);
  const edge = cur.edge_dir || prev.edge_dir;
  const edge_alignment = edge && speed_tip > 1e-9 && len(edge) > 1e-9 ? dot(unit(edge), mul(velocity_tip, 1 / speed_tip)) : null;
  return { velocity_tip, velocity_mid, speed_tip, speed_mid: len(velocity_mid), edge_alignment };
}

export const MISMATCH = Object.freeze([
  'damage_without_contact', 'visible_intersection_without_clash', 'parry_success_while_separated',
  'blade_through_body', 'hit_reaction_timing',
]);
const DAMAGE = new Set(['enemyHit', 'playerHit']);
const DEFENCE = new Set(['parry', 'clash']);

/**
 * Shadow-mode telemetry. Feed one state per rendered frame:
 *   {t, attacker:{blade, phase, clip}, defender:{blade, phase, body?:[capsules]}, combatEvents:[{type, time?, ...}]}
 * It never changes combat; it only observes and reports. Contacts are de-duplicated into episodes: an episode
 * continues while contact recurs within `cooldown_s` of its last contact frame.
 *
 * Mismatch rules (each finalized once its matching window has elapsed; call finish() at the end):
 *  - damage_without_contact: an enemyHit/playerHit with no blade–body episode starting within ±window_s.
 *  - hit_reaction_timing: an enemyHit/playerHit matched to a body episode whose start differs by more than
 *    timing_tolerance_ms; reports timing 'early' (event before contact) or 'late' and delta_ms (event − contact).
 *  - visible_intersection_without_clash: a blade–blade episode with no parry/clash event within ±window_s.
 *  - parry_success_while_separated: a parry (or clash) event with no blade–blade episode within ±window_s;
 *    reports the minimum blade separation observed in that window.
 *  - blade_through_body: a blade–body episode not explained by any damage event within ±window_s
 *    (the blade visibly passes through a body with no hit in combat); reports max penetration depth.
 */
export class ContactTelemetry {
  constructor(opts = {}) {
    this.opts = {
      cooldown_s: 0.15, window_s: 0.2, timing_tolerance_ms: 50, substeps: 8,
      bladeRadiusA: DEFAULT_BLADE_RADIUS, bladeRadiusB: DEFAULT_BLADE_RADIUS, bodyCapsules: null, ...opts,
    };
    this.events = [];
    this.mismatches = [];
    this.episodes = { blade: [], body: [] };
    this.combat = [];
    this.separation = []; // [{t, dist}] blade-blade separation per frame (for parry diagnostics)
    this.prev = null;
    this.now = -Infinity;
    this.frames = 0;
  }

  ingest(state) {
    const o = this.opts, t = state.t, prev = this.prev;
    this.frames++;
    const A = state.attacker?.blade, B = state.defender?.blade;
    const dt = prev ? Math.max(1e-6, t - prev.t) : 1 / 30;
    if (A && B) {
      const sep = segmentSegmentClosest(A.base, A.tip, B.base, B.tip).dist;
      this.separation.push({ t, dist: sep });
      const c = sweptBladeContact(prev?.attacker?.blade || A, A, prev?.defender?.blade || B, B,
        { substeps: o.substeps, radiusA: o.bladeRadiusA, radiusB: o.bladeRadiusB, dt });
      if (c) this._contact('blade', (prev ? prev.t : t) + c.u * (prev ? dt : 0), t, {
        point: c.point, normal: c.normal, depth: c.depth, rel_speed: c.rel_speed, along_a: c.along_a, along_b: c.along_b,
        clip: state.attacker?.clip ?? null, phase: state.attacker?.phase ?? null,
      });
    }
    const caps = state.defender?.body || o.bodyCapsules;
    if (A && caps) {
      const h = sweptBladeBody(prev?.attacker?.blade || A, A, caps, { substeps: o.substeps, bladeRadius: o.bladeRadiusA });
      if (h) this._contact('body', (prev ? prev.t : t) + h.u * (prev ? dt : 0), t, {
        point: h.point, normal: h.normal, depth: h.depth, name: h.name,
        clip: state.attacker?.clip ?? null, phase: state.attacker?.phase ?? null,
      });
    }
    for (const ev of state.combatEvents || []) {
      if (!DAMAGE.has(ev.type) && !DEFENCE.has(ev.type)) continue;
      const rec = { type: ev.type, t: ev.t ?? ev.time ?? t, dir: ev.dir ?? null, matched: null, final: false };
      this.combat.push(rec);
      this.events.push({ kind: 'combat', type: rec.type, t: rec.t, dir: rec.dir });
    }
    this.prev = { t, attacker: state.attacker ? { ...state.attacker } : null, defender: state.defender ? { ...state.defender } : null };
    this.now = t;
    this._finalize(t);
  }

  _contact(kind, tHit, tFrame, info) {
    const list = this.episodes[kind], last = list[list.length - 1];
    if (last && tHit - last.lastFrame <= this.opts.cooldown_s + 1e-9) {
      last.lastFrame = tFrame; last.frames++;
      last.maxDepth = Math.max(last.maxDepth, info.depth);
      return;
    }
    const ep = { kind, start: tHit, lastFrame: tFrame, frames: 1, maxDepth: info.depth, ...info, matched: null, final: false };
    list.push(ep);
    this.events.push({ kind: kind === 'blade' ? 'blade_contact' : 'body_contact', t: tHit, point: info.point, depth: info.depth,
      name: info.name ?? null, clip: info.clip, phase: info.phase });
  }

  _nearest(list, t, w, filter = () => true) {
    let best = null;
    for (const ep of list) {
      if (ep.matched || !filter(ep)) continue;
      const d = Math.abs(ep.start - t);
      if (d <= w + 1e-9 && (!best || d < Math.abs(best.start - t))) best = ep;
    }
    return best;
  }

  _finalize(now) {
    const { window_s: w, cooldown_s: cd, timing_tolerance_ms: tol } = this.opts;
    // 1) Combat events whose window has elapsed: match to the nearest unmatched episode of the right kind.
    for (const ev of this.combat) {
      if (ev.final || now < ev.t + w) continue;
      ev.final = true;
      if (DAMAGE.has(ev.type)) {
        const ep = this._nearest(this.episodes.body, ev.t, w);
        if (!ep) { this._mismatch('damage_without_contact', ev.t, { event_type: ev.type, dir: ev.dir }); continue; }
        ep.matched = ev; ev.matched = ep;
        const delta = (ev.t - ep.start) * 1000;
        if (Math.abs(delta) > tol) this._mismatch('hit_reaction_timing', ev.t, {
          event_type: ev.type, dir: ev.dir, timing: delta < 0 ? 'early' : 'late', delta_ms: Math.round(delta * 10) / 10, contact_t: ep.start,
        });
      } else {
        const ep = this._nearest(this.episodes.blade, ev.t, w);
        if (!ep) {
          let minSep = null;
          for (const s of this.separation) if (Math.abs(s.t - ev.t) <= w + 1e-9 && (minSep === null || s.dist < minSep)) minSep = s.dist;
          this._mismatch('parry_success_while_separated', ev.t, { event_type: ev.type, dir: ev.dir, min_separation_m: minSep });
          continue;
        }
        ep.matched = ev; ev.matched = ep;
      }
    }
    // 2) Episodes that are complete and can no longer be claimed by a pending combat event.
    for (const kind of ['blade', 'body']) for (const ep of this.episodes[kind]) {
      if (ep.final || now < Math.max(ep.lastFrame + cd, ep.start + 2 * w)) continue;
      ep.final = true;
      if (ep.matched) continue;
      if (kind === 'blade') this._mismatch('visible_intersection_without_clash', ep.start, { point: ep.point, clip: ep.clip, phase: ep.phase, rel_speed: ep.rel_speed });
      else this._mismatch('blade_through_body', ep.start, { point: ep.point, part: ep.name, max_depth_m: ep.maxDepth, clip: ep.clip, phase: ep.phase });
    }
  }

  _mismatch(category, t, info) {
    const m = { kind: 'mismatch', category, t, ...info };
    this.mismatches.push(m);
    this.events.push(m);
  }

  /** Finalize everything still pending (end of a recording). */
  finish() { this._finalize(Infinity); return this.summary(); }

  summary() {
    const counts = Object.fromEntries(MISMATCH.map(k => [k, 0]));
    for (const m of this.mismatches) counts[m.category]++;
    return {
      frames: this.frames, blade_contacts: this.episodes.blade.length, body_contacts: this.episodes.body.length,
      combat_events: this.combat.length, pending: this.combat.filter(e => !e.final).length +
        this.episodes.blade.filter(e => !e.final).length + this.episodes.body.filter(e => !e.final).length,
      mismatches: counts, mismatch_total: this.mismatches.length,
    };
  }
}
