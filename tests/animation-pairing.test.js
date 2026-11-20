// Paired-clip contact validation (C.7, shadow mode): an attack and the matching parry, placed at the engagement
// guard distance with contact frames aligned, must physically meet (swept blade-to-blade contact) near the planned
// contact frame, instead of the attack passing under/over the parry.
import test from 'node:test';
import assert from 'node:assert/strict';
import {existsSync, readFileSync} from 'node:fs';
import {sweptBladeContact} from '../animation-contact.js';

const INDEX = 'assets/v0.4.0/animations/clips_index_v003.json';
const have = existsSync(INDEX);
const idx = have ? JSON.parse(readFileSync(INDEX, 'utf8')) : null;
const D = have ? idx.engagement.guard_distance_m : 1.65;
// William at the origin facing +Z; Ser Aldren at z = D facing William (rotated 180 deg about Y).
const toWorldAldren = p => [-p[0], p[1], D - p[2]];
const blade = (c, f, xf = p => p, advance = 0) => ({base: xf(c.samples.blade_base[f]).map((v, i) => v + (i === 2 ? advance : 0)),
                                                    tip: xf(c.samples.blade_tip[f]).map((v, i) => v + (i === 2 ? advance : 0))});

function firstContact(att, attXf, attAdv, def, defXf, shift, range) {
  // attacker frame fa, defender frame fa + shift; returns the first attacker frame whose swept step contacts
  for (let fa = range[0]; fa <= range[1]; fa++) {
    const fd = Math.min(Math.max(fa + shift, 1), def.frame_end);
    const a0 = blade(att, fa - 1, attXf, attAdv(fa - 1)), a1 = blade(att, fa, attXf, attAdv(fa));
    const d0 = blade(def, fd - 1, defXf), d1 = blade(def, fd, defXf);
    const hit = sweptBladeContact(a0, a1, d0, d1, {substeps: 16});
    if (hit) return {frame: fa, hit};
  }
  return null;
}

test('Ser Aldren overhead meets William roof parry at the planned contact', t => {
  if (!have) return t.skip('clips not generated yet');
  const att = idx.clips.aldren_attack_head, def = idx.clips.william_parry_head;
  // William raises at f0..6 and is in the hold by the expected impact; align parry expected impact with attack contact
  const shift = def.expected_contact_frame - att.contact_frame;
  const r = firstContact(att, toWorldAldren, () => 0, def, p => p, shift, [12, att.frame_end]);
  assert.ok(r, 'attack never touches the parry (passes under or over it)');
  assert.ok(Math.abs(r.frame - att.contact_frame) <= 3, `contact at f${r.frame}, planned f${att.contact_frame}`);
});

test('William overhead (with suggested step-in) meets Ser Aldren roof parry at the planned contact', t => {
  if (!have) return t.skip('clips not generated yet');
  const att = idx.clips.william_attack_head, def = idx.clips.aldren_parry_head;
  const adv = f => att.camera_advance_m ? att.camera_advance_m[f] : 0;
  const shift = def.expected_contact_frame - att.contact_frame;
  const r = firstContact(att, p => p, adv, def, toWorldAldren, shift, [12, att.frame_end]);
  assert.ok(r, 'attack never touches the parry (passes under or over it)');
  assert.ok(Math.abs(r.frame - att.contact_frame) <= 3, `contact at f${r.frame}, planned f${att.contact_frame}`);
});
