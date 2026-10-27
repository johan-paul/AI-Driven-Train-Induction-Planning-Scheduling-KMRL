// src/components/InductionTable.jsx
import React from "react";

/**
 * InductionTable
 *
 * Props:
 *  - rows: array of records (backend shape preferred: train_id, duty, rank, pred_fail,
 *          odometer_km, branding_shortfall, last_clean_days, stabling_index, ...)
 *  - onRowClick: optional function(row) called when a row is clicked
 */
const InductionTable = ({ rows = [], onRowClick }) => {
  // helper to pick primary field with fallbacks
  const pick = (row, keys, fallback = null) => {
    for (const k of keys) {
      if (row && row[k] !== undefined && row[k] !== null) return row[k];
    }
    return fallback;
  };

  const safeNum = (v, decimals = null) => {
    if (v === undefined || v === null || v === "") return "-";
    const n = Number(v);
    if (!Number.isFinite(n)) return "-";
    return decimals === null ? n : n.toFixed(decimals);
  };

  const downloadCSV = () => {
    if (!Array.isArray(rows) || rows.length === 0) {
      // nothing to download
      return;
    }

    // define columns and header labels (backend-first names, friendly labels)
    const columns = [
      { key: "train_id", label: "Train ID" },
      { key: "advertiser", label: "Advertiser" },
      { key: "duty", label: "Duty" },
      { key: "rank", label: "Rank" },
      { key: "pred_fail", label: "Pred. Fail" },
      { key: "odometer_km", label: "Odometer (km)" },
      { key: "branding_shortfall", label: "Branding Shortfall (hrs)" },
      { key: "branding_req_train", label: "Req (train) (hrs)" },
      { key: "branding_req_hours", label: "Req (display) (hrs)" },
      { key: "branding_done", label: "Branding Done (hrs)" },
      { key: "alloc", label: "Alloc (hrs)" },
      { key: "last_clean_days", label: "Last Clean (days)" },
      { key: "stabling_index", label: "Stabling Idx" },
      { key: "decision_reasons", label: "Decision Reasons" },
    ];

    // build CSV with quoting and escaping
    const rowsCsv = rows.map((r) => {
      return columns
        .map((col) => {
          // fallback mapping for older prop names
          const raw =
            r[col.key] ??
            r[
              // older names map
              {
                train_id: "id",
                pred_fail: "predFail",
                odometer_km: "km",
                branding_shortfall: "brandShortfall",
                last_clean_days: "lastClean",
                stabling_index: "stablingIdx",
                branding_req_train: "brandingReqTrain",
                branding_req_hours: "brandingReqHours",
                branding_done: "brandingDone",
                alloc: "alloc",
                advertiser: "advertiser",
                rank: "rank",
                duty: "duty",
                decision_reasons: "decisionReasons",
              }[col.key]
            ];

          if (raw === undefined || raw === null) return '""';
          // if it's an object (e.g., decision_reasons JSON), stringify it
          const str = typeof raw === "object" ? JSON.stringify(raw) : String(raw);
          // escape double quotes by doubling them
          const escaped = str.replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(",");
    });

    const headerLine = columns.map((c) => `"${c.label.replace(/"/g, '""')}"`).join(",");
    const csvContent = [headerLine, ...rowsCsv].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "induction-plan.csv";
    // append to DOM to make click work in some browsers
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-[#141a24] p-4 rounded-lg shadow-md mb-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Full Induction Plan</h2>

        <button
          className="flex items-center space-x-2 py-2 px-4 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-md transition-colors duration-300"
          onClick={downloadCSV}
        >
          <span className="material-symbols-outlined">download</span>
          <span>Download Induction Plan CSV</span>
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-700">
          <thead className="bg-[#0d1117]">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Train ID
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Advertiser
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Duty
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Rank
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Pred. Fail
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Odometer (km)
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Branding Shortfall
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Last Clean (days)
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">
                Stabling Idx
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {Array.isArray(rows) && rows.length > 0 ? (
              rows.map((row, idx) => {
                const trainId = pick(row, ["train_id", "id"], "-");
                const advertiser = pick(row, ["advertiser"], "-");
                const duty = pick(row, ["duty"], "-");
                const rank = pick(row, ["rank"], "-");
                const predFail = pick(row, ["pred_fail", "predFail"], "-");
                const km = pick(row, ["odometer_km", "km"], "-");
                const brandShortfall = pick(row, ["branding_shortfall", "brandShortfall"], "-");
                const lastClean = pick(row, ["last_clean_days", "lastClean"], "-");
                const stablingIdx = pick(row, ["stabling_index", "stablingIdx"], "-");

                const rowBg =
                  duty === "Deploy"
                    ? "bg-[#5cffb6]/10"
                    : duty === "Standby"
                    ? "bg-[#ffd166]/10"
                    : "bg-[#ff6b6b]/10";

                return (
                  <tr
                    key={trainId + "_" + idx}
                    className={`hover:bg-[#1a212e] transition-colors duration-200 ${rowBg}`}
                    onClick={() => (typeof onRowClick === "function" ? onRowClick(row) : null)}
                    style={{ cursor: typeof onRowClick === "function" ? "pointer" : "default" }}
                  >
                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">{trainId}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{advertiser}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">
                      <span
                        className="px-2 py-1 rounded-full text-xs font-medium"
                        style={{
                          backgroundColor:
                            duty === "Deploy"
                              ? "#5cffb633"
                              : duty === "Standby"
                              ? "#ffd16633"
                              : "#ff6b6b33",
                          color: duty === "Deploy" ? "#5cffb6" : duty === "Standby" ? "#ffd166" : "#ff6b6b",
                        }}
                      >
                        {duty}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{safeNum(rank)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{safeNum(predFail, 3)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{safeNum(km)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{safeNum(brandShortfall)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{safeNum(lastClean)}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-sm">{safeNum(stablingIdx)}</td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td className="px-4 py-6 text-center text-sm text-gray-400" colSpan={9}>
                  No induction plan available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default InductionTable;
