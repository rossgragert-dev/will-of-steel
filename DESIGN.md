# Design record — initial decisions and implementation plan

## Confirmed
- Three.js, portrait mobile, first-person sword dueling.
- Fully real-time 3D combat; no pre-rendered attack sequences or mandatory quick-time events.
- Illustrated, non-real-time, choose-your-own-adventure storytelling with branching choices between encounters.
- Right thumb: four directional swipes for attacks plus stationary hold to lunge. Left thumb: hold to enter parry mode; right thumb chooses the guard.
- Develop and test in ChatGPT where feasible before handing a documented, tested project to Claude.

## Proposed, not locked
- Original low-fantasy setting with selectable origins, central campaign + optional quests, eventual boss and multi-opponent fights. Official title: Will of Steel. The protagonist is William; his background and the path he takes remain customizable.
- Longsword as initial weapon, first training yard as arena. Automatic footwork with future options to manage range. Combat realism hybrid (plausible technique with cinematic timing). No magic decision yet.
- Prototype directional matching is intentionally simple: swipe up = rising attack / low guard, down = overhead / high guard, left/right = lateral, center = thrust / central guard. Test mirror mapping on device before locking.
- Successful defense creates opening; perfectly timed guard gives longer opening. Spamming consumes stamina. Health and guard are visible for tuning, not committed as the permanent HUD.

## Milestone v0.1 — core combat spike
Two-mode narrative entry, one procedural opponent/arena, gesture parser, timing-based combat, parries/ripostes, basic visuals and feedback. Verify dual-touch capture and controls on iPhone before art polish.

## Milestone v0.2 — one convincing duel
- Introduce articulated/deforming rig with IK attaching both hands to longsword, authored windup/contact/recovery poses and blends, physically plausible blade orientation.
- Add blade swept-segment collision and body hit volumes, guard/parry gating, frame-independent contact and collision event debouncing. Keep the combat rules deterministic and separate from rendering.
- Add range/footwork states, readable opponent body cues, stagger and hit reaction, optional directional assist, training and practice feedback. Target stable 60 FPS on iPhone with 30 FPS fallback; measure on device rather than claiming achieved performance.
- Improve one original opponent and longsword, materials and lighting. Replace procedural geometry with optimized GLB assets when available; mobile LOD and texture budget.

## Milestone v0.3 — narrative foundation
Data-driven scene nodes, illustrated backgrounds, decisions, conditions, outcomes (win/loss/surrender), flags, and local versioned saves. First story segment introduces character and meaningful alternative paths. Ensure narrative mode suspends combat. Avoid hardcoding plot in rendering layer.

## Milestone v0.4 — vertical slice
One polished chapter with distinct opponents, unlockable skills and equipment, repeatable arena and duel practice. Measure load times, performance, input and audio. Add regression tests and accessibility settings. Iterate on playtesting before expanding weapons and campaign.

## Claude handoff threshold
Only when worthwhile: include repository, tested baseline/commit, design decisions, known limitations, source layout, build instructions, test results, preview URL when deployed, and incremental next tasks. Ask Claude to retain controls and accepted gameplay, work on isolated branch, report measured tests and avoid changing scope without approval.
