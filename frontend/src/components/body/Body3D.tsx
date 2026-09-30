import { CameraControls, CameraControlsImpl, Html } from "@react-three/drei";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import * as THREE from "three";

import type { ObsStatus } from "../../api/types";
import { isAbnormal } from "../insights/StatusMark";
import { FOCUS_3D, type OrganCode, type OrganStatus } from "./organs";

/**
 * The rice-paper body on the lacquer stage (docs/12 §5.3, ADR-0012): a translucent paper figure with gold ink
 * contours, organ systems tinted with their worst status, the lungs as faint context. Abnormal systems breathe;
 * choosing one flies the camera to it, names it and dims the rest (FR-27, FR-28). Everything is built from shaped
 * primitives, so there is nothing to download and it runs on integrated graphics.
 */

// The stage is always lacquer, so the dark palette applies whatever the page theme.
const STAGE = {
  paper: "#ede3d1",
  gold: "#c9a55a",
  none: "#a89a82",
  normal: "#8fb093",
  abnormal: "#e07a62",
  critical: "#f0907e",
};

function colourFor(status: ObsStatus | undefined): string {
  if (!status || status === "unknown") return STAGE.none;
  if (status === "normal") return STAGE.normal;
  return status.startsWith("critical") ? STAGE.critical : STAGE.abnormal;
}

const HOME = { position: [0, 1.0, 2.75] as const, target: [0, 0.88, 0] as const };
const { ACTION } = CameraControlsImpl;
type Vec3 = [number, number, number];
const SIDES = [-1, 1] as const;

export default function Body3D({ statuses, selected, onSelect, reducedMotion, names = {} }: {
  statuses: OrganStatus;
  selected: OrganCode | null;
  onSelect: (code: OrganCode) => void;
  reducedMotion: boolean;
  names?: Partial<Record<OrganCode, string>>;
}) {
  const breathing = !reducedMotion && Object.values(statuses).some((s) => s && isAbnormal(s));
  return (
    <Canvas
      dpr={[1, 1.5]}
      frameloop={breathing ? "always" : "demand"}
      camera={{ position: [...HOME.position], fov: 35, near: 0.05, far: 20 }}
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.55} />
      <directionalLight position={[2, 3, 4]} intensity={1.3} />
      <directionalLight position={[-2, 2, -3]} intensity={0.7} color={STAGE.gold} />
      <Camera selected={selected} reducedMotion={reducedMotion} />
      <PaperBody />
      <Organs statuses={statuses} selected={selected} onSelect={onSelect} reducedMotion={reducedMotion} names={names} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.001, 0.02]}>
        <ringGeometry args={[0.2, 0.36, 64]} />
        <meshBasicMaterial color={STAGE.gold} transparent opacity={0.12} />
      </mesh>
    </Canvas>
  );
}

function Camera({ selected, reducedMotion }: { selected: OrganCode | null; reducedMotion: boolean }) {
  const controls = useRef<CameraControls>(null);
  useEffect(() => {
    const c = controls.current;
    if (!c) return;
    if (selected) {
      const [x, y, z] = FOCUS_3D[selected];
      void c.setLookAt(x * 0.6, y + 0.04, z + 0.9, x, y, z, !reducedMotion);
    } else {
      void c.setLookAt(...HOME.position, ...HOME.target, !reducedMotion);
    }
  }, [selected, reducedMotion]);
  return (
    // The wheel scrolls the page, not the camera; pinch or the middle button zooms.
    <CameraControls ref={controls} minDistance={0.45} maxDistance={4.5} minPolarAngle={0.3} maxPolarAngle={2.4}
      smoothTime={0.45}
      mouseButtons={{ left: ACTION.ROTATE, middle: ACTION.DOLLY, right: ACTION.TRUCK, wheel: ACTION.NONE }}
      touches={{ one: ACTION.TOUCH_ROTATE, two: ACTION.TOUCH_DOLLY_TRUCK, three: ACTION.NONE }} />
  );
}

// --- Shaped primitives ----------------------------------------------------------------------------------------------

/** A limb segment that tapers from `r1` to `r2` with rounded ends, optionally with a bulge (calf, forearm). */
function taperedGeometry(r1: number, r2: number, length: number, bulge = 0): THREE.BufferGeometry {
  const pts: THREE.Vector2[] = [];
  const cap = 6;
  for (let i = 0; i <= cap; i++) {
    const a = (i / cap) * (Math.PI / 2);
    pts.push(new THREE.Vector2(Math.sin(a) * r2, -length / 2 - Math.cos(a) * r2 * 0.6));
  }
  const steps = 12;
  for (let i = 1; i < steps; i++) {
    const t = i / steps;
    const r = r2 + (r1 - r2) * t + bulge * Math.sin(Math.PI * Math.min(1, t * 1.4));
    pts.push(new THREE.Vector2(r, -length / 2 + length * t));
  }
  for (let i = cap; i >= 0; i--) {
    const a = (i / cap) * (Math.PI / 2);
    pts.push(new THREE.Vector2(Math.sin(a) * r1, length / 2 + Math.cos(a) * r1 * 0.6));
  }
  return new THREE.LatheGeometry(pts, 24);
}

/** A sphere pushed out of shape vertex by vertex: kidney beans, the liver's wedge, the heart's apex. */
function deformedSphere(fn: (v: THREE.Vector3) => void, detail = 32): THREE.BufferGeometry {
  const g = new THREE.SphereGeometry(1, detail, Math.round(detail * 0.75));
  const p = g.attributes.position as THREE.BufferAttribute;
  const v = new THREE.Vector3();
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    fn(v);
    p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}

const GEOMETRY = {
  // indented on the inner side (the hilum), for the left kidney; the right one is its mirror image
  kidney: () => deformedSphere((v) => {
    if (v.x < 0) v.x *= 1 - 0.55 * Math.exp(-(v.y * v.y) / 0.18);
  }),
  // tall and thick on the person's right, thinning to a wedge on the left
  liver: () => deformedSphere((v) => {
    const t = (v.x + 1) / 2; // 0 at the person's right (−x), 1 at the left
    v.y *= 1.15 - 0.75 * t;
    v.z *= 1 - 0.35 * t;
    if (v.y < 0) v.y *= 0.55;
  }),
  // a rounded base narrowing to an apex
  heart: () => deformedSphere((v) => {
    if (v.y < 0) {
      const k = 1 + v.y * 0.6;
      v.x *= k;
      v.z *= k;
      v.y *= 1.25;
    }
  }),
  lung: () => deformedSphere((v) => {
    if (v.y > 0) {
      const k = 1 - v.y * 0.45;
      v.x *= k;
      v.z *= k;
    }
    if (v.x > 0.4) v.x = 0.4 + (v.x - 0.4) * 0.4; // flat against the heart
  }, 24),
};

function useGeometry(make: () => THREE.BufferGeometry, key: string) {
  const g = useMemo(make, [key]); // eslint-free project: `key` stands for the values `make` closes over
  useEffect(() => () => g.dispose(), [g]);
  return g;
}

/** A shaped segment from one point to another. */
function Segment({ from, to, r1, r2, bulge = 0, material }: {
  from: Vec3;
  to: Vec3;
  r1: number;
  r2?: number;
  bulge?: number;
  material: THREE.Material;
}) {
  const key = `${from}|${to}|${r1}|${r2}|${bulge}`;
  const { position, quaternion, length } = useMemo(() => {
    const a = new THREE.Vector3(...from);
    const b = new THREE.Vector3(...to);
    const dir = a.clone().sub(b);
    return {
      position: a.clone().add(b).multiplyScalar(0.5),
      quaternion: new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize()),
      length: dir.length(),
    };
  }, [key]);
  const geometry = useGeometry(() => taperedGeometry(r1, r2 ?? r1, length, bulge), key);
  return <mesh position={position} quaternion={quaternion} geometry={geometry} material={material} />;
}

function Tube({ points, radius, material }: { points: Vec3[]; radius: number; material: THREE.Material }) {
  const key = `${points.join("|")}|${radius}`;
  const geometry = useGeometry(
    () => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p))), 48, radius, 8),
    key,
  );
  return <mesh geometry={geometry} material={material} />;
}

function Blob({ position, scale, rotation, geometry, material, mirror = false }: {
  position: Vec3;
  scale: Vec3;
  rotation?: Vec3;
  geometry: THREE.BufferGeometry;
  material: THREE.Material;
  mirror?: boolean;
}) {
  return (
    <mesh position={position} rotation={rotation} geometry={geometry} material={material}
      scale={mirror ? [-scale[0], scale[1], scale[2]] : scale} />
  );
}

// --- The paper figure -----------------------------------------------------------------------------------------------

const PAPER_VERTEX = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vView;
  varying float vY;
  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vY = world.y;
    vec4 mv = viewMatrix * world;
    vNormal = normalize(normalMatrix * normal);
    vView = normalize(-mv.xyz);
    gl_Position = projectionMatrix * mv;
  }
`;

// Rim light for the ink outline, plus faint contour lines every 5 cm like a brush drawing on rice paper.
const PAPER_FRAGMENT = /* glsl */ `
  uniform vec3 uPaper;
  uniform vec3 uInk;
  uniform float uStrength;
  varying vec3 vNormal;
  varying vec3 vView;
  varying float vY;
  void main() {
    float facing = abs(dot(normalize(vNormal), normalize(vView)));
    float rim = pow(1.0 - facing, 3.0);
    float t = vY * 20.0;
    float band = abs(fract(t) - 0.5);
    float line = 1.0 - smoothstep(0.0, fwidth(t) * 1.2, band);
    vec3 colour = mix(uPaper, uInk, clamp(rim * 1.2, 0.0, 1.0));
    float alpha = (0.05 + rim * 0.6 + line * 0.09 * (1.0 - rim)) * uStrength;
    gl_FragColor = vec4(colour, alpha);
  }
`;

function paperMaterial(strength: number) {
  return new THREE.ShaderMaterial({
    uniforms: {
      uPaper: { value: new THREE.Color(STAGE.paper) },
      uInk: { value: new THREE.Color(STAGE.gold) },
      uStrength: { value: strength },
    },
    vertexShader: PAPER_VERTEX,
    fragmentShader: PAPER_FRAGMENT,
    transparent: true,
    depthWrite: false,
  });
}

function PaperBody() {
  const material = useMemo(() => paperMaterial(1), []);
  const faint = useMemo(() => paperMaterial(0.55), []);

  // hips, waist, ribcage, chest, shoulders, then the base of the neck
  const torso = useGeometry(() => {
    const curve = new THREE.CatmullRomCurve3([
      [0.0, 0.83], [0.11, 0.835], [0.165, 0.87], [0.172, 0.94], [0.152, 1.02], [0.138, 1.08], [0.15, 1.16],
      [0.168, 1.25], [0.176, 1.33], [0.186, 1.39], [0.165, 1.44], [0.1, 1.465], [0.052, 1.475],
    ].map(([r, y]) => new THREE.Vector3(r, y, 0)));
    const pts = curve.getPoints(48).map((p) => new THREE.Vector2(Math.max(p.x, 0), p.y));
    const g = new THREE.LatheGeometry(pts, 48);
    g.scale(1, 1, 0.6);
    return g;
  }, "torso");
  const neck = useGeometry(() => taperedGeometry(0.043, 0.05, 0.09), "neck");
  const skull = useGeometry(() => new THREE.SphereGeometry(1, 32, 24), "skull");

  return (
    <group>
      <mesh geometry={torso} material={material} />
      <mesh geometry={neck} position={[0, 1.52, 0]} material={material} />
      <Blob geometry={skull} position={[0, 1.645, -0.005]} scale={[0.082, 0.1, 0.095]} material={material} />
      <Blob geometry={skull} position={[0, 1.585, 0.018]} scale={[0.062, 0.058, 0.066]} material={faint} />
      {SIDES.map((s) => (
        <group key={s}>
          <Blob geometry={skull} position={[0.185 * s, 1.405, -0.005]} scale={[0.058, 0.052, 0.058]} material={faint} />
          <Segment from={[0.2 * s, 1.41, 0]} to={[0.245 * s, 1.14, -0.012]} r1={0.047} r2={0.037} bulge={0.004}
            material={material} />
          <Segment from={[0.245 * s, 1.14, -0.012]} to={[0.275 * s, 0.9, 0.02]} r1={0.036} r2={0.026} bulge={0.006}
            material={material} />
          <Blob geometry={skull} position={[0.285 * s, 0.84, 0.024]} scale={[0.027, 0.058, 0.015]}
            rotation={[0, 0, 0.08 * s]} material={material} />
          <Segment from={[0.265 * s, 0.875, 0.034]} to={[0.258 * s, 0.84, 0.05]} r1={0.009} material={material} />
          <Segment from={[0.088 * s, 0.87, 0]} to={[0.097 * s, 0.49, 0.012]} r1={0.08} r2={0.05} material={material} />
          <Segment from={[0.097 * s, 0.49, 0.012]} to={[0.1 * s, 0.1, -0.004]} r1={0.047} r2={0.03} bulge={0.012}
            material={material} />
          <Blob geometry={skull} position={[0.103 * s, 0.035, 0.045]} scale={[0.038, 0.028, 0.095]} material={material} />
        </group>
      ))}
    </group>
  );
}

// --- Organ systems --------------------------------------------------------------------------------------------------

function Organs({ statuses, selected, onSelect, reducedMotion, names }: {
  statuses: OrganStatus;
  selected: OrganCode | null;
  onSelect: (code: OrganCode) => void;
  reducedMotion: boolean;
  names: Partial<Record<OrganCode, string>>;
}) {
  const props = (code: OrganCode) => ({
    code, status: statuses[code], selected: selected === code, dimmed: selected !== null && selected !== code,
    onSelect, reducedMotion, name: names[code],
  });
  const kidney = useGeometry(GEOMETRY.kidney, "kidney");
  const liver = useGeometry(GEOMETRY.liver, "liver");
  const heart = useGeometry(GEOMETRY.heart, "heart");
  const lung = useGeometry(GEOMETRY.lung, "lung");
  const round = useGeometry(() => new THREE.SphereGeometry(1, 20, 14), "round");
  const lungMaterial = useMemo(() => paperMaterial(0.8), []);

  return (
    <>
      {/* the lungs are context only: no lab test in the catalogue belongs to them */}
      {SIDES.map((s) => (
        <Blob key={s} geometry={lung} position={[0.085 * s, 1.3, -0.015]} scale={[0.07, 0.125, 0.07]}
          material={lungMaterial} mirror={s < 0} />
      ))}

      <OrganSystem {...props("bone")}>
        {(m) => (
          <>
            {SIDES.map((s) => (
              <group key={s}>
                <Segment from={[0.086 * s, 0.84, -0.005]} to={[0.097 * s, 0.515, 0.008]} r1={0.019} r2={0.016}
                  material={m} />
                <Blob geometry={round} position={[0.097 * s, 0.487, 0.016]} scale={[0.03, 0.024, 0.028]} material={m} />
                <Segment from={[0.099 * s, 0.46, 0.01]} to={[0.1 * s, 0.1, -0.003]} r1={0.015} r2={0.012} material={m} />
              </group>
            ))}
            {Array.from({ length: 14 }, (_, i) => (
              <mesh key={i} position={[0, 0.95 + i * 0.036, -0.078 + Math.sin(i / 4) * 0.01]} material={m}>
                <boxGeometry args={[0.032, 0.022, 0.028]} />
              </mesh>
            ))}
            {/* ribs: open rings around the chest, following the torso's depth */}
            {Array.from({ length: 6 }, (_, i) => (
              // the open side of each ring faces forward (the sternum), tilted down at the front
              <group key={`rib${i}`} position={[0, 1.2 + i * 0.037, -0.01]} scale={[1, 1, 0.62]}>
                <mesh rotation={[Math.PI / 2 + 0.25, 0, 0.725 * Math.PI]} material={m}>
                  <torusGeometry args={[0.14 + Math.sin((i / 5) * Math.PI) * 0.016, 0.0045, 6, 40, Math.PI * 1.55]} />
                </mesh>
              </group>
            ))}
            {/* pelvis */}
            <mesh position={[0, 0.9, -0.01]} rotation={[Math.PI / 2 + 0.35, 0, 0]} scale={[1, 0.7, 1]} material={m}>
              <torusGeometry args={[0.1, 0.014, 8, 36]} />
            </mesh>
          </>
        )}
      </OrganSystem>

      <OrganSystem {...props("blood")}>
        {(m) => (
          <>
            <Tube material={m} radius={0.007} points={[
              [0.02, 1.34, 0.04], [0.01, 1.41, 0.02], [-0.02, 1.4, -0.01], [0, 1.3, -0.04], [0, 1.1, -0.04],
              [0, 0.95, -0.02],
            ]} />
            {SIDES.map((s) => (
              <group key={s}>
                <Tube material={m} radius={0.006} points={[
                  [0, 0.95, -0.02], [0.06 * s, 0.86, 0.01], [0.09 * s, 0.6, 0.02], [0.1 * s, 0.3, 0.01], [0.1 * s, 0.08, 0.01],
                ]} />
                <Tube material={m} radius={0.005} points={[
                  [0.01 * s, 1.41, 0.01], [0.12 * s, 1.43, 0], [0.21 * s, 1.38, 0.01], [0.245 * s, 1.13, 0.01],
                  [0.275 * s, 0.9, 0.03],
                ]} />
                <Tube material={m} radius={0.004} points={[[0.015 * s, 1.41, 0.02], [0.025 * s, 1.5, 0.03], [0.03 * s, 1.6, 0.02]]} />
              </group>
            ))}
          </>
        )}
      </OrganSystem>

      <OrganSystem {...props("kidney")}>
        {(m) => SIDES.map((s) => (
          <Blob key={s} geometry={kidney} position={[0.068 * s, 1.07, -0.05]} rotation={[0, 0, 0.22 * s]}
            scale={[0.03, 0.054, 0.024]} material={m} mirror={s < 0} />
        ))}
      </OrganSystem>

      <OrganSystem {...props("liver")}>
        {(m) => (
          <Blob geometry={liver} position={[-0.045, 1.195, 0.035]} rotation={[0.1, 0, 0.12]} scale={[0.115, 0.065, 0.075]}
            material={m} />
        )}
      </OrganSystem>

      <OrganSystem {...props("pancreas")}>
        {(m) => <Segment from={[-0.035, 1.105, 0.035]} to={[0.1, 1.14, 0.0]} r1={0.021} r2={0.011} material={m} />}
      </OrganSystem>

      <OrganSystem {...props("immune")}>
        {(m) => (
          <>
            <Blob geometry={kidney} position={[0.11, 1.19, -0.025]} rotation={[0, 0, -0.35]} scale={[0.024, 0.045, 0.02]}
              material={m} />
            {([[0.14, 1.36, 0.01], [0.08, 0.89, 0.05], [0.035, 1.47, 0.03]] as Vec3[]).flatMap(([x, y, z]) =>
              SIDES.map((s) => (
                <Blob key={`${x}${y}${s}`} geometry={round} position={[x * s, y, z]} scale={[0.012, 0.012, 0.012]}
                  material={m} />
              )))}
          </>
        )}
      </OrganSystem>

      <OrganSystem {...props("heart")}>
        {(m) => (
          <Blob geometry={heart} position={[0.025, 1.33, 0.05]} rotation={[0.25, 0.2, 0.55]} scale={[0.048, 0.058, 0.044]}
            material={m} />
        )}
      </OrganSystem>

      <OrganSystem {...props("thyroid")}>
        {(m) => (
          <>
            {SIDES.map((s) => (
              <Blob key={s} geometry={round} position={[0.017 * s, 1.49, 0.038]} rotation={[0, 0, -0.25 * s]}
                scale={[0.012, 0.022, 0.01]} material={m} />
            ))}
            <mesh position={[0, 1.482, 0.046]} material={m}><boxGeometry args={[0.022, 0.008, 0.008]} /></mesh>
          </>
        )}
      </OrganSystem>

      <OrganSystem {...props("urinary")}>
        {(m) => (
          <>
            <Blob geometry={round} position={[0, 0.92, 0.06]} scale={[0.04, 0.032, 0.036]} material={m} />
            {SIDES.map((s) => (
              <Tube key={s} material={m} radius={0.003} points={[[0.062 * s, 1.03, -0.05], [0.04 * s, 0.98, 0], [0.015 * s, 0.93, 0.05]]} />
            ))}
          </>
        )}
      </OrganSystem>

      {statuses.prostate && (
        <OrganSystem {...props("prostate")}>
          {(m) => <Blob geometry={round} position={[0, 0.875, 0.04]} scale={[0.018, 0.016, 0.017]} material={m} />}
        </OrganSystem>
      )}
    </>
  );
}

/**
 * One organ system: its material follows the status; abnormal systems breathe, the chosen one glows and the others
 * fade back. Hovering or choosing a system shows its name beside it.
 */
function OrganSystem({ code, status, selected, dimmed, onSelect, reducedMotion, name, children }: {
  code: OrganCode;
  status?: ObsStatus;
  selected: boolean;
  dimmed: boolean;
  onSelect: (code: OrganCode) => void;
  reducedMotion: boolean;
  name?: string;
  children: (material: THREE.MeshStandardMaterial) => ReactNode;
}) {
  const [hovered, setHovered] = useState(false);
  const material = useMemo(() => new THREE.MeshStandardMaterial({ roughness: 0.45, metalness: 0.05, transparent: true }), []);
  const hasData = Boolean(status);

  useEffect(() => {
    const colour = new THREE.Color(colourFor(status));
    material.color.copy(colour);
    material.emissive.copy(colour);
    material.depthWrite = hasData && !dimmed;
  }, [material, status, hasData, dimmed]);

  useEffect(() => {
    document.body.style.cursor = hovered && hasData ? "pointer" : "";
    return () => {
      document.body.style.cursor = "";
    };
  }, [hovered, hasData]);

  const abnormal = Boolean(status && isAbnormal(status));
  useFrame(({ clock, invalidate }) => {
    const base = !hasData ? 0.02 : selected ? 0.85 : 0.3;
    const breath = abnormal && !reducedMotion && !dimmed ? 0.35 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 2.2)) : 0;
    const next = base + breath + (hovered && hasData ? 0.25 : 0);
    const opacity = !hasData ? 0.18 : dimmed ? 0.28 : 0.95;
    if (Math.abs(material.emissiveIntensity - next) > 0.001 || Math.abs(material.opacity - opacity) > 0.005) {
      material.emissiveIntensity = next;
      material.opacity += (opacity - material.opacity) * (reducedMotion ? 1 : 0.2);
      invalidate();
    }
  });

  const click = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (hasData) onSelect(code);
  };
  const [x, y, z] = FOCUS_3D[code];
  return (
    <group
      name={code}
      onClick={click}
      onPointerOver={(e) => {
        e.stopPropagation();
        setHovered(true);
      }}
      onPointerOut={() => setHovered(false)}
    >
      {children(material)}
      {name && hasData && (hovered || selected) && (
        <Html position={[x + (x >= 0 ? 0.09 : -0.09), y + 0.04, z]} center zIndexRange={[20, 0]}
          style={{ pointerEvents: "none" }}>
          <span className="whitespace-nowrap rounded-full border border-[#c9a55a]/50 bg-[#16120f]/85 px-2.5 py-1 text-xs text-[#ede3d1]">
            {name}
          </span>
        </Html>
      )}
    </group>
  );
}
