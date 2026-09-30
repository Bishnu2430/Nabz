# ADR-0012 · A drawn rice-paper body before the anatomical model

**Status:** Accepted · 2026-09-30 · changes the model part of [ADR-0006](0006-3d-rendering-stack.md); the rendering stack stands

## Context

ADR-0006 chose react-three-fiber for the 3D body map, and a GLB derived from Z-Anatomy for the anatomy. Preparing that GLB means:

- merging hundreds of Z-Anatomy meshes into ten organ-system groups in Blender;
- decimating them to about 150,000 triangles;
- compressing the result to 8 MB or less;
- then proving at least 45 fps on the reference laptop (risk R-04).

The nine-week plan put the body map, the timeline, accounts and export in one sprint (docs/07). The Blender work had not started. The body map is still a *Must* (FR-27, FR-28), and the flat fallback (FR-31) has to show the same thing.

## Decision

1. **Draw the body in code from primitives.**
   - The figure is made of about 20 simple shapes:
     - a lathe-turned torso;
     - capsules for the limbs;
     - scaled spheres for the head, hands and feet.
   - A small shader makes it look like the "rice-paper body" of docs/12 §5.3: translucent paper with a gold rim, and faint contour lines every 5 cm.
   - Each organ system is a group of spheres, capsules and tubes in its usual place. The blood system is a vessel tree from the heart to the limbs and neck; bones are the spine, femurs and knees.
2. **One table for both views.** `frontend/src/components/body/organs.ts` holds, for every organ-system code:
   - its 2D shapes;
   - its 3D focus point.
   The 3D scene and the SVG fallback draw from this table, so they cannot disagree. The codes are the catalogue's `organ_system.code`.
3. **Status by material, as ADR-0006 said.**
   - There is one material per organ system, coloured by its worst status.
   - The stage always uses the dark-theme status colours, because the stage is lacquer in both themes.
   - Abnormal systems breathe through their emissive intensity. The camera flies to a system when it is chosen.
   - With reduced motion there is no breathing and no flight.
4. **The Z-Anatomy model stays the upgrade path.**
   - A GLB whose mesh groups are named after `organ_system.mesh_ids` can replace the primitive groups one at a time.
   - Nothing else changes: the materials, the camera, the organ list and the fallback stay as they are.

## Alternatives considered

| Option | Why not now |
|---|---|
| Z-Anatomy GLB as planned | The Blender preparation and its frame-rate proof don't fit the sprint. It stays the upgrade path |
| A ready-made low-poly body model | The ones with licences that allow redistribution have no separate organs, so they would still need organ meshes |
| Flat SVG only | Meets FR-31 but not FR-27. The 3D view is the part users and the jury remember (ADR-0006) |

## Consequences

- **Nothing to download for the 3D view.** The code is loaded only when the 3D view is shown: 965 kB, or 255 kB gzipped, and most of that is three.js. The main bundle doesn't grow.
- **Few triangles**, well below ADR-0006's budget. Frame rate on the reference laptop (NFR-03) still has to be measured by hand. Automated checks run without a GPU.
- **No share-alike obligation yet.** CC BY-SA applies only once Z-Anatomy meshes are used.
- **Placement is schematic.** Organs sit where a reader expects them, not at anatomical scale. The UI never claims more: it shows systems and statuses, not anatomy.
