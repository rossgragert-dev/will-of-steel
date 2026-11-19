# Will of Steel v0.4.0 "Forged in Reality": progress report

Status as of 2026-11-19, on branch `development/v040-forged-in-reality`. Main and the live v0.3.0 game are unchanged.

| Phase | Status |
|---|---|
| A. Safety, environment, baseline | **Done** |
| B. Master knight, sword, first-person arms, PBR | **Candidates ready, awaiting your design approval** |
| C. Rigs, IK, four first movements | Rigs and IK done and validated in static poses; **no animation clips yet** |
| D. Renders, animation lab, comparison | Still renders done; **browser lab not started** |
| E–I. Animation library, physical contacts, playable preview, variants, release | Not started |

## Completed assets (all original and script-generated)
- **Longsword v006** (`build_longsword.py`).
  - Type XVa blade (92 cm, diamond section with fuller, distal taper from 7.8 to 3 mm), forged crossguard, waisted leather grip, wheel pommel. 2,610 triangles.
  - Named hand, blade and edge markers plus capsule/box collision metadata.
- **Ser Aldren v006** (`build_ser_aldren.py`).
  - Mid-15th-century harness: sallet, visor, bevor, two-lame gorget, rounded breastplate and backplate, fauld and culet, tassets, lamed pauldrons, rerebraces, winged couters, vambraces, mitten gauntlets, cuisses, winged poleyns, greaves and lamed sabatons, all worn over a padded doublet and hose.
  - Mail skirt and armpit voiders, leather straps and buckles, sword belt.
  - 35,064 triangles in 5 skinned slots (13 draw calls).
- **William's first-person arms v004** (`build_william_arms.py`). Quilted gambeson sleeves, couters, vambraces with straps and buckles, leather gloves with fully articulated fingers. 9,636 triangles.
- **Shared libraries.**
  - `wos_humanoid.py`: armature builder, thick armour shells, Catmull-Rom lofts, distance-based skinning with twist bones, IK and hinge limits.
  - `wos_materials.py`: tileable procedural PBR steel, cloth, mail and leather, with a pixel-loss guard.

## Rendered previews (Cycles, inspected)
`previews/v0.4.0/`:
- sword: side, edge, hilt, three-quarter
- knight: guard pose front ¾, side, back ¾, upper detail, player POV
- arms: six first-person guard views at the game's 61° portrait FOV with the knight at 2.3 m, plus an inspection view

## Rigging and animation
- **Knight rig:** 45 bones (34 deform), including twist bones, IK and pole controls, and `weapon_r` / `grip_l` sockets. Elbow and knee hinge limits.
- **Arms rig:** 51 bones, with three phalanges per finger and an `fp_eye` reference bone.
- **IK calibration:** pole angles calibrated automatically. Guard-pose IK error is 0.04 mm or less, and the left hand sits on the sword grip within 1.2 mm in every guard.
- **Weapon attachment convention:** documented in `assets/v0.4.0/MANIFEST.md`.
- **Animation:** none yet. No clips have been authored and nothing is motion capture.

## Combat changes
None to game code yet. The deterministic combat engine, controls, AI and tests are unchanged.

Groundwork for combat realism:
- Collision markers and volumes on the sword.
- Physically reachable first-person guard poses (`william_fp_guards_v004.json`) to replace the old 1.13 m hilt distance.

## Testing
- `node --test tests/*.test.js`: 69/69 pass, the same as the v0.3.0 baseline.
- All GLBs pass `tools/validation/inspect-glb.mjs`: required bones and markers present, triangle budgets met.
- Automatic checks: 0 flipped faces; IK and grip errors as above; guard visibility scores.
- Not done yet: Three.js runtime rendering, performance on mobile, and on-device iPhone testing.

## Outstanding issues
1. **Approvals needed:**
   - the knight's and sword's design
   - the viewmodel camera offset (0.20 m back, 12° pitch)
2. **Head guard** still hides 27% of the opponent.
3. **The knight's gauntlets and helmet** read as simple shapes. All art is procedural and below hand-sculpted AAA quality.
4. **GLB sizes:** 8.1 MB knight and 5.0 MB arms, because textures are lossless PNGs. They need WebP/JPEG compression before mobile use.
5. **Editable `.blend` sources** are kept local, not published, because they can embed absolute local paths. They can be regenerated from the committed scripts.
6. **Eevee is degraded** on the development GPU (missing a Vulkan feature), so previews use Cycles on the CPU.

## Remaining tasks
- **C:** author the ready stance, overhead strike, diagonal cut and overhead parry, for both the enemy and first person.
- **D:** browser animation lab (GLTFLoader, AnimationMixer, scrubbing, speeds, overlays), compared against v0.3.0.
- **E–I:**
  - the 36-motion core library
  - shadow-mode swept collision telemetry with a debug overlay
  - an isolated Three.js playable preview with a procedural fallback
  - Edric, Lucan, Garrick and Rowan variants
  - the courtyard environment
  - texture compression and performance measurement
  - release notes
