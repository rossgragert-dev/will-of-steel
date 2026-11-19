# v0.4.0 Phase B: review checkpoint (design approval required)

Date: 2026-11-19. All renders are actual Cycles output from Blender 5.3.0, inspected one by one. Nothing has been integrated into the game; `node --test` still passes 69/69.

## Review set
- Sword: `previews/v0.4.0/longsword_xva_v006_{side,edge,hilt,three_quarter}.png`
- Ser Aldren: `previews/v0.4.0/ser_aldren_v006_{guard_front34,guard_side,guard_back34,guard_detail_upper,player_pov_portrait}.png`
- William's arms, at the game's 61° FOV in a 720×1280 portrait frame with Ser Aldren at 2.3 m: `previews/v0.4.0/william_fp_arms_v004_pov_{ready,head_5,upperLeft_4,upperRight_3,lowerLeft_1,lowerRight_2}.png` and `_inspect_last_pose.png`

## Verified
- All GLBs pass `tools/validation/inspect-glb.mjs`: required bones and markers are present and triangle counts are within budget.
- Ser Aldren's guard pose is driven by the rig's own IK. Wrist and ankle error is 0.04 mm or less; the left hand sits within 0.04 mm of the sword's `hand_secondary`.
- The IK pole angles were calibrated automatically (arms -90°, legs +90°). Face orientation was checked automatically: 0 flipped faces.

## Bugs found and fixed during review
1. All roughness and normal maps were saved black, because the colour space was set after the pixels were written. This produced the chrome look. Fixed, and a pixel-loss guard was added.
2. The steel normal map caused sawtooth shading on the lofted plates; isolated with `tools/blender/diag_shading.py`. The steel now uses no normal map.
3. Eevee is degraded on this workstation (Radeon Pro W5500, missing a Vulkan feature), so review renders use Cycles on the CPU.
4. Cloth and straps intersected the plates. The cloth was slimmed and the straps given clearance.

## First-person framing: decision "readability first" (user, 2026-11-19), arms v004
Each guard keeps its blade angle from `rig-poses.js`. A search over 300 candidates per guard chose the hilt position, clavicle lift (0° or 12°) and elbow pole. Candidates were scored on how much of the opponent the arms hide (screen raster, 36×64, opponent at 2.3 m), IK reach, and whether the blade and hilt are visible. Viewmodel camera: 0.20 m back, 0.02 m up, pitched 12° down, 61° vertical FOV.

| Guard | Opponent hidden | Arms' share of screen | Blade in frame | Left hand to grip |
|---|---|---|---|---|
| ready | 0% | 3% | 90% | 0.0 mm |
| head (5) | 27% | 34% | 24% | 1.2 mm |
| upper left (4) | 10% | 20% | 52% | 0.0 mm |
| upper right (3) | 1% | 11% | 52% | 0.0 mm |
| lower left (1) | 0% | 12% | 10% | 0.0 mm |
| lower right (2) | 8% | 19% | 5% | 0.0 mm |

The low guards point the blade down and out of frame, as the guard requires, and the hilt and hands stay visible. The head guard is still the most obstructive. The viewmodel camera offset needs your approval before it goes into the game.

## Known issues (not yet fixed)
- **Head guard:** the raised right forearm still covers about a quarter of the opponent.
- **Ser Aldren:** the gauntlets read as simple cylinders, and the sallet, visor and bevor look like stacked bands. Only one pose has been shown; there's no animation yet (Phase C).
- **File size:** the GLBs embed lossless PNGs (8.1 MB knight, 5.0 MB arms). WebP or JPEG textures are needed before mobile integration.
- **Quality ceiling:** the art is entirely procedural (scripted lofts, no sculpting). It reads as grounded and historically plausible, but it doesn't reach hand-sculpted AAA quality, such as the titles named in the handoff.
