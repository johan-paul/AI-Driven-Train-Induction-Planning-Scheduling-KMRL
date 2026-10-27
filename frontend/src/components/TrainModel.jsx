// src/components/TrainModel.jsx
import React, { Suspense, useMemo, useRef, useEffect } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls, Float, Text, useGLTF } from "@react-three/drei";
import * as THREE from "three";

/**
 * CameraAnimator
 * Performs a short cinematic zoom then gentle orbital motion.
 * Cleans up requestAnimationFrame on unmount.
 */
function CameraAnimator() {
  const { camera } = useThree();
  const frame = useRef(0);
  const rafRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const animate = () => {
      if (!mounted) return;

      // initial cinematic zoom first ~60 frames (~1s at 60fps)
      if (frame.current < 60) {
        const progress = frame.current / 60;
        camera.position.z = 10 - progress * 4; // zoom 10 → 6
      } else {
        camera.position.z = 6;
      }

      // gentle lateral motion and slightly elevated camera
      camera.position.y = 2;
      camera.position.x = Math.sin(frame.current * 0.01) * 1.5;

      // look a bit above the origin for nicer composition
      camera.lookAt(0, 1, 0);

      frame.current += 1;
      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);

    return () => {
      mounted = false;
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [camera]);

  return null;
}

/**
 * TrainGLB
 * Loads a GLB, normalizes its scale and center once, then renders a float group.
 */
function TrainGLB({ url, label, color, position = [0, 0, 0], desiredSize = 1 }) {
  const gltf = useGLTF(url); // drei's useGLTF — Suspense wraps this

  const sceneClone = useMemo(() => {
    if (!gltf || !gltf.scene) return null;

    const clone = gltf.scene.clone(true);

    // compute bounding box
    const box = new THREE.Box3().setFromObject(clone);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 0.0001);
    const scale = desiredSize / maxDim;
    clone.scale.setScalar(scale);

    // recenter
    box.setFromObject(clone);
    const center = box.getCenter(new THREE.Vector3());
    clone.position.sub(center);

    return clone;
  }, [gltf, desiredSize]);

  if (!sceneClone) return null;

  return (
    <Float speed={0.8} rotationIntensity={0.03} floatIntensity={0.05}>
      <group position={position}>
        <primitive object={sceneClone} />
        <Text
          position={[0, -0.7, 0]}
          fontSize={0.2}
          color={color}
          anchorX="center"
          anchorY="top"
        >
          {label}
        </Text>
      </group>
    </Float>
  );
}

/**
 * Rail
 * Simple plane used as track visual
 */
function Rail({ length = 20, position = [0, -1, 0] }) {
  return (
    <mesh position={position} rotation={[-Math.PI / 2, 0, 0]}>
      <planeGeometry args={[length, 0.4]} />
      <meshStandardMaterial color="#555" metalness={0.8} roughness={0.4} />
    </mesh>
  );
}

/**
 * TrainModel - top-level component
 *
 * Props:
 *  - deploy, standby, ibl: arrays of train ids (strings)
 *  - modelPaths: { deploy, standby, ibl } urls (GLB)
 */
export default function TrainModel({
  deploy = [],
  standby = [],
  ibl = [],
  modelPaths = {
    deploy: "/models/train_deploy.glb",
    standby: "/models/train_standby.glb",
    ibl: "/models/train_ibl.glb",
  },
}) {
  const desiredSize = 1.0;
  const spacingX = 2.2;

  // simple fallback if arrays large — keeps scene manageable client-side
  const clampList = (arr) => (Array.isArray(arr) ? arr.slice(0, 12) : []);

  const deployList = clampList(deploy);
  const standbyList = clampList(standby);
  const iblList = clampList(ibl);

  return (
    <div className="bg-[#0a0d12] rounded-lg p-3 shadow-lg" style={{ height: 420 }}>
      <Canvas camera={{ position: [0, 2.5, 10], fov: 45 }}>
        {/* cinematic animator */}
        <CameraAnimator />

        {/* lights */}
        <ambientLight intensity={0.6} />
        <directionalLight position={[5, 8, 5]} intensity={1.2} />

        {/* controls */}
        <OrbitControls enableZoom enablePan={false} />

        <Suspense
          fallback={
            <group>
              <mesh>
                <boxGeometry args={[1, 1, 1]} />
                <meshStandardMaterial color="#333" />
              </mesh>
            </group>
          }
        >
          {/* Deploy row */}
          <Rail position={[0, -1, 2]} length={20} />
          {deployList.map((id, i) => (
            <TrainGLB
              key={`deploy-${id}`}
              url={modelPaths.deploy}
              label={id}
              color="#5cffb6"
              position={[i * spacingX - ((deployList.length - 1) * spacingX) / 2, 0, 2]}
              desiredSize={desiredSize}
            />
          ))}
          <Text position={[-11, 0.5, 2]} fontSize={0.4} color="#5cffb6" anchorX="left">
            Deploy
          </Text>

          {/* Standby row */}
          <Rail position={[0, -1, 0]} length={20} />
          {standbyList.map((id, i) => (
            <TrainGLB
              key={`standby-${id}`}
              url={modelPaths.standby}
              label={id}
              color="#ffd166"
              position={[i * spacingX - ((standbyList.length - 1) * spacingX) / 2, 0, 0]}
              desiredSize={desiredSize}
            />
          ))}
          <Text position={[-11, 0.5, 0]} fontSize={0.4} color="#ffd166" anchorX="left">
            Standby
          </Text>

          {/* IBL row */}
          <Rail position={[0, -1, -2]} length={20} />
          {iblList.map((id, i) => (
            <TrainGLB
              key={`ibl-${id}`}
              url={modelPaths.ibl}
              label={id}
              color="#ff6b6b"
              position={[i * spacingX - ((iblList.length - 1) * spacingX) / 2, 0, -2]}
              desiredSize={desiredSize}
            />
          ))}
          <Text position={[-11, 0.5, -2]} fontSize={0.4} color="#ff6b6b" anchorX="left">
            IBL
          </Text>
        </Suspense>
      </Canvas>
    </div>
  );
}
