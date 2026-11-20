# v0.4.0 Phase C/D: "The Art of Swordsmanship" — fencing animation, rigs, contact layer, animation lab

Status 2026-11-20, branch `development/v040-forged-in-reality`. **The game is unchanged.** No game module imports any of this work, and `main` and the stable site are untouched. All motion is **original hand-authored keyframing**, inspired by German longsword technique (Pflug, vom Tag, Oberhau, roof/hanging parry); nothing is motion capture.

## 1. Rig audit and corrective changes (C.1)
Audit tool: `tools/blender/audit_rig.py`. Reports: `docs/asset-pipeline/rig_audit_knight_v006.json`, `rig_audit_arms_v004.json`, `rig_audit_knight_v007.json`. Range-of-motion renders: `previews/v0.4.0/rig_audit/`.

| Finding | Evidence | Fix |
|---|---|---|
| Skin weights are healthy: at most 4 influences per vertex (the glTF limit), none unweighted, all sums equal 1 | audit JSON | none needed |
| Pauldrons slid off the shoulder in overhead poses (55% clavicle / 45% upper-arm weighting) | `knight_v006_vom_tag_high_a.png` | **Ser Aldren v007**: shoulder cap 25/75, first lame 10/90, so the plate rides with the arm |
| The doublet tore out at the armpit when the arm lifted | `knight_v006_diag_windup_right_b.png` | **v007**: torso underlayer no longer weighted to arm bones |
| Gauntlet cuffs swung away from the vambrace on wrist bend ("cups") | pilot render `aldren_v006/stills/..._contact` | **v008**: cuff shared between hand and forearm-twist, graded along the forearm |
| Twist bones were never driven, so all pronation landed at the wrist (candy-wrapper) | audit wrist twist | the animation engine drives `forearm_twist_*` at 60% of wrist roll; residual is in the clip QA |
| Some two-hand placements are out of reach, because clavicles aren't in the IK chain | audit grip errors of 51–134 mm | the engine animates clavicle lift and protraction and runs a temporally smoothed reach solver; every frame is checked |

The bone hierarchy, names, sockets and hinge limits (elbow 0–150°, knee −150–0°) are unchanged from v006, so v007 and v008 are drop-in replacements with the same skeleton. The current knight is **`ser_aldren_v008.glb`**.

## 2. First-person overhead parry redesign (C.2)
Tool: `tools/blender/fp_parry_search.py`. Output: `assets/v0.4.0/first-person/william_fp_guards_v005.json`. Mesh and rig are unchanged from arms v004, and the viewmodel camera is unchanged (0.20 m back, 0.02 m up, 12° down, 61° vertical FOV).

| Metric (same scorer for both) | v004 head parry | **v005 head parry** |
|---|---|---|
| Opponent hidden by the arms | 26.9% | **0.0%** |
| Blade visible on screen | 24% | 62% |
| Hands on grip (left wrist error) | 1.1 mm | 0.0 mm |
| Parry geometry (blade crosses the centre line above the eye, 0.15–0.75 m out, at least 0.25 m to the left, within 30° of level, true edge up) | **fails**: crossed 9 cm *below* the eye | passes: +8 cm above, 0.40 m out, 0.53 m left, 8° |

- **Lower-right regression check:** re-measured from its v004 pose at 8.1%, unchanged.
- **Renders:** `previews/v0.4.0/william_fp_arms_v005_pov_head_5.png` and `_compare_head_5_v004_vs_v005.png` (side by side), plus `_inspect_head_5.png`.

## 3. Clips (C.3–C.6, C.8)
- **Authoring:** `tools/blender/build_animations.py` (keys) and `tools/blender/wos_anim.py` (engine).
- **Engine.** Each key sets posture (pelvis, spine, clavicles, head), footwork and the sword's hilt, blade and edge.
  - Both hands are solved by the rig's own IK onto one sword frame, so the grip can't separate.
  - Feet interpolate exactly between keys with a lift arc, so planted feet can't slide.
  - Timing uses one C1-continuous monotone curve per clip, so there is no stutter at keys.
  - Results are baked to plain bone rotations and constraints are muted for export.

**Current exports.** These contain the skeleton and animations only:
- **`assets/v0.4.0/animations/aldren_clips_v009.glb`** (232 KB)
- **`william_clips_v005.glb`** (208 KB)
- index: **`clips_index_v003.json`**

Earlier versions are kept on disk and superseded:
- **Ser Aldren clips v001–v006:** reach, elbow-fold, speed-stutter and pop fixes. Each round was found by the per-frame QA.
- **v007–v008:** v008 fixed GLB keyframe times, which had been written at Blender's default 24 fps; a test now covers this.
- **v009:** the overhead contact was raised to helmet-top height so it lands on the parry exactly at the planned frame. It had been landing one frame early.
- **William clips v001–v004:** same kinds of fixes. **v005** applied the matching overhead contact change.

The table below is for v008/v004. In v009/v005 only the two overhead attacks changed. Their grip, elbow and drift QA is unchanged, and the overhead elbow range is now 21–145°.

| Clip | Frames (s) | Contact | Grip err max (mm) | Elbow range (°) | Peak tip speed (m/s) | Planted-foot drift (mm) | Max reach corr. (mm) |
|---|---|---|---|---|---|---|---|
| aldren_idle_ready | 90 (3.0, loop) | – | 0.04 | 81–96 | 0.0 | 0.01 | 0 |
| aldren_attack_head | 44 (1.47) | f24 (0.545) | 0.09 | 40–145 | 22.9 | 1.67 | 55 |
| aldren_attack_upper_left | 44 (1.47) | f24 (0.545) | 0.07 | 36–144 | 18.5 | 1.19 | 12 |
| aldren_attack_upper_right | 44 (1.47) | f24 (0.545) | 0.09 | 16–144 | 18.7 | 3.42 | 37 |
| aldren_parry_head | 30 (1.0) | impact f9 | 0.07 | 49–119 | 8.1 | 0.01 | 0 |
| aldren_deflect_head | 20 (0.67) | impact f0 | 0.05 | 49–108 | 2.8 | 0.01 | 0 |
| william_idle_ready | 90 (3.0, loop) | – | 0.03 | 23–73 | ~0 | n/a | 0 |
| william_attack_head | 44 (1.47) | f24 (0.545) | 0.04 | 14–94 | 17.4 | n/a | 20 |
| william_attack_upper_left | 44 (1.47) | f24 (0.545) | 1.05 | 8–91 | 16.3 | n/a | 77 |
| william_attack_upper_right | 44 (1.47) | f24 (0.545) | 0.04 | 16–104 | 16.0 | n/a | 79 |
| william_parry_head | 28 (0.93) | impact f8 | 0.03 | 26–83 | 7.2 | n/a | 0 |
| william_deflect_head | 20 (0.67) | impact f0 | 0.04 | 42–93 | 2.6 | n/a | 0 |

**Phases (attacks):** prepare 0–5, windup 5–18, attack 18–24, follow-through 24–34, recovery 34–44.
- **Parry phases:** raise, hold, recover.
- **Deflect phases:** impact, absorb, settle.
- **Each index entry also includes:** per-frame blade base, mid and tip, true-edge direction, grip error, elbow angles, residual wrist twist, feet and pelvis positions (knight), reach correction, and William's suggested `camera_advance_m` curve.

**Footwork (knight attacks).**
- The lead foot steps 0.20 m and lands with the blow, and the rear foot follows.
- Recovery retreats rear foot first, then lead foot.
- **Root motion:** in place. The motion comes from the pelvis, the root bone doesn't move, and net displacement is 0.

**Engagement distance (derived from the clips, recorded in the index).**
- Guard distance: 1.65 m.
- Contact distance: about 1.45 m after the 0.20 m step.
- At contact, the blade's percussion point lands 1.52 m out at head height (overhead) and about 1.44 m out at shoulder height (diagonals).
- The v0.3 scene's 2.3–3.25 m spacing cannot be reached by any realistic cut.

## 4. Integration conventions (for Three.js)
- **Units and axes:** metres; glTF Y-up; characters face +Z. Clips bind to the model by bone name, applied with `AnimationMixer` on the model scene.
- **Sword attachment:** `weapon_r` bone, local +Y = blade direction, local +Z = true edge, sword `hand_primary` at the bone head. The off hand should match `grip_l` against the sword's `hand_secondary`, which it does within the grip errors above.
- **Timing:** contact sits at `contact_normalized` (0.545), not the v0.3 value of 0.72.
  - Map the engine's windup interval (start → `e.until`) onto frames 0 → `contact_frame`.
  - Map the recovery interval onto `contact_frame` → `frame_end`.
  - This is a two-segment time warp, the same structure as `motion.js#timelineTime`, with the contact constant taken from the clip.
- **First person:**
  - Align the game camera to the rest transform of `fp_eye`, plus the viewmodel offset.
  - `fp_eye` is a child of `spine_03`, which the clips rotate slightly, so don't parent the camera to the animated bone.
  - `camera_advance_m` is an optional step-in curve and is not applied automatically.
- **Mobile variants (candidates, visual A/B not yet done):**
  - `ser_aldren_v008_mobile_webp.glb`: 2.68 MB, down from 8.15 MB
  - `william_fp_arms_v004_mobile_webp.glb`: 0.97 MB, down from 4.98 MB
  - WebP textures at q85, identical geometry and skeleton. PNG masters are preserved.

## 5. Contact layer, shadow mode (C.7)
`animation-contact.js` (new; not imported by the game) provides:
- swept segment-to-segment blade contact, with adaptive sub-steps and sign-flip tunnelling detection
- blade-to-body capsule tests
- blade kinematics: velocity and edge alignment

**`ContactTelemetry`** de-duplicates contact episodes and classifies five mismatch types:
- damage without contact
- visible intersection without a clash
- parry success while the blades are separated
- a blade passing through a body
- hit-reaction timing early or late

It runs live in the lab and never changes `combat.js`.

## 6. Animation lab (D.1)
`preview/v040-animation-lab/` is separate from the published `preview/v040-assets/` lab, which is unchanged. Features:
- **Inspection:** orbit and zoom; side, front, combat and first-person cameras; skeleton, joints and armour toggles.
- **Playback:** clip select, play, pause, restart, loop, frame scrub, and 25/50/75/100% speed.
- **Overlays:** contract (gold) versus browser-measured (cyan) blade paths, contact markers, sockets, hit capsules, pelvis trace and feet, plus live readouts.
- **Comparison:** an approximate v0.3 path overlay.
- **Automation:** URL parameters for scripted captures.

**To view it locally:**
1. Run `node tools/serve.mjs 8080`.
2. Open http://localhost:8080/preview/v040-animation-lab/
3. For example: `?char=both&clip=aldren_attack_head&frame=24&cam=side&overlays=path,contact,hitbox&paused=1`

## 7. Rendered review (D.2)
> **Published copies:** in the GitHub repository, the renders below (and `previews/v0.4.0/rig_audit/`, `william_fp_arms_v005_*`) are at the same relative paths under **`previews/v0.4.0-public/`**, for example `previews/v0.4.0-public/animation/aldren_v009/...`.
> - Blender had embedded the local `.blend` path in each PNG's metadata, so `tools/validation/publish-sanitized.mjs` writes copies with those text chunks removed; pixels are byte-identical.
> - The originals stay local, and future renders no longer embed the path.
> - Paired first-person renders: `animation/william_v005/` (paired clips) and `animation/william_v005_b/` (idle and diagonals).
- **Ser Aldren:** `previews/v0.4.0/animation/aldren_v007/`. Stills at wind-up, acceleration, contact, follow-through and recovery from ¾-front and side cameras, plus `video/*_100pct.mp4` and `*_25pct.mp4` (25% is the same frames shown at quarter speed).
- **Ser Aldren's revised overhead:** `previews/v0.4.0/animation/aldren_v009/`.
- **William:** first-person camera renders against Ser Aldren playing the paired clip (William's attack against his parry; William's parry and deflection against his overhead, contact frames aligned).
  - Diagonals and idle: `previews/v0.4.0/animation/william_v004/`.
  - Paired clips: `william_v005/`. `william_v004/` and `william_v004_r2/` are superseded.
- **Browser captures:** `previews/v0.4.0/lab-screenshots/*_20261120-14*.png`.

The renders are from clip v007, which has the same keys as v008: v008 only fixed the GLB frame rate.

## 7b. Paired-contact findings (C.7)
Placing the two fighters at the guard distance and aligning the clips showed two things.

1. **A render-placement bug, now fixed.** The opponent's rig kept a parent that was never loaded, so the first William paired renders put Ser Aldren *inside* William. Those renders are kept in `william_v004/` and superseded by `william_v004_r2/` and `william_v005/`.
2. **The overheads met the roof parries one frame early** (frame 23, at about 1.72–1.78 m), not at the planned contact frame 24.
   - I first misread a frame-24 still as the attack "passing under" the parry. In fact, with no physical response yet, the attacking blade continues *through* the parry after contact.
   - v009/v005 move contact to exactly frame 24 at parry height.

`tests/animation-pairing.test.js` now requires swept blade-to-blade contact within ±3 frames of the plan, in both directions; William's direction includes his suggested step-in.

**Limitation:** until the deflection response is wired in at runtime, an unopposed attacking blade visually continues through a parry in the offline renders.

## 8. Tests
`node --test tests/*.test.js`: **107 / 107 pass**. Two paired-contact tests were added after the counts below, in `tests/animation-pairing.test.js`. The suite is made up of:
- the original 69
- 18 contact-geometry and telemetry tests
- 10 clip-contract tests (naming, timing, phases, grip, joint limits, foot sliding, loop seams, skeleton compatibility, GLB parsing)
- 8 motion-quality tests: true edge leading at contact, tip speed ≤ 24 m/s with no single-frame spikes, transitions to and from ready and parry hold, interruption-safe grip on every attack frame, phase order, rigid sword attachment, smooth reach corrections, and GLB keyframe timing matching the metadata

**Headless Chrome (desktop, SwiftShader software WebGL):** 30 captures, all states rendered. Performance:
- mixer update 0.03–0.08 ms per frame; sword attachment 0.02–0.07 ms
- 50,220 triangles in 35 draw calls with both characters plus lab overlays
- render times come from a CPU rasteriser and **are not device GPU timings**

**Physical iPhone testing has not been done.**

## 9. Local-only editable sources (not published: they can embed absolute local paths)
- **Character rigs:** `source/blender/characters/ser_aldren_v007.blend` and `ser_aldren_v008.blend`. The rig audit opened `ser_aldren_v006.blend` read-only.
- **Animation scenes:** `source/blender/animations/aldren_anim_v001…v009.blend` and `william_anim_v001…v005.blend`.
- **Arms:** `source/blender/first-person/william_fp_arms_v004.blend`, unchanged and the source for the parry search and William clips.

## 10. Outstanding issues (for the approval checkpoint)
1. **The diagonals are clearly different in wind-up and travel**, but both finish near the centre line at the contact frame, so a single still doesn't separate them.
2. **The overhead peak tip speed is 22.9 m/s.** That's plausible for a committed cut but at the upper end; there's a slight speed wobble around frame 21.
3. **William's diagonal attacks need up to 8 cm of smoothed reach correction**, because his shoulders can't step in. The suggested step-in is supplied as `camera_advance_m`.
4. **Residual wrist twist is up to about 72°** at the extremes of the attacks, within anatomical range but worth checking in the renders.
5. **The deflection is generic:** one restrained 6 cm give for the head parry only. There's no direction-specific deflection yet.
6. **Not yet integrated into the game.** The combat engine still uses v0.3 motion, and physical contact is not authoritative.
7. **The mobile WebP variants** need a visual A/B and an on-device load test.
8. **First-person viewmodel: upper arms visible at attack contact.**
   - The viewmodel camera sits 0.20 m behind the eye, which is behind the shoulders, so when William's arms rise forward the upper arms pass in front of the lens.
   - Their open sleeve ends become visible: `william_v005/stills/william_attack_head_pov_24_contact.png`.
   - The proposed fix is first-person-only upper-arm hiding or capping, or a near plane of about 0.15 m. This needs a decision before integration.
9. **The incoming overhead reads poorly in a still.** In first person it's seen almost end-on, and the meeting point with William's roof parry is just above the top edge of the frame. Contact is verified geometrically (pairing test, frame 24), but on-screen readability should be judged in motion, possibly with a contact spark or slight hit-stop at integration.
