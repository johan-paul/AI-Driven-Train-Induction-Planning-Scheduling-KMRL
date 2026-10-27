// src/components/Stats.jsx
import React from "react";

export default function Stats({ stats = {} }) {
  // map backend keys with fallbacks
  const total =
    stats.total ?? stats.total_trains ?? stats.Total ?? 0;
  const deploy =
    stats.deploy ?? stats.deployed ?? 0;
  const standby =
    stats.standby ?? stats.Standby ?? 0;
  const ibl =
    stats.ibl ?? stats.IBL ?? 0;

  return (
    <div className="grid grid-cols-4 gap-4 mb-6 bg-[#141a24] p-4 rounded-lg shadow-md">
      <div className="flex flex-col items-center justify-center">
        <span className="text-sm text-gray-400">Total Trains</span>
        <span className="text-2xl font-bold">{total}</span>
      </div>
      <div className="flex flex-col items-center justify-center">
        <span className="text-sm text-gray-400">Deploy</span>
        <span className="text-2xl font-bold text-[#5cffb6]">{deploy}</span>
      </div>
      <div className="flex flex-col items-center justify-center">
        <span className="text-sm text-gray-400">Standby</span>
        <span className="text-2xl font-bold text-[#ffd166]">{standby}</span>
      </div>
      <div className="flex flex-col items-center justify-center">
        <span className="text-sm text-gray-400">IBL</span>
        <span className="text-2xl font-bold text-[#ff6b6b]">{ibl}</span>
      </div>
    </div>
  );
}
