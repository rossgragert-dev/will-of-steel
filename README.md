# Will of Steel

A first-person, portrait-mode mobile sword-dueling RPG starring William.

## Design direction

- Three.js and JavaScript; real-time 3D combat.
- Illustrated branching narrative between encounters.
- Right thumb: four directional swipes to cut, stationary hold to lunge.
- Left thumb: hold to enter parry mode; right thumb selects guard.
- Target: iPhone Safari, 60 FPS with a stable 30 FPS fallback.
- Development in ChatGPT first, followed by targeted Claude review and integration.

## Status

The v0.1 combat prototype is imported in this repository. All ten combat-logic tests pass locally. Browser rendering, physical blade collisions, and physical iPhone testing remain outstanding.

Run `npm test` for the combat tests and `npm run serve` to start a local HTTP server (Python 3 required). Open http://localhost:8080 in a WebGL2-capable browser. Three.js loads from a CDN and requires internet access.

GitHub Pages deployment is not yet verified.

See [the original prototype README](docs/v0.1-README.md) for full setup and limitations, and [DESIGN.md](DESIGN.md) for the development plan.
