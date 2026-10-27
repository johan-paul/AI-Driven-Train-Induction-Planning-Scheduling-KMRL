// src/components/ControlPanel.jsx
import React, { useState, useEffect } from "react";

/**
 * ControlPanel
 *
 * Props:
 *  - onRun(payload)         : function called when user clicks Run. Receives payload for backend.
 *  - loading (bool)         : whether a run is in progress (disables button / shows "Running...")
 *  - trainOptions (string[]) : optional array of train IDs to populate force-fail multi-select
 */
export default function ControlPanel({ onRun, loading = false, trainOptions = [] }) {
  const [serviceCount, setServiceCount] = useState(8);
  const [lambda, setLambda] = useState(0.35);
  const [mlPredictor, setMlPredictor] = useState(false);
  const [forceFail, setForceFail] = useState([]);

  // keep the internal select options in sync if trainOptions change
  useEffect(() => {
    // if previously selected forced IDs are no longer available, filter them out
    if (Array.isArray(trainOptions) && trainOptions.length > 0) {
      setForceFail((prev) => prev.filter((id) => trainOptions.includes(id)));
    }
  }, [trainOptions]);

  const handleSubmit = () => {
    // coerce numeric types (backend expects numbers)
    const payload = {
      service_count: Number.isFinite(Number(serviceCount)) ? parseInt(serviceCount, 10) : 8,
      lambda_risk: Number.isFinite(Number(lambda)) ? parseFloat(lambda) : 0.35,
      use_ml: Boolean(mlPredictor),
      forced_failed_ids: Array.isArray(forceFail) ? forceFail : []
    };
    if (typeof onRun === "function") onRun(payload);
  };

  return (
    <div className="bg-[#141a24] p-4 rounded-lg shadow-md mb-6">
      <h2 className="text-lg font-semibold mb-4">Control Panel</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Service rakes required (SERVICE_COUNT)</label>
            <input
              type="range"
              min="1"
              max="20"
              value={serviceCount}
              onChange={(e) => setServiceCount(Number(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>1</span>
              <span>{serviceCount}</span>
              <span>20</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">
              λ (risk weight in composite): <span className="font-semibold">{lambda}</span>
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={lambda}
              onChange={(e) => setLambda(Number(e.target.value))}
              className="w-full h-2 bg-gray-700 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>0.0</span>
              <span>0.5</span>
              <span>1.0</span>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center">
            <input
              id="ml-predictor"
              type="checkbox"
              checked={mlPredictor}
              onChange={() => setMlPredictor((s) => !s)}
              className="w-4 h-4 text-primary-600 bg-gray-700 border-gray-600 rounded"
            />
            <label htmlFor="ml-predictor" className="ml-2 text-sm font-medium">
              Use ML predictor to fill missing pred_fail
            </label>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">What-if: Force-fail trains (simulate breakdown)</label>
            <select
              multiple
              value={forceFail}
              onChange={(e) => setForceFail(Array.from(e.target.selectedOptions, (o) => o.value))}
              className="w-full bg-[#0b0f14] border border-gray-700 rounded-md p-2 text-sm"
              aria-label="Force-fail trains"
            >
              {Array.isArray(trainOptions) && trainOptions.length > 0 ? (
                trainOptions.map((tid) => (
                  <option key={tid} value={tid}>
                    {tid}
                  </option>
                ))
              ) : (
                // fallback sample options if none provided
                <>
                  <option value="T12">T12</option>
                  <option value="T14">T14</option>
                  <option value="T15">T15</option>
                  <option value="T17">T17</option>
                  <option value="T21">T21</option>
                  <option value="T23">T23</option>
                </>
              )}
            </select>
          </div>

          <button
            onClick={handleSubmit}
            disabled={loading}
            className={`mt-4 w-full py-2 px-4 ${
              loading ? "bg-gray-500 cursor-not-allowed" : "bg-primary-600 hover:bg-primary-700"
            } text-white font-semibold rounded-md transition-colors duration-300 transform hover:scale-[1.02]`}
            aria-busy={loading}
          >
            {loading ? "Running..." : "Run Induction (backend)"}
          </button>
        </div>
      </div>
    </div>
  );
}
