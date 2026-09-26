# ADR-0006 · 3D body map with react-three-fiber and Z-Anatomy

**Status:** Accepted · 2026-09-26

## Context

The 3D body map is the part of Nabz that judges and users remember. It must run smoothly on a laptop with integrated Intel graphics and on mid-range phones. It must let the app colour and select organ systems by ID, and it must use a legally reusable anatomy model.

## Decision

- **Rendering.** three.js through **react-three-fiber**, with **drei** helpers (camera controls, GLTF loading, bounds and fly-to) and **postprocessing** (bloom and outline for the "glowing organ" effect).
- **Model.** Organ-system meshes derived from **Z-Anatomy** (CC BY-SA 4.0). In Blender: merge into about 15 organ-system groups with stable names that match `organ_system.mesh_ids`, decimate to a total of about 150k triangles, and export GLB with Draco or meshopt compression (target ≤ 8 MB).
- **Status materials.** One shared material per status (normal, low/high, critical, no data) using Nord palette colours, animated by emissive intensity rather than new materials.
- **Performance guards.** Device-pixel-ratio cap at 1.5, frame-on-demand rendering when idle, and organ-level detail loaded on focus.
- **Fallback.** A 2D SVG body with the same organ IDs when WebGL 2 is unavailable (FR-31).

## Alternatives considered

| Option | Why not |
|---|---|
| Plain three.js (imperative) | More code to keep scene and React state in sync |
| Babylon.js | Capable, but a smaller React ecosystem and a heavier bundle |
| Unity WebGL export | Large download, poor mobile performance, awkward integration with the web UI |
| Commercial anatomy models | Licences usually forbid redistribution or are expensive |

## Consequences

- Share-alike: modified anatomy meshes must be published under CC BY-SA 4.0, with attribution on the About screen.
- A Sprint 1 spike must prove the frame rate on the demo laptop before the design depends on it (risk R-04).
