// src/components/TrainCard.jsx
import React from "react";

export default function TrainCard({ train = {}, color = "#4a90e2", onViewDetails }) {
  // normalize values
  const req = Number(train.brandReq ?? train.branding_req_train ?? 0);
  const done = Number(train.brandDone ?? train.branding_done ?? 0);
  const shortfall = Number(train.brandShortfall ?? 0);
  const pct = req > 0 ? Math.min(Math.round((done / req) * 100), 100) : 0; // clamp to 100

  // Pred fail formatting (3 decimals)
  const rawPred = train.predFail ?? train.pred_fail ?? train.pred ?? null;
  const predDisplay = (rawPred === null || rawPred === undefined || Number.isNaN(Number(rawPred)))
    ? "-"
    : Number(Number(rawPred)).toFixed(3);

  return (
    <div
      className="backdrop-blur-lg bg-white/5 border border-white/10 p-4 rounded-xl shadow-lg transition hover:shadow-purple-500/20"
      style={{ borderLeft: `4px solid ${color}` }}
    >
      {/* Header */}
      <div className="flex justify-between items-start">
        <h3 className="text-lg font-bold">{train.id ?? train.train_id}</h3>
        <span
          className="text-xs px-2 py-1 rounded-full"
          style={{ background: `${color}22`, color }}
        >
          Rank: {train.rank ?? "-"}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2 text-sm mt-3">
        <div>Pred. Fail: <span className="font-medium">{predDisplay}</span></div>
        <div>Km: <span className="font-medium">{train.km ?? "-"}</span></div>
        <div>Advertiser: <span className="font-medium">{train.advertiser ?? "-"}</span></div>

        {/* Removed: Brand shortfall line as requested */}

        <div>Stabling idx: <span className="font-medium">{train.stablingIdx ?? "-"}</span></div>
        <div>Last Clean: <span className="font-medium">{train.lastClean ?? "-"}</span></div>
      </div>

      {/* Branding Progress */}
      <div className="mt-3">
        <div className="flex justify-between text-xs text-gray-400 mb-1">
          <span>Brand req/done: {req}/{done} hrs</span>
          <span>{pct}%</span>
        </div>
        <div className="w-full bg-gray-700/50 rounded-full h-2">
          <div className="h-2 rounded-full" style={{ width: `${pct}%`, background: color }} />
        </div>
      </div>

      {/* Reasons & Details */}
      <details className="mt-3">
        <summary className="cursor-pointer text-sm font-medium text-gray-300">Reasons & details</summary>
        <div className="mt-2 pl-2 border-l-2 border-gray-700 text-sm text-gray-300 space-y-2">
          <ul className="list-disc list-inside space-y-1">
            {Array.isArray(train.reasons) && train.reasons.length > 0 ? (
              train.reasons.map((r, i) => <li key={i}>{r}</li>)
            ) : (
              <li>No details available</li>
            )}
          </ul>

          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              if (onViewDetails) onViewDetails(train);
            }}
            className="mt-2 px-3 py-1 bg-purple-600 hover:bg-purple-700 rounded-lg text-sm text-white font-semibold shadow-md transition"
          >
            View More
          </button>
        </div>
      </details>
    </div>
  );
}
