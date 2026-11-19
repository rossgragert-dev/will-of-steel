# v0.4.0 Phase A — Safety, Environment and Baseline Audit

Date: 2026-11-18
Branch: `development/v040-forged-in-reality` (local only, not pushed), based on `main` @ `ae61ad5` (v0.3.0 The Living Blade).

## Safety policy
The no-deletion / backup-before-modify policy in `WILL_OF_STEEL_V040_HANDOFF.md` §1 has been acknowledged. Nothing has been deleted or overwritten. This file is new.

## Environment (read-only checks)
| Tool | Result |
|---|---|
| Git | 2.56.0.windows.4 |
| Node.js | v26.13.1 (`C:\Program Files\nodejs\node.exe`) |
| npm | 11.20.0 |
| Blender | **Not found.** Not on PATH and not in `C:\Program Files\Blender Foundation`, Steam `common\Blender`, or `%LOCALAPPDATA%\Programs\Blender Foundation`. No path has been provided yet. No wider search was run, per policy. |
| Unity | Editor 6000.6.9f1 under `C:\Program Files\Unity\Hub\Editor` (optional sandbox only) |
| Chrome | Present (`C:\Program Files\Google\Chrome\Application\chrome.exe`) |
| Edge | Present (`C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`) |
| Python | Only the Windows Store stub (`WindowsApps\python.exe`). The `npm run serve` script (`python3 -m http.server`) will probably not work. |

## Repository state
- Working tree is clean apart from untracked `.claude/` (local Claude settings, which must never be committed) and `WILL_OF_STEEL_V040_HANDOFF.md`.
- Branches: `main`, plus remote `archive/v0.1.2` through `archive/v0.2.2`. All are untouched.
- There is no `.gitignore`.
- Runtime: about 330 lines of compact ES modules. Three.js 0.180.0 loads from the jsDelivr CDN, with unpkg as a fallback. No local assets, no build step, no npm dependencies.
- Rendering: `art.js` (procedural materials/meshes), `fencing-rig.js` + `motion.js` + `rig-poses.js` (Bone hierarchy, analytic IK, 10 authored clips), `blade-contact.js` (swept contact, effects only).
- Simulation: `combat.js` (deterministic Duel, authoritative), `opponents.js` (5 profiles), `zones.js` / `blade-input.js` (controls).

## Baseline tests
Command: `node --test tests/*.test.js` (the same as `npm test`; reviewed and safe: read-only, no file writes).

**69 tests, 69 pass, 0 fail, 0 skipped. Duration about 332 ms.** These match the previously reported 69 checks.

Test files: advanced, art, blade-input, combat, motion, opponents, rig-poses, zones.

## Known limitations carried in (from docs/v0.3.0.md and handoff §4)
Rigid-plate knight with no skinned humanoid. Tube forearms and unnatural wrists/elbows. The high parry hides the enemy. Hits sometimes register without visual reach. Weak deflection contact. Upright, robotic posture with no footwork or weight transfer. Armour looks shiny and disconnected. No external assets, no MoCap.
