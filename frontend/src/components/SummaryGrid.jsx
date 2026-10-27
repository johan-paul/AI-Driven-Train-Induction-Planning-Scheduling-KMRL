// src/components/SummaryGrid.jsx
import React from "react";

/**
 * SummaryGrid
 *
 * Props:
 *  - summary: object with arrays for deploy, standby, ibl (preferred)
 *      fallback keys supported: deployed, deploy, standby, ibl, IBL
 *  - maxTilesPerColumn: optional number to limit tiles shown and show "+N" indicator (default 12)
 *  - onTileClick: optional function(trainId) called when a tile is clicked
 */
const SummaryGrid = ({ summary = {}, maxTilesPerColumn = 12, onTileClick }) => {
  // normalize keys with fallbacks
  const deployArr = Array.isArray(summary.deploy)
    ? summary.deploy
    : Array.isArray(summary.deployed)
    ? summary.deployed
    : [];
  const standbyArr = Array.isArray(summary.standby)
    ? summary.standby
    : [];
  const iblArr = Array.isArray(summary.ibl)
    ? summary.ibl
    : Array.isArray(summary.IBL)
    ? summary.IBL
    : [];

  const renderTiles = (arr, colorClass, textColor, label) => {
    if (!Array.isArray(arr) || arr.length === 0) {
      return <div className="text-xs text-gray-400">—</div>;
    }

    const visible = arr.slice(0, maxTilesPerColumn);
    const hiddenCount = Math.max(0, arr.length - visible.length);

    return (
      <div className="grid grid-cols-2 gap-4">
        {visible.map((id) => (
          <button
            key={String(id)}
            type="button"
            onClick={() => typeof onTileClick === "function" ? onTileClick(id) : null}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                typeof onTileClick === "function" ? onTileClick(id) : null;
              }
            }}
            title={`${label} — ${id}`}
            aria-label={`${label} train ${id}`}
            className={`${colorClass} w-12 h-6 rounded-sm opacity-80 hover:opacity-100 transition-all duration-300 flex items-center justify-center text-xs ${textColor} font-bold focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-white/30`}
          >
            {id}
          </button>
        ))}

        {hiddenCount > 0 && (
          <div
            className="w-12 h-6 rounded-sm opacity-60 flex items-center justify-center text-xs text-gray-200 bg-black/30"
            title={`${hiddenCount} more`}
            aria-hidden="true"
          >
            +{hiddenCount}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="w-full h-[400px] mb-8 relative bg-[#0a0d12] rounded-lg overflow-hidden shadow-xl">
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative w-full h-full">
          {/* Labels */}
          <div className="absolute left-1/4 transform -translate-x-1/2 top-4 bg-black/50 px-4 py-1 rounded-md z-10">
            <span className="text-[#5cffb6] font-bold">Deploy</span>
          </div>
          <div className="absolute left-1/2 transform -translate-x-1/2 top-4 bg-black/50 px-4 py-1 rounded-md z-10">
            <span className="text-[#ffd166] font-bold">Standby</span>
          </div>
          <div className="absolute left-3/4 transform -translate-x-1/2 top-4 bg-black/50 px-4 py-1 rounded-md z-10">
            <span className="text-[#ff6b6b] font-bold">IBL</span>
          </div>

          {/* Grid */}
          <div className="grid grid-cols-3 h-full p-6">
            {/* Deploy */}
            <div className="flex flex-col items-center justify-center bg-[#0d1117]/50">
              {renderTiles(deployArr, "bg-[#5cffb6]", "text-black", "Deploy")}
            </div>

            {/* Standby */}
            <div className="flex flex-col items-center justify-center bg-[#0d1117]/30">
              {renderTiles(standbyArr, "bg-[#ffd166]", "text-black", "Standby")}
            </div>

            {/* IBL */}
            <div className="flex flex-col items-center justify-center bg-[#0d1117]/50">
              {renderTiles(iblArr, "bg-[#ff6b6b]", "text-black", "IBL")}
            </div>
          </div>
        </div>
      </div>

      {/* Hint */}
      <div className="absolute bottom-2 right-2 text-xs text-gray-400 bg-black/40 px-2 py-1 rounded">
        <span>Click a tile to view details</span>
      </div>
    </div>
  );
};

export default SummaryGrid;
