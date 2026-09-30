import type { ObsStatus } from "../../api/types";

/**
 * Organ systems on the body map, in drawing order (back to front). The codes are `organ_system.code` from the
 * catalogue; the 2D diagram and the 3D scene both draw from this table so they always show the same thing (FR-31).
 *
 * 2D coordinates are in a 240 × 530 viewBox with the person facing the viewer, so the person's right side is on
 * the left of the screen. 3D coordinates are metres in a 1.75 m figure, +x to the person's left, +z forward.
 */
export type OrganCode =
  | "bone" | "blood" | "kidney" | "liver" | "pancreas" | "immune" | "heart" | "thyroid" | "urinary" | "prostate";

export const ORGAN_ORDER: OrganCode[] = [
  "bone", "blood", "kidney", "liver", "pancreas", "immune", "heart", "thyroid", "urinary", "prostate",
];

/** A filled area, or a line (vessels, bones) drawn with a stroke. */
export type Shape2D = { d: string; line?: boolean };

const ellipse = (cx: number, cy: number, rx: number, ry: number): Shape2D => ({
  d: `M${cx - rx} ${cy}a${rx} ${ry} 0 1 0 ${2 * rx} 0a${rx} ${ry} 0 1 0 ${-2 * rx} 0Z`,
});

export const SHAPES_2D: Record<OrganCode, Shape2D[]> = {
  bone: [
    { d: "M98 306 L101 396", line: true },
    { d: "M142 306 L139 396", line: true },
    ellipse(101, 402, 5, 4),
    ellipse(139, 402, 5, 4),
  ],
  blood: [
    // aorta from the heart, down to the legs; arteries to the arms and neck
    { d: "M124 142 C 122 128, 112 126, 116 138 C 118 170, 120 230, 120 282 C 114 300, 110 330, 108 380 C 106 420, 104 450, 103 485", line: true },
    { d: "M120 282 C 126 300, 130 330, 132 380 C 134 420, 136 450, 137 485", line: true },
    { d: "M116 126 C 100 122, 82 124, 72 138 C 66 170, 62 230, 56 300", line: true },
    { d: "M124 126 C 140 122, 158 124, 168 138 C 174 170, 178 230, 184 300", line: true },
    { d: "M116 126 L114 84", line: true },
    { d: "M124 126 L126 84", line: true },
  ],
  kidney: [
    { d: "M92 236 C 92 222, 108 222, 108 232 C 104 236, 104 242, 108 246 C 108 256, 92 254, 92 236 Z" },
    { d: "M148 236 C 148 222, 132 222, 132 232 C 136 236, 136 242, 132 246 C 132 256, 148 254, 148 236 Z" },
  ],
  liver: [
    { d: "M89 186 C 92 176, 118 174, 140 180 C 144 182, 142 188, 136 191 C 122 198, 104 206, 94 204 C 88 202, 87 194, 89 186 Z" },
  ],
  pancreas: [
    { d: "M106 218 C 108 212, 122 213, 132 211 C 140 209, 148 210, 148 214 C 148 218, 140 219, 132 220 C 122 222, 110 225, 106 218 Z" },
  ],
  immune: [
    { d: "M146 184 C 152 182, 156 190, 154 198 C 152 206, 146 206, 145 200 C 144 194, 142 186, 146 184 Z" },
    ellipse(86, 160, 3, 3),
    ellipse(154, 160, 3, 3),
    ellipse(102, 316, 3, 3),
    ellipse(138, 316, 3, 3),
  ],
  heart: [
    { d: "M114 146 C 115 136, 131 132, 139 139 C 146 145, 145 158, 136 168 C 128 166, 116 158, 114 146 Z" },
  ],
  thyroid: [
    { d: "M120 98 C 117 93, 112 93, 112 98 C 112 103, 117 104, 120 100 C 123 104, 128 103, 128 98 C 128 93, 123 93, 120 98 Z" },
  ],
  urinary: [
    { d: "M103 250 C 108 266, 112 280, 114 290", line: true },
    { d: "M137 250 C 132 266, 128 280, 126 290", line: true },
    ellipse(120, 297, 12, 9),
  ],
  prostate: [ellipse(120, 313, 5, 4)],
};

/** One half of the figure (the person's right); the other half is its mirror image. */
export const BODY_HALF_2D =
  "M108 76 C 109 90, 106 99, 96 104 C 84 109, 71 111, 65 122 C 59 133, 58 152, 56 172 C 54 196, 50 216, 48 236 " +
  "C 46 260, 44 282, 42 300 C 40 312, 37 322, 41 331 C 45 338, 54 336, 56 327 C 58 317, 58 307, 60 299 " +
  "C 64 276, 66 252, 70 230 C 73 210, 75 190, 79 160 C 82 190, 86 220, 86 245 C 86 265, 80 282, 80 300 " +
  "C 80 330, 84 368, 88 400 C 91 432, 90 462, 92 488 C 93 498, 83 505, 85 511 C 88 517, 108 517, 110 510 " +
  "C 112 500, 109 490, 110 478 C 111 450, 113 424, 113 400 C 114 368, 116 340, 120 326";

/** Where the 3D camera looks when an organ is chosen: [x, y, z] in metres. */
export const FOCUS_3D: Record<OrganCode, [number, number, number]> = {
  bone: [0, 0.62, 0.02],
  blood: [0, 1.2, 0.04],
  kidney: [0, 1.06, -0.03],
  liver: [-0.06, 1.2, 0.04],
  pancreas: [0.02, 1.12, 0.02],
  immune: [0.07, 1.18, 0.02],
  heart: [0.03, 1.33, 0.05],
  thyroid: [0, 1.5, 0.04],
  urinary: [0, 0.9, 0.04],
  prostate: [0, 0.84, 0.02],
};

export type OrganStatus = Partial<Record<OrganCode, ObsStatus>>;

export const isOrganCode = (code: string): code is OrganCode => (ORGAN_ORDER as string[]).includes(code);
