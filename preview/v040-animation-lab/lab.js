// Will of Steel v0.4.0 — isolated animation laboratory. Read-only QA tool; not part of the game.
// Loads clips_index_v003.json (if present), the character GLBs, the longsword, applies clip GLBs through
// THREE.AnimationMixer (tracks bind by node name), attaches the sword per the asset convention and measures.
import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {sampleClip} from '../../motion.js';
import {sweptBladeContact, sweptBladeBody, segmentSegmentClosest, ContactTelemetry} from '../../animation-contact.js';

const $ = id => document.getElementById(id);
const ROOT = '../../';
const INDEX_URL = ROOT + 'assets/v0.4.0/animations/clips_index_v003.json';
// Used only when the clips index does not exist yet (static models).
const FALLBACK = {
  fps: 30,
  engagement: {guard_distance_m: 1.65, contact_distance_m: 1.45, attack_step_m: .20},
  characters: {
    aldren: {model: 'assets/v0.4.0/characters/ser_aldren_v006.glb', clips_glb: null, view: 'third_person'},
    william: {model: 'assets/v0.4.0/first-person/william_fp_arms_v004.glb', clips_glb: null, view: 'first_person'},
  },
  weapon: {model: 'assets/v0.4.0/weapons/longsword_xva_v006.glb', socket: 'weapon_r', off_hand_socket: 'grip_l'},
  clips: {},
};
const GUARDS_URL = ROOT + 'assets/v0.4.0/first-person/william_fp_guards_v004.json';
const PHASE_COLORS = {prepare: '#8aa', windup: '#cc9', attack: '#e66', follow_through: '#e94', recovery: '#8c8', raise: '#9cf', hold: '#6af', recover: '#8c8', impact: '#f66', absorb: '#fa6', settle: '#8c8'};

// ---------- URL params ----------
const P = new URLSearchParams(location.search);
const want = {
  char: P.get('char'), clip: P.get('clip'), clip2: P.get('clip2'), frame: P.has('frame') ? Number(P.get('frame')) : null,
  cam: P.get('cam'), overlays: P.has('overlays') ? P.get('overlays').split(',').filter(Boolean) : null,
  paused: P.get('paused') === '1', dist: P.has('dist') ? Number(P.get('dist')) : null, perf: P.get('perf') === '1',
  perfFrames: Number(P.get('perfFrames') || 120), ui: P.get('ui'),
};
if (want.ui === 'stage') document.body.classList.add('ui-stage');

// ---------- renderer / scene ----------
const host = $('viewport');
const automation = P.has('paused') || P.has('frame') || want.perf;
const renderer = new T.WebGLRenderer({antialias: true, powerPreference: 'high-performance', preserveDrawingBuffer: automation});
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 1.6));
renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.25; renderer.outputColorSpace = T.SRGBColorSpace;
host.appendChild(renderer.domElement);
const scene = new T.Scene(); scene.background = new T.Color(0x263033);
const camera = new T.PerspectiveCamera(45, 1, .01, 200);
const orbit = new OrbitControls(camera, renderer.domElement); orbit.enableDamping = true; orbit.minDistance = .2; orbit.maxDistance = 30;
scene.add(new T.HemisphereLight(0xddeeff, 0x596368, 2.0));
const key = new T.DirectionalLight(0xffe7c6, 2.6); key.position.set(-4, 7, 5); scene.add(key);
const fill = new T.DirectionalLight(0xa4c9ff, 1.1); fill.position.set(4, 2, -4); scene.add(fill);
try { const pm = new T.PMREMGenerator(renderer); scene.environment = pm.fromScene(new RoomEnvironment(), .04).texture; pm.dispose(); } catch (e) { console.warn('env fallback', e); }
const grid = new T.GridHelper(10, 40, 0x7b745c, 0x3c4649); scene.add(grid);
const floor = new T.Mesh(new T.CircleGeometry(6, 48), new T.MeshStandardMaterial({color: 0x2c3537, roughness: .95}));
floor.rotation.x = -Math.PI / 2; floor.position.y = -.002; scene.add(floor);

// ---------- state ----------
const S = {
  index: null, clipsAvailable: false, fps: 30, chars: {}, mode: 'aldren', dist: 1.65, cam: 'orbit', frame: 0, playing: false, loop: true,
  speed: 1, overlays: new Set(['path', 'contact', 'mesh']), timeline: null, guards: null, ready: false,
};
const overlayRoot = new T.Group(); scene.add(overlayRoot);
const loader = new GLTFLoader();
const loadGLB = url => new Promise((res, rej) => loader.load(url, res, undefined, rej));
const V = () => new T.Vector3();
const tmpM = new T.Matrix4(), tmpV = V(), tmpV2 = V();
// Sword local -> socket bone: sword +Y -> bone +Y (blade), sword +X (true edge) -> bone +Z, sword +Z -> bone -X;
// then translate so hand_primary (sword local (0,-0.05,0)) sits on the bone origin.
const SWORD_R = new T.Matrix4().makeBasis(new T.Vector3(0, 0, 1), new T.Vector3(0, 1, 0), new T.Vector3(-1, 0, 0));
const SWORD_T = new T.Matrix4().makeTranslation(0, .05, 0);
const SWORD_OFFSET = new T.Matrix4().multiplyMatrices(SWORD_R, SWORD_T);

function status(msg) { $('status').textContent = msg; }

// ---------- character setup ----------
async function loadCharacter(id, cfg, swordScene) {
  const gltf = await loadGLB(ROOT + cfg.model);
  const holder = new T.Group(); holder.name = 'holder_' + id; holder.add(gltf.scene); scene.add(holder);
  const bones = {}; const meshes = [];
  gltf.scene.traverse(o => { if (o.name) bones[o.name] = bones[o.name] || o; if (o.isMesh) { meshes.push(o); o.frustumCulled = false; } });
  const sword = swordScene.clone(true); sword.matrixAutoUpdate = false; scene.add(sword);
  const sw = {}; sword.traverse(o => { if (o.name) sw[o.name] = o; });
  const c = {id, cfg, gltf, holder, bones, meshes, sword, sw, mixer: new T.AnimationMixer(gltf.scene), clips: {}, action: null, clipName: null,
    skel: null, measured: null};
  if (cfg.clips_glb && S.clipsAvailable) {
    try {
      const anim = await loadGLB(ROOT + cfg.clips_glb);
      for (const a of anim.animations) c.clips[a.name] = a;
    } catch (e) { console.warn('clips GLB failed for ' + id, e); c.clipsError = String(e.message || e); }
  }
  return c;
}

function attachSword(c) {
  const sock = c.bones[S.index.weapon?.socket || 'weapon_r'];
  if (!sock) return;
  c.sword.matrix.multiplyMatrices(sock.matrixWorld, SWORD_OFFSET);
  c.sword.matrixWorld.copy(c.sword.matrix);
  for (const ch of c.sword.children) ch.updateMatrixWorld(true);
}
const wpos = (o, out = V()) => (o ? out.setFromMatrixPosition(o.matrixWorld) : null);

function setClip(c, name) {
  if (c.action) { c.action.stop(); c.action = null; }
  c.clipName = name || null;
  const clip = name && c.clips[name];
  if (clip) {
    const a = c.mixer.clipAction(clip); a.setLoop(T.LoopRepeat, Infinity); a.reset(); a.play(); c.action = a;
  }
}
const meta = name => (name && S.index.clips?.[name]) || null;
function clipFrames(c) { const m = meta(c.clipName); return m ? m.frame_end : 0; }
function localFrame(c, f) {
  const m = meta(c.clipName); if (!m) return 0;
  const len = m.frame_end - m.frame_start;
  if (m.loop && len > 0) return m.frame_start + (((f - m.frame_start) % len) + len) % len;
  return Math.min(Math.max(f, m.frame_start), m.frame_end);
}
function poseAt(c, f) {
  if (c.action) {
    const lf = localFrame(c, f), dur = c.action.getClip().duration;
    c.action.time = Math.min(Math.max(0, lf / S.fps), Math.max(0, dur - 1e-4));
    c.mixer.update(0);
  }
  c.holder.updateMatrixWorld(true);
  attachSword(c);
}

// ---------- measurement (per timeline frame, world space) ----------
function elbowFlex(c, s) {
  const sh = wpos(c.bones['upperarm_' + s]), el = wpos(c.bones['forearm_' + s]), wr = wpos(c.bones['hand_' + s]);
  if (!sh || !el || !wr) return null;
  const a = sh.sub(el).normalize(), b = wr.sub(el).normalize();
  return 180 - T.MathUtils.radToDeg(Math.acos(T.MathUtils.clamp(a.dot(b), -1, 1)));
}
const arr = v => (v ? [v.x, v.y, v.z] : null);
function capsulesFor(c) {
  const b = n => wpos(c.bones[n]);
  const caps = [], add = (name, a, bb, r) => { if (a && bb) caps.push({name, a: arr(a), b: arr(bb), r}); };
  const head = b('head'), neck = b('neck'), pelvis = b('pelvis'), sp3 = b('spine_03');
  if (head) add('head', head, head.clone().add(new T.Vector3(0, .22, 0)), .12);
  if (pelvis && neck) add('torso', pelvis, neck, .17);
  else if (sp3) add('torso', sp3.clone().add(new T.Vector3(0, -.45, 0)), sp3, .16);
  for (const s of ['l', 'r']) {
    add('upperarm_' + s, b('upperarm_' + s), b('forearm_' + s), .065);
    add('forearm_' + s, b('forearm_' + s), b('hand_' + s), .055);
    add('thigh_' + s, b('thigh_' + s), b('calf_' + s), .085);
    add('calf_' + s, b('calf_' + s), b('foot_' + s), .065);
  }
  return caps;
}
function measureFrame(c) {
  const sw = c.sw;
  return {
    base: arr(wpos(sw.blade_base)), mid: arr(wpos(sw.blade_mid)), tip: arr(wpos(sw.blade_tip)),
    edge: sw.edge_true && sw.blade_mid ? arr(wpos(sw.edge_true).sub(wpos(sw.blade_mid)).normalize()) : null,
    grip_mm: sw.hand_secondary && c.bones[S.index.weapon?.off_hand_socket || 'grip_l'] ? wpos(sw.hand_secondary).distanceTo(wpos(c.bones[S.index.weapon?.off_hand_socket || 'grip_l'])) * 1000 : null,
    elbow_l: elbowFlex(c, 'l'), elbow_r: elbowFlex(c, 'r'),
    pelvis: arr(wpos(c.bones.pelvis || c.bones.spine_03)), foot_l: arr(wpos(c.bones.foot_l)), foot_r: arr(wpos(c.bones.foot_r)),
    caps: capsulesFor(c),
  };
}
function visibleChars() { return S.mode === 'both' ? ['william', 'aldren'] : [S.mode]; }
function timelineLength() { return Math.max(0, ...visibleChars().map(id => clipFrames(S.chars[id]))); }

function rebuildTimeline() {
  const n = timelineLength();
  const perChar = {};
  for (const id of visibleChars()) {
    const c = S.chars[id], list = [];
    for (let f = 0; f <= n; f++) { poseAt(c, f); list.push(measureFrame(c)); }
    perChar[id] = list;
  }
  // Contacts between the two swords and blade-vs-body, swept frame to frame (deterministic, shadow mode).
  const contacts = [], bodyHits = [];
  let telemetry = null;
  if (S.mode === 'both') {
    const W = perChar.william, A = perChar.aldren;
    const mW = meta(S.chars.william.clipName), mA = meta(S.chars.aldren.clipName);
    const attackerId = mW?.kind === 'attack' ? 'william' : 'aldren', defenderId = attackerId === 'william' ? 'aldren' : 'william';
    const att = perChar[attackerId], def = perChar[defenderId], mAtt = meta(S.chars[attackerId].clipName), mDef = meta(S.chars[defenderId].clipName);
    for (let f = 1; f <= n; f++) {
      const bl = o => ({base: o.base, tip: o.tip});
      const hit = sweptBladeContact(bl(W[f - 1]), bl(W[f]), bl(A[f - 1]), bl(A[f]), {dt: 1 / S.fps});
      if (hit) contacts.push({frame: f - 1 + hit.u, ...hit});
      const bh = sweptBladeBody(bl(att[f - 1]), bl(att[f]), def[f].caps);
      if (bh) bodyHits.push({frame: f - 1 + bh.u, ...bh});
    }
    // Shadow telemetry with the combat event an engine would emit at the authored contact frame.
    telemetry = new ContactTelemetry();
    const cf = mAtt?.kind === 'attack' ? mAtt.contact_frame : null;
    const evType = !mDef ? null : mDef.kind === 'parry' ? 'parry' : mDef.kind === 'deflect' ? 'clash' : (attackerId === 'william' ? 'enemyHit' : 'playerHit');
    for (let f = 0; f <= n; f++) {
      telemetry.ingest({t: f / S.fps, attacker: {blade: att[f], phase: phaseOf(mAtt, f), clip: S.chars[attackerId].clipName},
        defender: {blade: def[f], phase: phaseOf(mDef, f), body: def[f].caps},
        combatEvents: cf !== null && cf !== undefined && f === cf && evType ? [{type: evType, time: f / S.fps}] : []});
    }
    telemetry.finish();
    telemetry.meta = {attacker: attackerId, expected_event: cf != null ? `${evType} @ frame ${cf}` : 'none (no attack clip)'};
  }
  S.timeline = {n, perChar, contacts, bodyHits, telemetry};
  $('scrub').max = String(n); $('scrub').disabled = n === 0;
  drawTicks(); buildPathOverlays(); buildV03(); writeMetrics(); writeTelemetry();
  applyFrame(Math.min(S.frame, n));
}

function phaseOf(m, f) {
  if (!m?.phases) return null;
  let name = null;
  for (const [k, [a, b]] of Object.entries(m.phases)) if (f >= a && f <= b) name = k;
  return name;
}
function primaryChar() {
  if (S.mode !== 'both') return S.chars[S.mode];
  const w = S.chars.william, a = S.chars.aldren;
  return meta(a.clipName)?.kind === 'attack' || !meta(w.clipName) ? a : w;
}

// ---------- overlays ----------
const mats = {
  gold: new T.LineBasicMaterial({color: 0xe2c37a, depthTest: false, transparent: true}),
  goldDim: new T.LineBasicMaterial({color: 0xe2c37a, depthTest: false, transparent: true, opacity: .35}),
  cyan: new T.LineDashedMaterial({color: 0x6fd6e8, depthTest: false, transparent: true, dashSize: .02, gapSize: .015}),
  orange: new T.LineBasicMaterial({color: 0xf09040, depthTest: false, transparent: true}),
  orangeDim: new T.LineDashedMaterial({color: 0xf09040, depthTest: false, transparent: true, opacity: .6, dashSize: .03, gapSize: .02}),
  root: new T.LineBasicMaterial({color: 0xb07cff, depthTest: false, transparent: true}),
};
const sphere = (r, color) => new T.Mesh(new T.SphereGeometry(r, 14, 10), new T.MeshBasicMaterial({color, depthTest: false, transparent: true, opacity: .9}));
const groups = {path: new T.Group(), v03: new T.Group(), root: new T.Group(), contact: new T.Group(), hitbox: new T.Group(), feet: new T.Group(), sockets: new T.Group(), joints: new T.Group()};
for (const g of Object.values(groups)) { g.renderOrder = 10; overlayRoot.add(g); }
function line(points, mat, parent) {
  if (points.filter(Boolean).length < 2) return null;
  const g = new T.BufferGeometry().setFromPoints(points.filter(Boolean).map(p => new T.Vector3(...p)));
  const l = new T.Line(g, mat); if (mat.isLineDashedMaterial) l.computeLineDistances(); l.renderOrder = 10; parent.add(l); return l;
}
const toWorld = (c, p) => (p ? new T.Vector3(...p).applyMatrix4(c.holder.matrixWorld).toArray() : null);
function clear(g) { for (const ch of [...g.children]) { g.remove(ch); ch.geometry?.dispose?.(); } }

const live = {
  tipMarker: sphere(.022, 0xffffff), contractContact: sphere(.03, 0xe2c37a), measuredContact: sphere(.026, 0x6fd6e8),
  liveContacts: [], pelvis: sphere(.03, 0xb07cff), feet: [sphere(.035, 0x55dd77), sphere(.035, 0x55dd77)], v03Blade: null, capsules: [],
  joints: null, sockets: [],
};
groups.path.add(live.tipMarker); groups.contact.add(live.contractContact, live.measuredContact); groups.root.add(live.pelvis); groups.feet.add(...live.feet);

function buildPathOverlays() {
  for (const k of ['path', 'root']) { for (const ch of [...groups[k].children]) if (!Object.values(live).includes(ch) && ch !== live.tipMarker && ch !== live.pelvis) { groups[k].remove(ch); ch.geometry?.dispose?.(); } }
  for (const ch of [...groups.contact.children]) if (ch !== live.contractContact && ch !== live.measuredContact) groups.contact.remove(ch);
  const legend = [];
  for (const id of visibleChars()) {
    const c = S.chars[id], m = meta(c.clipName), M = S.timeline.perChar[id];
    if (m?.samples) {
      const s = m.samples;
      line(s.blade_tip.map(p => toWorld(c, p)), mats.gold, groups.path);
      line(s.blade_base.map(p => toWorld(c, p)), mats.goldDim, groups.path);
    }
    if (M.length > 1) line(M.map(x => x.tip), mats.cyan, groups.path);
    if (M.length > 1) line(M.map(x => x.pelvis), mats.root, groups.root);
  }
  // Every swept contact between the swords over the timeline (small red), shadow mode.
  for (const h of S.timeline.contacts) { const s = sphere(.014, 0xff4040); s.position.set(...h.point); groups.contact.add(s); }
  for (const h of S.timeline.bodyHits) { const s = sphere(.014, 0xff40c0); s.position.set(...h.point); groups.contact.add(s); }
  legend.push('<span class="c-gold">━ contract blade tip/base</span>', '<span class="c-cyan">┅ measured tip</span>');
  if (S.overlays.has('v03')) legend.push('<span class="c-orange">━ v0.3 grip/tip (approx.)</span>');
  if (S.overlays.has('contact')) legend.push('<span style="color:#e2c37a">● contract contact</span> <span style="color:#6fd6e8">● measured @contact</span> <span style="color:#f44">● sword×sword</span> <span style="color:#f4c">● blade×body</span>');
  if (S.overlays.has('root')) legend.push('<span style="color:#b07cff">━ pelvis trace</span>');
  $('legend').innerHTML = S.overlays.has('path') || S.overlays.has('contact') || S.overlays.has('v03') || S.overlays.has('root') ? legend.join('<br>') : '';
}

function v03Data(c) {
  const m = meta(c.clipName);
  const zone = m?.game_zone || (c.clipName?.includes('upper_left') ? 'upperLeft' : c.clipName?.includes('upper_right') ? 'upperRight' : 'head');
  const view = c.id === 'aldren' ? 'enemy' : 'player';
  const eye = c.id === 'william' && c.restEye ? c.restEye : [0, 1.675, .075];
  // enemy: grip in v0.3 'arms' group frame (knight-local offset (0, 1.40, 0.05), enemy faces +Z) -> Aldren glTF space.
  // player: grip in camera space (-Z forward) -> William glTF space (faces +Z): (x,y,z) -> eye + (-x, y, -z).
  const map = s => {
    if (view === 'enemy') return {g: [s.grip[0], s.grip[1] + 1.40, s.grip[2] + .05], a: s.axis};
    return {g: [eye[0] - s.grip[0], eye[1] + s.grip[1], eye[2] - s.grip[2]], a: [-s.axis[0], s.axis[1], -s.axis[2]]};
  };
  const at = p => { const {g, a} = map(sampleClip(view, zone, p)); return {grip: g, base: g.map((v, i) => v + a[i] * .15), tip: g.map((v, i) => v + a[i] * 1.07)}; };
  return {zone, view, at};
}
function buildV03() {
  clear(groups.v03); live.v03Blades = [];
  if (!S.overlays.has('v03')) return;
  for (const id of visibleChars()) {
    const c = S.chars[id], d = v03Data(c), grips = [], tips = [];
    for (let i = 0; i <= 60; i++) { const s = d.at(i / 60); grips.push(toWorld(c, s.grip)); tips.push(toWorld(c, s.tip)); }
    line(grips, mats.orange, groups.v03); line(tips, mats.orangeDim, groups.v03);
    const bl = line([[0, 0, 0], [0, 1, 0]], mats.orange, groups.v03); bl.userData = {c, d};
    (live.v03Blades ||= []).push(bl);
  }
}

function drawTicks() {
  const n = S.timeline.n, el = $('ticks'); el.replaceChildren();
  if (!n) return;
  for (const h of S.timeline.contacts) { const i = document.createElement('i'); i.style.left = (100 * h.frame / n) + '%'; el.append(i); }
  for (const id of visibleChars()) {
    const m = meta(S.chars[id].clipName), cf = m?.contact_frame ?? m?.expected_contact_frame;
    if (cf != null) { const i = document.createElement('i'); i.className = 'gold'; i.style.left = (100 * cf / n) + '%'; el.append(i); }
  }
}

function ensureSkeletons() {
  for (const c of Object.values(S.chars)) {
    const want2 = S.overlays.has('skeleton') && c.holder.visible;
    if (want2 && !c.skel) { c.skel = new T.SkeletonHelper(c.gltf.scene); c.skel.material.depthTest = false; c.skel.material.transparent = true; c.skel.material.opacity = .8; scene.add(c.skel); }
    if (!want2 && c.skel) { scene.remove(c.skel); c.skel.dispose?.(); c.skel = null; }
  }
}
function updateJoints() {
  if (!S.overlays.has('joints')) { groups.joints.visible = false; return; }
  const pts = [];
  for (const id of visibleChars()) S.chars[id].gltf.scene.traverse(o => { if (o.isBone) pts.push(wpos(o)); });
  if (!live.joints) {
    live.joints = new T.Points(new T.BufferGeometry(), new T.PointsMaterial({color: 0xffee66, size: 6, sizeAttenuation: false, depthTest: false, transparent: true}));
    live.joints.renderOrder = 11; groups.joints.add(live.joints);
  }
  live.joints.geometry.setFromPoints(pts); groups.joints.visible = true;
}
function updateSockets() {
  if (!S.overlays.has('sockets')) { groups.sockets.visible = false; return; }
  if (!live.sockets.length) {
    for (const id of ['aldren', 'william']) {
      const c = S.chars[id]; if (!c) continue;
      for (const n of [S.index.weapon?.socket || 'weapon_r', S.index.weapon?.off_hand_socket || 'grip_l']) {
        const ax = new T.AxesHelper(.09); ax.material.depthTest = false; ax.renderOrder = 12; ax.userData = {c, bone: c.bones[n]}; groups.sockets.add(ax); live.sockets.push(ax);
      }
      for (const [n, col] of [['hand_primary', 0xffd040], ['hand_secondary', 0x40e0ff], ['blade_tip', 0xff5050], ['edge_true', 0x50ff80]]) {
        const s = sphere(.012, col); s.userData = {c, node: c.sw[n]}; groups.sockets.add(s); live.sockets.push(s);
      }
    }
  }
  for (const o of live.sockets) {
    const vis = o.userData.c.holder.visible; o.visible = vis; if (!vis) continue;
    if (o.userData.bone) { o.userData.bone.matrixWorld.decompose(o.position, o.quaternion, tmpV2); }
    else if (o.userData.node) wpos(o.userData.node, o.position);
  }
  groups.sockets.visible = true;
}
function updateCapsules(f) {
  for (const m of live.capsules) { groups.hitbox.remove(m); m.geometry.dispose(); }
  live.capsules = [];
  if (!S.overlays.has('hitbox')) return;
  // Opponent = the defender in 'both' mode, otherwise the shown character's own capsules.
  let id = S.mode;
  if (S.mode === 'both') id = primaryChar().id === 'aldren' ? 'william' : 'aldren';
  const caps = S.timeline.perChar[id]?.[f]?.caps || [];
  const hitNames = new Set(S.timeline.bodyHits.filter(h => Math.abs(h.frame - f) < 1.5).map(h => h.name));
  for (const cp of caps) {
    const a = new T.Vector3(...cp.a), b = new T.Vector3(...cp.b), L = a.distanceTo(b);
    const m = new T.Mesh(new T.CapsuleGeometry(cp.r, Math.max(.001, L), 4, 10),
      new T.MeshBasicMaterial({color: hitNames.has(cp.name) ? 0xff3050 : 0x50c8ff, wireframe: true, transparent: true, opacity: .45, depthTest: false}));
    m.position.copy(a).lerp(b, .5); if (L > 1e-4) m.quaternion.setFromUnitVectors(new T.Vector3(0, 1, 0), b.clone().sub(a).normalize());
    m.renderOrder = 9; groups.hitbox.add(m); live.capsules.push(m);
  }
}

// ---------- frame application + readouts ----------
function sampleIndex(m, f) {
  const fr = m?.samples?.frames; if (!fr) return -1;
  let i = 0; while (i < fr.length - 1 && fr[i + 1] <= f) i++; return i;
}
const fmt = (v, d = 1) => (v == null || !Number.isFinite(v) ? '—' : v.toFixed(d));
function applyFrame(f) {
  S.frame = f;
  const fi = Math.round(f);
  for (const id of visibleChars()) poseAt(S.chars[id], f);
  const c = primaryChar(), m = meta(c.clipName), M = S.timeline.perChar[c.id], cur = M[Math.min(fi, M.length - 1)];
  const lf = Math.round(localFrame(c, f));
  const ph = phaseOf(m, lf);
  $('scrub').value = String(fi); $('frameOut').textContent = m ? `${lf} / ${m.frame_end}` : 'static';
  $('phaseOut').textContent = ph || '—'; $('phaseOut').style.color = PHASE_COLORS[ph] || '';
  $('rPhase').textContent = (ph || '—') + (m ? ` · ${c.clipName}` : '');
  $('rFrame').textContent = m ? `${lf} / ${m.frame_end} (${(lf / S.fps).toFixed(2)} s)` : 'rest pose (no clip)';
  // Tip speed from contract samples, and measured from the attached sword.
  let spS = null, grS = null, elS = null, camAdv = null;
  const si = sampleIndex(m, lf);
  if (si >= 0) {
    const s = m.samples, j = Math.min(si + 1, s.frames.length - 1), k = j === si ? si - 1 : si;
    if (k >= 0 && j !== k) { const dt = (s.frames[j] - s.frames[k]) / S.fps; spS = Math.hypot(...s.blade_tip[j].map((v, q) => v - s.blade_tip[k][q])) / dt; }
    grS = s.grip_error_mm?.[si]; elS = [s.elbow_deg_l?.[si], s.elbow_deg_r?.[si]];
    camAdv = m.camera_advance_m?.[si] ?? null;
  }
  const prevM = M[Math.max(0, fi - 1)], nextM = M[Math.min(M.length - 1, fi + 1)];
  const spM = M.length > 1 ? Math.hypot(...nextM.tip.map((v, q) => v - prevM.tip[q])) / ((Math.min(M.length - 1, fi + 1) - Math.max(0, fi - 1)) / S.fps || 1) : null;
  $('rSpeed').textContent = `${fmt(spS, 2)} m/s contract · ${fmt(spM, 2)} measured`;
  $('rGrip').textContent = `${fmt(grS)} mm contract · ${fmt(cur?.grip_mm)} mm measured`;
  $('rElbow').textContent = `${elS ? fmt(elS[0], 0) + '/' + fmt(elS[1], 0) : '—'}° contract · ${fmt(cur?.elbow_l, 0)}/${fmt(cur?.elbow_r, 0)}° measured`;
  const cf = m?.contact_frame ?? m?.expected_contact_frame ?? null;
  const near = S.timeline.contacts.find(h => Math.abs(h.frame - f) < 1.01);
  let ctext = cf != null ? `${m.contact_frame != null ? 'contact' : 'expected impact'} @ ${cf}` + (m.contact_normalized != null ? ` (${m.contact_normalized.toFixed(2)})` : '') : 'no contact frame';
  if (S.mode === 'both') ctext += ` · live: ${near ? `HIT ${fmt(near.rel_speed, 1)} m/s` : 'apart'}`;
  if (camAdv != null) ctext += ` · cam advance ${fmt(camAdv, 3)} m (readout only)`;
  $('rContact').textContent = ctext;

  // live markers
  live.tipMarker.visible = !!cur?.tip; if (cur?.tip) live.tipMarker.position.set(...cur.tip);
  if (cf != null && m?.samples) {
    const ci = sampleIndex(m, cf);
    live.contractContact.visible = ci >= 0; if (ci >= 0) live.contractContact.position.set(...toWorld(c, m.samples.blade_tip[ci]));
    const mc = M[Math.min(cf, M.length - 1)]; live.measuredContact.visible = !!mc; if (mc) live.measuredContact.position.set(...mc.tip);
    const s = Math.abs(lf - cf) <= 1 ? 1.8 : 1; live.contractContact.scale.setScalar(s);
  } else { live.contractContact.visible = live.measuredContact.visible = false; }
  for (const s of live.liveContacts) groups.contact.remove(s);
  live.liveContacts = [];
  if (near) { const s = sphere(.04, 0xff2020); s.position.set(...near.point); groups.contact.add(s); live.liveContacts.push(s); }
  if (cur?.pelvis) live.pelvis.position.set(...cur.pelvis);
  // feet: green when planted (sample foot height < 0.03 m), orange when lifted; position = foot bone head (ankle).
  ['foot_l', 'foot_r'].forEach((k, i) => {
    const p = cur?.[k]; live.feet[i].visible = !!p; if (!p) return;
    live.feet[i].position.set(...p);
    const sh = si >= 0 && m.samples[k] ? m.samples[k][si][1] : null;
    live.feet[i].material.color.set(sh == null ? 0x99aaaa : sh < .03 ? 0x55dd77 : 0xff9944);
  });
  for (const bl of live.v03Blades || []) {
    if (!bl.parent) continue;
    const {c: cc, d} = bl.userData, mm = meta(cc.clipName);
    const p = mm ? Math.min(1, Math.max(0, localFrame(cc, f) / mm.frame_end)) : 0, s = d.at(p);
    bl.geometry.setFromPoints([new T.Vector3(...toWorld(cc, s.base)), new T.Vector3(...toWorld(cc, s.tip))]);
  }
  updateCapsules(fi); updateJoints(); updateSockets(); applyCamera(false);
}

function writeMetrics() {
  const out = [];
  for (const id of visibleChars()) {
    const c = S.chars[id], m = meta(c.clipName), M = S.timeline.perChar[id];
    out.push(`[${id}] ${c.clipName || 'rest pose'}  model=${c.cfg.model.split('/').pop()}`);
    const g = M.map(x => x.grip_mm).filter(Number.isFinite);
    out.push(`  measured left-hand grip (sword hand_secondary ↔ ${S.index.weapon?.off_hand_socket || 'grip_l'}): max ${fmt(Math.max(...g))} mm, frame0 ${fmt(g[0])} mm`);
    if (m?.samples) {
      let worst = 0;
      for (let i = 0; i < m.samples.frames.length; i++) {
        const f = m.samples.frames[i], mm = M[Math.min(f, M.length - 1)];
        worst = Math.max(worst, new T.Vector3(...toWorld(c, m.samples.blade_tip[i])).distanceTo(new T.Vector3(...mm.tip)));
      }
      out.push(`  contract vs measured blade tip: max ${fmt(worst * 1000)} mm`);
      out.push(`  contract grip error max ${fmt(Math.max(...m.samples.grip_error_mm))} mm; root ${m.root_motion?.mode || '?'} net ${JSON.stringify(m.root_motion?.net_displacement_m || null)}`);
    } else if (!S.clipsAvailable) out.push('  clips not yet available — static rest pose');
    if (c.clipName && !c.action) out.push(`  WARNING: animation '${c.clipName}' not found in ${c.cfg.clips_glb}`);
    if (c.clipsError) out.push('  clips GLB error: ' + c.clipsError);
  }
  if (S.mode === 'both') {
    const W = S.timeline.perChar.william, A = S.timeline.perChar.aldren;
    let minSep = Infinity, at = 0;
    for (let f = 0; f < W.length; f++) { const d = segmentSegmentClosest(W[f].base, W[f].tip, A[f].base, A[f].tip).dist; if (d < minSep) { minSep = d; at = f; } }
    out.push(`[pair] distance ${S.dist.toFixed(2)} m; min sword separation ${fmt(minSep * 1000)} mm @ frame ${at}; sword×sword contacts ${S.timeline.contacts.length}; blade×body ${S.timeline.bodyHits.length}`);
  }
  $('metrics').textContent = out.join('\n');
}
function writeTelemetry() {
  const t = S.timeline.telemetry;
  $('shadowTag').hidden = S.mode !== 'both';
  if (!t) { $('telemetry').textContent = 'Show both characters to run shadow-mode contact telemetry (animation-contact.js).'; return; }
  $('telemetry').textContent = `attacker: ${t.meta.attacker}; synthesized engine event: ${t.meta.expected_event}\n` + JSON.stringify(t.summary(), null, 1) +
    '\n' + t.mismatches.map(m => `${(m.t * S.fps).toFixed(1)}f ${m.category} ${m.timing ? m.timing + ' ' + m.delta_ms + 'ms' : ''}${m.part ? ' part=' + m.part : ''}${m.min_separation_m != null ? ' sep=' + (m.min_separation_m * 1000).toFixed(0) + 'mm' : ''}`).join('\n');
}

// ---------- cameras ----------
const eyeFix = new T.Matrix4().makeRotationX(Math.PI / 2); // bone +Y forward/+Z up -> camera -Z forward/+Y up
function centerOf() {
  if (S.mode === 'both') return new T.Vector3(0, 1.25, S.dist / 2);
  return S.mode === 'william' ? new T.Vector3(0, 1.35, .3) : new T.Vector3(0, 1.1, 0);
}
function applyCamera(reset) {
  const cam = S.cam, ctr = centerOf();
  $('portraitGuide').hidden = cam !== 'fp';
  orbit.enabled = cam === 'orbit';
  if (cam === 'orbit') { if (reset) { orbit.target.copy(ctr); camera.position.copy(ctr).add(new T.Vector3(2.2, .7, S.mode === 'both' ? -1.2 : 2.6)); camera.fov = 45; camera.updateProjectionMatrix(); orbit.update(); } return; }
  camera.up.set(0, 1, 0);
  if (cam === 'fp') {
    const vm = S.guards?.viewmodel_camera || {back_m: .2, up_m: .02, pitch_down_deg: 12, fov_y_deg: 61};
    const w = S.chars.william;
    let eyeW;
    if (w && w.holder.visible && w.bones.fp_eye) eyeW = w.bones.fp_eye.matrixWorld.clone();
    else { // Aldren alone: virtual William eye at the engagement distance, facing -Z toward him.
      const restEye = w?.restEye || [0, 1.675, .075];
      // bone frame facing -Z: +Y forward = -Z world, +Z up = +Y world  ->  Rx(-90deg)
      eyeW = new T.Matrix4().makeTranslation(0, restEye[1], S.dist).multiply(new T.Matrix4().makeRotationX(-Math.PI / 2));
    }
    const m = eyeW.multiply(eyeFix).multiply(new T.Matrix4().makeTranslation(0, vm.up_m, vm.back_m)).multiply(new T.Matrix4().makeRotationX(-T.MathUtils.degToRad(vm.pitch_down_deg)));
    m.decompose(camera.position, camera.quaternion, tmpV);
    camera.fov = vm.fov_y_deg; camera.updateProjectionMatrix(); return;
  }
  camera.fov = 40;
  // Fit a width x height box (metres) for the current aspect, so portrait screens keep both fighters in frame.
  const fit = (w, h) => { const vt = Math.tan(T.MathUtils.degToRad(camera.fov / 2)), ht = vt * camera.aspect; return Math.max(h / 2 / vt, w / 2 / ht) * 1.08; };
  const both = S.mode === 'both';
  if (cam === 'side') { const d = fit(both ? S.dist + 1.9 : 1.9, 2.15); camera.position.set(ctr.x + d, ctr.y + .1, ctr.z); }
  else if (cam === 'front') { const d = fit(1.5, 2.15); camera.position.set(0, 1.25, both ? S.dist - d : d); }
  else if (cam === 'combat') camera.position.set(.55, 1.9, both ? -Math.max(1.0, fit(1.6, 1.6) - S.dist) : 3.0);
  camera.lookAt(cam === 'combat' && both ? new T.Vector3(0, 1.2, S.dist * .8) : new T.Vector3(ctr.x, cam === 'combat' ? ctr.y : 1.07, cam === 'front' && both ? S.dist : ctr.z));
  camera.updateProjectionMatrix();
}

// ---------- UI wiring ----------
function placeCharacters() {
  const w = S.chars.william, a = S.chars.aldren;
  a.holder.visible = S.mode !== 'william'; w.holder.visible = S.mode !== 'aldren';
  a.sword.visible = a.holder.visible; w.sword.visible = w.holder.visible;
  a.holder.position.set(0, 0, S.mode === 'both' ? S.dist : 0); a.holder.rotation.y = S.mode === 'both' ? Math.PI : 0;
  w.holder.position.set(0, 0, 0); w.holder.rotation.y = 0;
  for (const c of [a, w]) { c.holder.updateMatrixWorld(true); for (const ms of c.meshes) ms.visible = S.overlays.has('mesh'); }
  $('distRow').hidden = S.mode !== 'both'; $('clip2Row').hidden = S.mode !== 'both';
  $('title').textContent = S.mode === 'both' ? `William vs Ser Aldren · ${S.dist.toFixed(2)} m` : S.mode === 'aldren' ? 'Ser Aldren' : 'William — first-person arms';
}
function clipsFor(id) { return Object.entries(S.index.clips || {}).filter(([, m]) => m.character === id).map(([n]) => n); }
function fillSelect(sel, names, value) {
  sel.replaceChildren();
  if (!names.length) { const o = document.createElement('option'); o.value = ''; o.textContent = S.clipsAvailable ? '(no clips for this character)' : 'clips not yet available — rest pose'; sel.append(o); sel.disabled = true; return ''; }
  sel.disabled = false;
  for (const n of names) { const o = document.createElement('option'); o.value = n; o.textContent = n + (meta(n)?.loop ? ' (loop)' : ''); sel.append(o); }
  sel.value = names.includes(value) ? value : names[0]; return sel.value;
}
function counterpart(name, otherId) {
  const m = meta(name); const names = clipsFor(otherId);
  if (!m) return names[0] || '';
  const zone = name.split('_').slice(2).join('_');
  const pick = m.kind === 'attack' ? [`${otherId}_parry_${zone}`, `${otherId}_parry_head`, `${otherId}_idle_ready`] : [`${otherId}_idle_ready`];
  return pick.find(n => names.includes(n)) || names[0] || '';
}
function chooseClips(primary, secondary) {
  const mode = S.mode;
  if (mode !== 'both') { const v = fillSelect($('clip'), clipsFor(mode), primary); setClip(S.chars[mode], v); return; }
  const all = [...clipsFor('aldren'), ...clipsFor('william')];
  const v = fillSelect($('clip'), all, primary);
  const pid = meta(v)?.character || 'aldren', oid = pid === 'aldren' ? 'william' : 'aldren';
  const v2 = fillSelect($('clip2'), clipsFor(oid), secondary || counterpart(v, oid));
  setClip(S.chars[pid], v); setClip(S.chars[oid], v2);
}
function refresh(resetCam = false) {
  placeCharacters(); ensureSkeletons(); rebuildTimeline();
  for (const [k, g] of Object.entries(groups)) if (!['sockets', 'joints'].includes(k)) g.visible = S.overlays.has(k);
  groups.path.visible = S.overlays.has('path'); groups.contact.visible = S.overlays.has('contact');
  applyCamera(resetCam);
}
function setPressed(btn, on) { btn.setAttribute('aria-pressed', String(on)); }
function syncButtons() {
  for (const b of $('cams').children) setPressed(b, b.dataset.cam === S.cam);
  for (const b of $('overlays').children) setPressed(b, S.overlays.has(b.dataset.ov));
  setPressed($('play'), S.playing); $('play').textContent = S.playing ? 'Pause' : 'Play';
  setPressed($('loop'), S.loop); $('loop').textContent = 'Loop: ' + (S.loop ? 'On' : 'Off');
}
function wire() {
  $('char').onchange = () => { S.mode = $('char').value; chooseClips(null, null); refresh(true); syncButtons(); };
  $('clip').onchange = () => { chooseClips($('clip').value, null); S.frame = 0; refresh(); };
  $('clip2').onchange = () => { chooseClips($('clip').value, $('clip2').value); refresh(); };
  $('dist').oninput = () => { S.dist = Number($('dist').value); $('distOut').textContent = S.dist.toFixed(2) + ' m'; refresh(); };
  $('play').onclick = () => { S.playing = !S.playing; if (S.playing && S.frame >= S.timeline.n) S.frame = 0; syncButtons(); };
  $('restart').onclick = () => { S.frame = 0; applyFrame(0); };
  $('loop').onclick = () => { S.loop = !S.loop; syncButtons(); };
  $('speed').onchange = () => { S.speed = Number($('speed').value); };
  $('scrub').oninput = () => { S.playing = false; syncButtons(); applyFrame(Number($('scrub').value)); };
  for (const b of $('cams').children) b.onclick = () => { S.cam = b.dataset.cam; syncButtons(); applyCamera(true); };
  for (const b of $('overlays').children) b.onclick = () => {
    const k = b.dataset.ov; S.overlays.has(k) ? S.overlays.delete(k) : S.overlays.add(k); syncButtons(); refresh();
  };
}

function resize() {
  const w = Math.max(1, host.clientWidth), h = Math.max(1, host.clientHeight);
  renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(host); resize();

let last = performance.now();
function tick(now) {
  const dt = Math.min(.1, (now - last) / 1000); last = now;
  if (S.ready && S.playing && S.timeline?.n) {
    let f = S.frame + dt * S.fps * S.speed;
    if (f > S.timeline.n) { if (S.loop) f = f % S.timeline.n; else { f = S.timeline.n; S.playing = false; syncButtons(); } }
    applyFrame(f);
  }
  if (S.cam === 'orbit') orbit.update();
  renderer.render(scene, camera);
}

// ---------- perf ----------
function runPerf(N) {
  const gl = renderer.getContext(), mix = [], ren = [], attach = [];
  const chars = visibleChars().map(id => S.chars[id]);
  for (let i = 0; i < N; i++) {
    const t0 = performance.now();
    for (const c of chars) c.mixer.update(1 / S.fps);
    const t1 = performance.now();
    for (const c of chars) { c.holder.updateMatrixWorld(true); attachSword(c); }
    const t2 = performance.now();
    renderer.render(scene, camera); gl.finish();
    const t3 = performance.now();
    mix.push(t1 - t0); attach.push(t2 - t1); ren.push(t3 - t2);
  }
  const st = a => { const s = [...a].sort((x, y) => x - y); return {avg: +(a.reduce((x, y) => x + y, 0) / a.length).toFixed(3), p95: +s[Math.floor(s.length * .95)].toFixed(3), max: +s[s.length - 1].toFixed(3)}; };
  const info = renderer.info.render;
  const result = {frames: N, mode: S.mode, clip: chars.map(c => c.clipName), mixer_update_ms: st(mix), attach_ms: st(attach), render_ms: st(ren),
    draw_calls: info.calls, triangles: info.triangles, renderer: (gl.getExtension('WEBGL_debug_renderer_info') ? gl.getParameter(gl.getExtension('WEBGL_debug_renderer_info').UNMASKED_RENDERER_WEBGL) : 'unknown'),
    viewport: [renderer.domElement.width, renderer.domElement.height], note: 'render_ms includes gl.finish(); headless swiftshader numbers are CPU rasterizer times, not device GPU times'};
  console.log('LAB_PERF ' + JSON.stringify(result));
  $('perfOut').textContent = JSON.stringify(result); $('perfOut').hidden = false;
  document.title += ` [perf mixer=${result.mixer_update_ms.avg}ms render=${result.render_ms.avg}ms]`;
  return result;
}

// ---------- synthetic in-memory clips (?synthetic=1, only when the real index is absent) ----------
// Exercises mixer binding by bone name, timeline, overlays, contact and telemetry. Not authored animation.
function syntheticIndex() {
  const idx = JSON.parse(JSON.stringify(FALLBACK)); idx.version = 'synthetic';
  const atk = ch => ({character: ch, animation: `${ch}_attack_head`, game_zone: 'head', kind: 'attack', loop: false, frame_start: 0, frame_end: 30,
    duration_s: 1, contact_frame: 20, contact_normalized: 20 / 30, phases: {windup: [0, 12], attack: [12, 20], follow_through: [20, 25], recovery: [25, 30]}});
  const par = ch => ({character: ch, animation: `${ch}_parry_head`, game_zone: 'head', kind: 'parry', loop: false, frame_start: 0, frame_end: 30,
    duration_s: 1, contact_frame: null, expected_contact_frame: 18, phases: {raise: [0, 14], hold: [14, 24], recover: [24, 30]}});
  idx.clips = {aldren_attack_head: atk('aldren'), aldren_parry_head: par('aldren'), william_attack_head: atk('william'), william_parry_head: par('william')};
  return idx;
}
function syntheticClips(c) {
  const out = {}, q = new T.Quaternion(), e = new T.Euler();
  const track = (bone, keys) => {
    const b = c.bones[bone]; if (!b) return null;
    const times = [], values = [];
    for (const [t, x, z] of keys) { q.copy(b.quaternion).multiply(new T.Quaternion().setFromEuler(e.set(x, 0, z))); times.push(t); values.push(q.x, q.y, q.z, q.w); }
    return new T.QuaternionKeyframeTrack(`${bone}.quaternion`, times, values);
  };
  const make = (name, up, fore) => {
    const tracks = [];
    for (const s of ['l', 'r']) {
      tracks.push(track('upperarm_' + s, up.map(([t, a]) => [t, a, 0])), track('forearm_' + s, fore.map(([t, a]) => [t, a, 0])));
    }
    out[name] = new T.AnimationClip(name, 1, tracks.filter(Boolean));
  };
  make(`${c.id}_attack_head`, [[0, 0], [.4, 1.6], [.67, .9], [1, 0]], [[0, 0], [.4, .9], [.67, .2], [1, 0]]);
  make(`${c.id}_parry_head`, [[0, 0], [.47, 1.4], [.8, 1.4], [1, 0]], [[0, 0], [.47, .6], [.8, .6], [1, 0]]);
  return out;
}

// ---------- boot ----------
async function boot() {
  status('Loading clips index…');
  try {
    const r = await fetch(INDEX_URL, {cache: 'no-store'});
    if (!r.ok) throw new Error('HTTP ' + r.status);
    S.index = await r.json(); S.clipsAvailable = true;
  } catch (e) {
    S.index = FALLBACK; S.clipsAvailable = false;
  }
  S.synthetic = !S.clipsAvailable && P.get('synthetic') === '1';
  if (S.synthetic) S.index = syntheticIndex();
  S.fps = S.index.fps || 30;
  const eng = S.index.engagement || FALLBACK.engagement;
  S.dist = Number.isFinite(want.dist) && want.dist > 0 ? want.dist : eng.guard_distance_m;
  $('dist').value = String(S.dist); $('distOut').textContent = S.dist.toFixed(2) + ' m';
  try { S.guards = await (await fetch(GUARDS_URL)).json(); } catch { S.guards = null; }
  status('Loading models…');
  const swordGltf = await loadGLB(ROOT + (S.index.weapon?.model || FALLBACK.weapon.model));
  const chars = S.index.characters || FALLBACK.characters;
  const [aldren, william] = await Promise.all([loadCharacter('aldren', chars.aldren, swordGltf.scene), loadCharacter('william', chars.william, swordGltf.scene)]);
  S.chars = {aldren, william};
  if (S.synthetic) for (const c of [aldren, william]) Object.assign(c.clips, syntheticClips(c));
  william.holder.updateMatrixWorld(true);
  if (william.bones.fp_eye) william.restEye = wpos(william.bones.fp_eye).toArray();

  // apply requested state
  S.mode = ['aldren', 'william', 'both'].includes(want.char) ? want.char : (want.clip && meta(want.clip)?.character) || 'aldren';
  $('char').value = S.mode;
  S.cam = ['orbit', 'fp', 'side', 'front', 'combat'].includes(want.cam) ? want.cam : 'orbit';
  if (want.overlays) S.overlays = new Set(want.overlays.map(o => (o === 'nomesh' ? null : o)).filter(Boolean).concat(want.overlays.includes('nomesh') ? [] : ['mesh']));
  if (want.overlays?.includes('nomesh')) S.overlays.delete('mesh');
  chooseClips(want.clip, want.clip2);
  S.frame = 0; S.playing = !want.paused && !want.perf && (S.clipsAvailable || S.synthetic);
  wire(); syncButtons(); refresh(true);
  if (want.frame != null && Number.isFinite(want.frame)) applyFrame(Math.max(0, Math.min(want.frame, S.timeline.n)));
  const nClips = Object.values(S.chars).reduce((s, c) => s + Object.keys(c.clips).length, 0);
  if (S.synthetic) status('SYNTHETIC TEST CLIPS (in-memory, ?synthetic=1) — pipeline check only, not authored animation.');
  else status(S.clipsAvailable ? `Clips index ${S.index.version || ''} · ${Object.keys(S.index.clips || {}).length} clips · ${nClips} animations loaded`
    : 'Clips not yet available (clips_index_v003.json missing) — static models in rest pose.');
  S.ready = true;
  renderer.setAnimationLoop(tick);
  // Render the requested state synchronously (rAF does not fire in every headless mode, e.g. --dump-dom).
  resize(); applyCamera(false); renderer.render(scene, camera);
  await new Promise(r => setTimeout(r, 30));
  if (want.perf) runPerf(Math.max(10, want.perfFrames));
  window.__labReady = true; window.__lab = S;
  document.title += ' [ready]';
}
boot().catch(e => { console.error(e); status('Lab failed: ' + (e.message || e)); document.title += ' [error]'; window.__labError = String(e.message || e); });
