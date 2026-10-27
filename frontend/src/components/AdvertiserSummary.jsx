// src/components/AdvertiserSummary.jsx
import React from "react";

/**
 * Simple single-horizontal bar advertiser summary.
 * Each advertiser shows: pill label, hours done/req above, single bar, % label below.
 *
 * Accepts items with flexible shapes coming from backend:
 *  - name or advertiser
 *  - req, display_required, advertiser_total_required
 *  - done, advertiser_total_done
 *  - pct (optional precomputed percent 0..1 or 0..100)
 */
export default function AdvertiserSummary({ advertisers = [] }) {
  if (!Array.isArray(advertisers) || advertisers.length === 0) {
    return (
      <div className="bg-[#141a24] p-4 rounded-lg shadow-md mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">📊 Advertiser Summary</h2>
        <div className="text-sm text-gray-400">No advertisers to display</div>
      </div>
    );
  }

  return (
    <div className="bg-[#141a24] p-4 rounded-lg shadow-md mb-6">
      <h2 className="text-lg font-semibold mb-4 flex items-center">📊 Advertiser Summary</h2>

      <div className="space-y-4">
        {advertisers.map((a, idx) => {
          // flexible name field
          const name = a.name ?? a.advertiser ?? `Advertiser ${idx + 1}`;

          // flexible done/req fields
          const doneRaw = a.done ?? a.advertiser_total_done ?? a.total_done ?? 0;
          const reqRaw =
            a.req ??
            a.display_required ??
            a.display_req ??
            a.advertiser_total_required ??
            a.total_required ??
            0;

          // numeric sanitization
          const done = Number.isFinite(Number(doneRaw)) ? Number(doneRaw) : 0;
          const req = Number.isFinite(Number(reqRaw)) ? Number(reqRaw) : 0;

          // percent: allow backend to pass pct (0..1 or 0..100)
          let percent = null;
          if (a.pct !== undefined && a.pct !== null) {
            const p = Number(a.pct);
            if (!Number.isNaN(p)) percent = p > 1 ? Math.round(p) : Math.round(p * 100);
          } else {
            percent = req > 0 ? Math.round((done / req) * 100) : 0;
          }
          if (!Number.isFinite(percent) || percent < 0) percent = 0;
          if (percent > 100) percent = 100;

          // small accessibility: aria and title
          const pctTitle = `${percent}% complete — ${done}/${req} hrs`;

          return (
            <div key={name + "_" + idx}>
              <div className="flex items-center justify-between mb-1">
                <span
                  className="px-3 py-1 text-sm font-medium bg-green-700 rounded-full"
                  title={name}
                >
                  {name}
                </span>
                <span className="text-sm text-gray-400">
                  {done}/{req} hrs
                </span>
              </div>

              <div
                className="w-full bg-gray-700 rounded-full h-3"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={percent}
                aria-label={`${name} progress`}
                title={pctTitle}
              >
                <div
                  className="h-3 rounded-full"
                  style={{ width: `${percent}%`, background: "#3b82f6" }}
                />
              </div>

              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>{percent}% complete</span>
                <span className="text-xs">{done} hrs</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
