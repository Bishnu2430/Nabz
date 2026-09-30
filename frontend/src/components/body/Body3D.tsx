import { CameraControls, CameraControlsImpl } from "@react-three/drei";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import * as THREE from "three";

import type { ObsStatus } from "../../api/types";
import { isAbnormal } from "../insights/StatusMark";
import { FOCUS_3D, type OrganCode, type OrganStatus } from "./organs";

/**
 * The rice-paper body on the lacquer stage (docs/12 §5.3, ADR-0006): a translucent paper figure with gold ink
 * contours, and organ systems tinted with their worst status. Abnormal organs breathe slowly; choosing one flies
 * the camera to it (FR-27, FR-28). The figure is built from primitives, so it costs no download and runs on
 * integrated graphics; the organ IDs match `organ_system.mesh_ids` for a later anatomical model.
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

export default function Body3D({ statuses, selected, onSelect, reducedMotion }: {
  statuses: OrganStatus;
  selected: OrganCode | null;
  onSelect: (code: OrganCode) => void;
  reducedMotion: boolean;
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
      <Organs statuses={statuses} selected={selected} onSelect={onSelect} reducedMotion={reducedMotion} />
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
    float alpha = 0.05 + rim * 0.6 + line * 0.09 * (1.0 - rim);
    gl_FragColor = vec4(colour, alpha);
  }
`;

type Vec3 = [number, number, number];

function PaperBody() {
  const material = useMemo(() => new THREE.ShaderMaterial({
    uniforms: { uPaper: { value: new THREE.Color(STAGE.paper) }, uInk: { value: new THREE.Color(STAGE.gold) } },
    vertexShader: PAPER_VERTEX,
    fragmentShader: PAPER_FRAGMENT,
    transparent: true,
    depthWrite: false,
  }), []);

  const torso = useMemo(() => {
    const profile: [number, number][] = [
      [0.0, 0.84], [0.12, 0.845], [0.155, 0.88], [0.165, 0.95], [0.15, 1.03], [0.14, 1.1], [0.15, 1.18],
      [0.17, 1.27], [0.18, 1.35], [0.185, 1.41], [0.15, 1.45], [0.07, 1.47], [0.05, 1.48],
    ];
    const g = new THREE.LatheGeometry(profile.map(([r, y]) => new THREE.Vector2(r, y)), 48);
    g.scale(1, 1, 0.62);
    return g;
  }, []);

  const sides = [-1, 1];
  return (
    <group>
      <mesh geometry={torso} material={material} />
      <mesh position={[0, 1.52, 0]} material={material}>
        <cylinderGeometry args={[0.045, 0.05, 0.1, 24]} />
      </mesh>
      <mesh position={[0, 1.63, 0]} scale={[0.085, 0.11, 0.095]} material={material}>
        <sphereGeometry args={[1, 32, 24]} />
      </mesh>
      {sides.map((s) => (
        <group key={s}>
          <Limb from={[0.2 * s, 1.41, 0]} to={[0.25 * s, 1.13, -0.01]} radius={0.042} material={material} />
          <Limb from={[0.25 * s, 1.13, -0.01]} to={[0.28 * s, 0.88, 0.02]} radius={0.035} material={material} />
          <mesh position={[0.29 * s, 0.82, 0.02]} scale={[0.03, 0.06, 0.02]} material={material}>
            <sphereGeometry args={[1, 16, 12]} />
          </mesh>
          <Limb from={[0.085 * s, 0.86, 0]} to={[0.095 * s, 0.48, 0.01]} radius={0.065} material={material} />
          <Limb from={[0.095 * s, 0.48, 0.01]} to={[0.1 * s, 0.1, 0]} radius={0.048} material={material} />
          <mesh position={[0.1 * s, 0.04, 0.05]} scale={[0.04, 0.03, 0.09]} material={material}>
            <sphereGeometry args={[1, 16, 12]} />
          </mesh>
        </group>
      ))}
    </group>
  );
}

/** A capsule from one point to another. */
function Limb({ from, to, radius, material }: { from: Vec3; to: Vec3; radius: number; material: THREE.Material }) {
  const key = `${from}|${to}`; // the arrays are written inline, so compare by value
  const { position, quaternion, length } = useMemo(() => {
    const a = new THREE.Vector3(...from);
    const b = new THREE.Vector3(...to);
    const dir = b.clone().sub(a);
    return {
      position: a.clone().add(b).multiplyScalar(0.5),
      quaternion: new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize()),
      length: dir.length(),
    };
  }, [key]);
  return (
    <mesh position={position} quaternion={quaternion} material={material}>
      <capsuleGeometry args={[radius, length, 6, 16]} />
    </mesh>
  );
}

function Tube({ points, radius, material }: { points: Vec3[]; radius: number; material: THREE.Material }) {
  const key = points.join("|");
  const geometry = useMemo(
    () => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points.map((p) => new THREE.Vector3(...p))), 48, radius, 8),
    [key, radius],
  );
  useEffect(() => () => geometry.dispose(), [geometry]);
  return <mesh geometry={geometry} material={material} />;
}

// --- Organ systems --------------------------------------------------------------------------------------------------

function Organs({ statuses, selected, onSelect, reducedMotion }: {
  statuses: OrganStatus;
  selected: OrganCode | null;
  onSelect: (code: OrganCode) => void;
  reducedMotion: boolean;
}) {
  const props = (code: OrganCode) => ({ code, status: statuses[code], selected: selected === code, onSelect, reducedMotion });
  const sides = [-1, 1];
  return (
    <>
      <OrganSystem {...props("bone")}>
        {(m) => (
          <>
            {sides.map((s) => (
              <group key={s}>
                <Limb from={[0.088 * s, 0.84, -0.005]} to={[0.097 * s, 0.51, 0.005]} radius={0.017} material={m} />
                <mesh position={[0.097 * s, 0.48, 0.02]} material={m}><sphereGeometry args={[0.026, 16, 12]} /></mesh>
              </group>
            ))}
            {Array.from({ length: 14 }, (_, i) => (
              <mesh key={i} position={[0, 0.95 + i * 0.036, -0.075]} material={m}>
                <boxGeometry args={[0.03, 0.022, 0.026]} />
              </mesh>
            ))}
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
            {sides.map((s) => (
              <group key={s}>
                <Tube material={m} radius={0.006} points={[
                  [0, 0.95, -0.02], [0.06 * s, 0.86, 0.01], [0.09 * s, 0.6, 0.02], [0.1 * s, 0.3, 0.01], [0.1 * s, 0.08, 0.01],
                ]} />
                <Tube material={m} radius={0.005} points={[
                  [0.01 * s, 1.41, 0.01], [0.12 * s, 1.43, 0], [0.21 * s, 1.38, 0.01], [0.25 * s, 1.13, 0.01],
                  [0.28 * s, 0.9, 0.03],
                ]} />
                <Tube material={m} radius={0.004} points={[[0.015 * s, 1.41, 0.02], [0.025 * s, 1.5, 0.03], [0.03 * s, 1.6, 0.02]]} />
              </group>
            ))}
          </>
        )}
      </OrganSystem>

      <OrganSystem {...props("kidney")}>
        {(m) => sides.map((s) => (
          <mesh key={s} position={[0.07 * s, 1.07, -0.05]} rotation={[0, 0, 0.25 * s]} scale={[0.033, 0.055, 0.028]} material={m}>
            <sphereGeometry args={[1, 24, 16]} />
          </mesh>
        ))}
      </OrganSystem>

      <OrganSystem {...props("liver")}>
        {(m) => (
          <mesh position={[-0.05, 1.2, 0.04]} rotation={[0, 0, 0.18]} scale={[0.11, 0.055, 0.07]} material={m}>
            <sphereGeometry args={[1, 32, 20]} />
          </mesh>
        )}
      </OrganSystem>

      <OrganSystem {...props("pancreas")}>
        {(m) => <Limb from={[-0.03, 1.1, 0.03]} to={[0.1, 1.14, 0.0]} radius={0.017} material={m} />}
      </OrganSystem>

      <OrganSystem {...props("immune")}>
        {(m) => (
          <>
            <mesh position={[0.11, 1.19, -0.02]} rotation={[0, 0, -0.3]} scale={[0.028, 0.048, 0.028]} material={m}>
              <sphereGeometry args={[1, 20, 14]} />
            </mesh>
            {([[0.14, 1.36, 0.01], [0.08, 0.89, 0.05], [0.035, 1.47, 0.03]] as Vec3[]).flatMap(([x, y, z]) =>
              sides.map((s) => (
                <mesh key={`${x}${y}${s}`} position={[x * s, y, z]} material={m}><sphereGeometry args={[0.012, 12, 8]} /></mesh>
              )))}
          </>
        )}
      </OrganSystem>

      <OrganSystem {...props("heart")}>
        {(m) => (
          <mesh position={[0.03, 1.33, 0.05]} rotation={[0.2, 0, -0.45]} scale={[0.05, 0.062, 0.045]} material={m}>
            <sphereGeometry args={[1, 32, 20]} />
          </mesh>
        )}
      </OrganSystem>

      <OrganSystem {...props("thyroid")}>
        {(m) => (
          <>
            {sides.map((s) => (
              <mesh key={s} position={[0.018 * s, 1.49, 0.04]} scale={[0.013, 0.022, 0.011]} material={m}>
                <sphereGeometry args={[1, 16, 12]} />
              </mesh>
            ))}
            <mesh position={[0, 1.485, 0.045]} material={m}><boxGeometry args={[0.022, 0.008, 0.008]} /></mesh>
          </>
        )}
      </OrganSystem>

      <OrganSystem {...props("urinary")}>
        {(m) => (
          <>
            <mesh position={[0, 0.92, 0.06]} scale={[0.04, 0.032, 0.036]} material={m}><sphereGeometry args={[1, 24, 16]} /></mesh>
            {sides.map((s) => (
              <Tube key={s} material={m} radius={0.003} points={[[0.065 * s, 1.03, -0.05], [0.04 * s, 0.98, 0], [0.015 * s, 0.93, 0.05]]} />
            ))}
          </>
        )}
      </OrganSystem>

      {statuses.prostate && (
        <OrganSystem {...props("prostate")}>
          {(m) => <mesh position={[0, 0.875, 0.04]} material={m}><sphereGeometry args={[0.018, 16, 12]} /></mesh>}
        </OrganSystem>
      )}
    </>
  );
}

/** One organ system: its material follows the status; abnormal systems breathe, the chosen one glows. */
function OrganSystem({ code, status, selected, onSelect, reducedMotion, children }: {
  code: OrganCode;
  status?: ObsStatus;
  selected: boolean;
  onSelect: (code: OrganCode) => void;
  reducedMotion: boolean;
  children: (material: THREE.MeshStandardMaterial) => ReactNode;
}) {
  const [hovered, setHovered] = useState(false);
  const material = useMemo(() => new THREE.MeshStandardMaterial({ roughness: 0.5, transparent: true }), []);
  const hasData = Boolean(status);

  useEffect(() => {
    const colour = new THREE.Color(colourFor(status));
    material.color.copy(colour);
    material.emissive.copy(colour);
    material.opacity = hasData ? 0.95 : 0.2;
    material.depthWrite = hasData;
  }, [material, status, hasData]);

  useEffect(() => {
    document.body.style.cursor = hovered && hasData ? "pointer" : "";
    return () => {
      document.body.style.cursor = "";
    };
  }, [hovered, hasData]);

  const abnormal = Boolean(status && isAbnormal(status));
  useFrame(({ clock, invalidate }) => {
    const base = !hasData ? 0.02 : selected ? 0.85 : 0.3;
    const breath = abnormal && !reducedMotion ? 0.35 * (0.5 + 0.5 * Math.sin(clock.elapsedTime * 2.2)) : 0;
    const next = base + breath + (hovered && hasData ? 0.25 : 0);
    if (Math.abs(material.emissiveIntensity - next) > 0.001) {
      material.emissiveIntensity = next;
      invalidate();
    }
  });

  const click = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation();
    if (hasData) onSelect(code);
  };
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
    </group>
  );
}
