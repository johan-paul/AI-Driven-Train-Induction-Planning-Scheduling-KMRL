// src/pages/ConfigPage.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { postJSON, uploadFile } from "../api"; // make sure src/api.js exports these

function ConfigPage() {
  const navigate = useNavigate();
  const [useML, setUseML] = useState(false);
  const [forcedFails, setForcedFails] = useState([]); // selected train ids
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);
  const [mode, setMode] = useState("mock");

  // Slider states
  const [serviceCount, setServiceCount] = useState(8);
  const [lambda, setLambda] = useState(0.35);

  const allTrains = [
    "T11","T12","T13","T14","T15","T16","T17","T18",
    "T21","T22","T23","T24","T25","T26","T27","T28","T29","T30",
    "T31","T32","T33","T34","T35","T36","T37"
  ];

  const handleRun = async () => {
    setLoading(true);

    try {
      // 1) If CSV uploaded, upload it (backend will save snapshots)
      if (file) {
        // uploadFile handles FormData and proper headers
        await uploadFile("/ingest/upload_csv", file);
      } else {
        // 1b) If not uploading, call ingest/auto?mode=... to make snapshot (mock/pull/mqtt/uns)
        // For pull/mqtt you can extend cfg here; keep simple for now
        try {
          await postJSON(`/ingest/auto?mode=${encodeURIComponent(mode)}`, {});
        } catch (e) {
          // non-fatal: some backends may return 4xx when ingest not supported; still attempt run_induction
          console.warn("ingest/auto failed (continuing):", e);
        }
      }

      // 2) Build run_induction payload using backend key names
      const payload = {
        service_count: Number(serviceCount),
        lambda_risk: Number(lambda),
        use_ml: Boolean(useML),
        forced_failed_ids: Array.isArray(forcedFails) ? forcedFails : []
      };

      // 3) Call /run_induction
      const resp = await postJSON("/run_induction", payload);

      // Example resp: { summary: {...}, results: [...] }
      // Save to localStorage so DashboardPage loads it immediately
      try {
        window.localStorage.setItem("latest_plan", JSON.stringify({ fetched_at: Date.now(), plan_id: resp.plan_id ?? null, results: resp.results ?? resp.results ?? [] , summary: resp.summary ?? null }));
      } catch (e) {
        console.warn("Could not write latest_plan to localStorage:", e);
      }

      // 4) route to dashboard
      navigate("/dashboard");
    } catch (err) {
      console.error("Run induction failed, falling back to dashboard with mock:", err);
      // still navigate so user sees UI; dashboard will fall back to mock data if needed
      navigate("/dashboard");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-gradient-to-br from-[#0b0f14] via-[#1a103d] to-[#0b0f14] text-white font-sans">
      {/* Glow effects */}
      <div className="absolute w-96 h-96 bg-purple-700/30 rounded-full blur-3xl top-0 left-0 animate-pulse" />
      <div className="absolute w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-3xl bottom-0 right-0 animate-pulse" />

      <div className="relative backdrop-blur-xl bg-white/10 border border-white/20 rounded-2xl shadow-2xl max-w-6xl w-full grid grid-cols-2 gap-10 p-12">
        {/* Left Column */}
        <div className="flex flex-col">
          <h2 className="text-3xl font-bold mb-10 text-center drop-shadow-lg">
            🚆 KMRL Induction Config
          </h2>

          <div className="space-y-6 w-full">
            <label className="block text-gray-200">
              Service rakes required (SERVICE_COUNT): {serviceCount}
              <input
                type="range"
                min="1"
                max="40"
                value={serviceCount}
                onChange={(e) => setServiceCount(Number(e.target.value))}
                className="w-full accent-purple-500 mt-2"
              />
            </label>

            <label className="block text-gray-200">
              λ (risk weight in composite): {lambda.toFixed(2)}
              <input
                type="range"
                min="0"
                max="5"
                step="0.01"
                value={lambda}
                onChange={(e) => setLambda(Number(e.target.value))}
                className="w-full accent-purple-500 mt-2"
              />
            </label>

            <label className="block text-gray-200">
              Upload CSV (optional)
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files && e.target.files[0] ? e.target.files[0] : null)}
                className="w-full mt-2 p-2 rounded bg-black/30 border border-white/20"
              />
            </label>

            <label className="block text-gray-200">
              Mode Selection
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full mt-2 p-2 rounded bg-black/30 border border-white/20"
              >
                <option value="mock">mock</option>
                <option value="pull">pull</option>
                <option value="mqtt">mqtt</option>
                <option value="uns">uns</option>
              </select>
            </label>

            <div className="flex items-center gap-2 mt-4">
              <input
                type="checkbox"
                checked={useML}
                onChange={() => setUseML(!useML)}
                className="accent-purple-500"
              />
              <span className="text-gray-200">Use ML predictor for pred_fail</span>
            </div>

            <div>
              <label className="block mb-2 text-gray-200">Force-fail trains</label>
              <div className="max-h-32 overflow-y-auto bg-black/30 rounded-lg p-3 text-sm border border-white/20 space-y-2">
                {allTrains.map((t) => (
                  <label key={t} className="flex items-center gap-3 text-gray-300">
                    <input
                      type="checkbox"
                      checked={forcedFails.includes(t)}
                      onChange={() =>
                        setForcedFails((prev) =>
                          prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]
                        )
                      }
                      className="accent-red-500"
                    />
                    {t}
                  </label>
                ))}
              </div>
            </div>
          </div>

          <button
            onClick={handleRun}
            disabled={loading}
            className="w-full mt-10 py-3 rounded-lg bg-purple-600 hover:bg-purple-700 transition shadow-lg shadow-purple-500/40 text-white font-semibold text-lg"
          >
            {loading ? "⏳ Running..." : "🚀 Run Induction"}
          </button>

          {loading && (
            <div className="flex justify-center mt-4">
              <div className="w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
            </div>
          )}
        </div>

        {/* Right Column - Train Image */}
        <div className="flex items-center justify-center">
          <img
            src="/images/train.png"
            alt="3D Train"
            className="w-full max-w-md object-contain drop-shadow-2xl animate-fadeIn"
          />
        </div>
      </div>
    </div>
  );
}

export default ConfigPage;
