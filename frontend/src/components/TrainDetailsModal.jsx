// src/components/TrainDetailsModal.jsx
import React, { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import { OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";

function TrainModel3D({ duty }) {
  const gltfPath =
    duty === "Standby" ? "/models/train_standby.glb" :
    duty === "IBL" ? "/models/train_ibl.glb" :
    "/models/train_deploy.glb";

  const { scene } = useGLTF(gltfPath, true);
  const groupRef = useRef();

  useEffect(() => {
    if (!scene || !groupRef.current) return;
    const clone = scene.clone(true);

    const box = new THREE.Box3().setFromObject(clone);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z, 0.0001);
    const targetSize = 5.0; // 🔥 make model bigger
    const scale = targetSize / maxDim;
    clone.scale.setScalar(scale);

    box.setFromObject(clone);
    const center = box.getCenter(new THREE.Vector3());
    clone.position.sub(center);

    const group = groupRef.current;
    while (group.children.length) group.remove(group.children[0]);
    group.add(clone);
  }, [scene]);

  return (
    <>
      <group ref={groupRef} />
      <OrbitControls
        enablePan={false}
        enableZoom={true}
        autoRotate
        autoRotateSpeed={0.8}
      />
    </>
  );
}

export default function TrainDetailsModal({ train, onClose }) {
  const closeRef = useRef(null);
  if (!train) return null;

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    if (closeRef.current) closeRef.current.focus();

    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener("keydown", onKey);
    };
  }, [onClose]);

  const tid = train.train_id ?? train.id ?? "—";
  const predRaw = train.predFail ?? train.pred_fail ?? train.pred ?? null;
  const pred = (predRaw === null || predRaw === undefined || Number.isNaN(Number(predRaw)))
    ? "-"
    : Number(Number(predRaw)).toFixed(3);
  const km = train.km ?? train.odometer_km ?? "-";
  const advertiser = train.advertiser ?? "-";
  const brandDone = train.brandDone ?? 0;
  const brandReq = train.brandReq ?? 0;
  const reasons = Array.isArray(train.reasons) ? train.reasons : [];

  // pick bar color based on duty
  const duty = train.duty ?? "Deploy";
  const dutyColor =
    duty === "Standby" ? "#facc15" : // yellow-400
    duty === "IBL" ? "#ef4444" :    // red-500
    "#22c55e";                      // green-500 (Deploy default)

  const modal = (
    <div
      role="dialog"
      aria-modal="true"
      onClick={(e) => e.target === e.currentTarget && onClose()}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 99999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(2,6,23,0.64)",
        padding: 20,
      }}
    >
      <div
        style={{
          width: "min(980px, 96vw)",
          maxHeight: "92vh",
          overflowY: "auto",
          borderRadius: 16,
          padding: 20,
          background: "rgba(15, 20, 30, 0.54)",
          border: "1px solid rgba(255,255,255,0.05)",
          boxShadow: "0 20px 60px rgba(3,6,18,0.6)",
          backdropFilter: "blur(12px) saturate(120%)",
          WebkitBackdropFilter: "blur(12px) saturate(120%)",
          position: "relative",
        }}
      >
        {/* left accent bar (dynamic color) */}
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            bottom: 0,
            width: 6,
            borderTopLeftRadius: 16,
            borderBottomLeftRadius: 16,
            background: dutyColor,
          }}
        />

        {/* Close button */}
        <button
          ref={closeRef}
          onClick={onClose}
          style={{
            position: "absolute",
            right: 14,
            top: 12,
            background: "transparent",
            border: "none",
            color: "#cbd5e1",
            fontSize: 18,
            cursor: "pointer",
            padding: 8,
          }}
          aria-label="Close details"
        >
          ✕
        </button>

        <h2 style={{ marginBottom: 12, fontSize: 20, color: "#e9eefb" }}>
          🚆 Train {tid} — Details
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
          {/* Bigger 3D Viewer */}
          <div style={{ height: 400, borderRadius: 12, overflow: "hidden", background: "rgba(0,0,0,0.2)" }}>
            <Suspense fallback={<div className="flex items-center justify-center h-full">Loading 3D…</div>}>
              <Canvas camera={{ position: [0, 2, 12], fov: 55 }}>
                <ambientLight intensity={0.7} />
                <directionalLight position={[8, 10, 5]} intensity={1.0} />
                <TrainModel3D duty={duty} />
              </Canvas>
            </Suspense>
          </div>

          {/* Right details */}
          <div>
            <ul style={{ margin: 0, paddingLeft: 18, lineHeight: 1.9, color: "#c9e0ff" }}>
              <li><strong>Rank:</strong> {train.rank ?? "-"}</li>
              <li><strong>Failure Probability:</strong> {typeof pred === "number" ? Number(pred).toFixed(3) : pred}</li>
              <li><strong>Kilometers:</strong> {km}</li>
              <li><strong>Advertiser:</strong> {advertiser}</li>
              <li><strong>Stabling Index:</strong> {train.stablingIdx ?? "-"}</li>
              <li><strong>Last Cleaned:</strong> {train.lastClean ?? "-"}</li>
              <li><strong>Branding:</strong> {brandDone}/{brandReq} hrs</li>
            </ul>

            <div style={{ marginTop: 14 }}>
              <h4 style={{ margin: "8px 0", color: "#d6e4ff" }}>Reasons</h4>
              {reasons.length ? (
                <ul style={{ paddingLeft: 18, color: "#9fb0d9" }}>
                  {reasons.map((r, i) => <li key={i}>{String(r)}</li>)}
                </ul>
              ) : (
                <div style={{ color: "#9fb0d9" }}>No details available</div>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div style={{ marginTop: 20, textAlign: "right" }}>
          <button
            onClick={onClose}
            style={{
              padding: "8px 16px",
              background: "linear-gradient(90deg,#7c3aed,#a78bfa)",
              color: "#fff",
              border: "none",
              borderRadius: 10,
              cursor: "pointer",
              fontWeight: 600,
              boxShadow: "0 8px 30px rgba(124,58,237,0.18)"
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modal, document.body);
}
