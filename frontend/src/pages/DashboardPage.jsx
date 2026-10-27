// src/pages/DashboardPage.jsx
import React, { useEffect, useState } from "react";
import Stats from "../components/Stats";
import TrainGroups from "../components/TrainGroups";
import InductionTable from "../components/InductionTable";
import TrainModel from "../components/TrainModel";
import AdvertiserSummary from "../components/AdvertiserSummary";
import TrainDetailsModal from "../components/TrainDetailsModal";
import { getJSON } from "../api"; // uses VITE_API_BASE and VITE_API_KEY

const MOCK = {
  stats: { total: 6, deploy: 2, standby: 2, ibl: 2 },
  groups: [
    { name: "Deploy", color: "#5cffb6", trains: [] },
    { name: "Standby", color: "#ffd166", trains: [] },
    { name: "IBL", color: "#ff6b6b", trains: [] },
  ],
  rows: [],
};

function adaptRows(rows = []) {
  return rows.map((r) => {
    const train_id = r.train_id ?? r.id ?? r.trainId ?? "-";
    const duty = r.duty ?? r.Duty ?? "-";
    const rank = r.rank ?? r.Rank ?? null;
    const pred_fail = r.pred_fail ?? r.predFail ?? 0;
    const odometer_km = r.odometer_km ?? r.km ?? r.odometer ?? null;
    const branding_req_train = r.branding_req_train ?? r.branding_req_hours ?? r.brandReq ?? 0;
    const branding_done = r.branding_done ?? r.brandDone ?? 0;
    const branding_shortfall =
      r.branding_shortfall ?? r.brandShortfall ?? Math.max(0, branding_req_train - branding_done);
    const advertiser = r.advertiser ?? r.advert ?? null;
    const alloc = r.alloc ?? 0;
    const last_clean_days = r.last_clean_days ?? r.lastClean ?? null;
    const stabling_index = r.stabling_index ?? r.stablingIdx ?? null;
    const decision_reasons = r.decision_reasons ?? r.reasons ?? [];

    return {
      // Backend-style (snake_case) for InductionTable
      train_id,
      duty,
      rank,
      pred_fail,
      odometer_km,
      branding_req_train,
      branding_done,
      branding_shortfall,
      advertiser,
      alloc,
      last_clean_days,
      stabling_index,
      decision_reasons,

      // UI-friendly aliases for TrainGroups / TrainCard
      id: train_id,
      predFail: pred_fail,
      km: odometer_km,
      brandReq: branding_req_train,
      brandDone: branding_done,
      brandShortfall: branding_shortfall,
      lastClean: last_clean_days,
      stablingIdx: stabling_index,
      reasons: Array.isArray(decision_reasons)
        ? decision_reasons
        : decision_reasons
        ? [decision_reasons]
        : [],
    };
  });
}


function groupByDuty(adaptedRows) {
  const dutyMap = {};
  adaptedRows.forEach((r) => {
    const key = (r.duty || "Standby");
    if (!dutyMap[key]) dutyMap[key] = [];
    dutyMap[key].push(r);
  });
  const groups = [
    { name: "Deploy", color: "#5cffb6", trains: dutyMap["Deploy"] ?? dutyMap["deploy"] ?? [] },
    { name: "Standby", color: "#ffd166", trains: dutyMap["Standby"] ?? dutyMap["standby"] ?? [] },
    { name: "IBL", color: "#ff6b6b", trains: dutyMap["IBL"] ?? dutyMap["ibl"] ?? [] },
  ];
  return groups;
}

function buildAdvertiserSummary(adaptedRows) {
  const map = {};
  adaptedRows.forEach((r) => {
    if (!r.advertiser) return;
    const name = String(r.advertiser);
    if (!map[name]) map[name] = { name, req: 0, done: 0 };
    map[name].req += Number(r.branding_req_train || 0);
    map[name].done += Number(r.branding_done || 0);
  });
  return Object.values(map);
}

export default function DashboardPage() {
  const [rows, setRows] = useState([]);
  const [groups, setGroups] = useState(MOCK.groups);
  const [stats, setStats] = useState(MOCK.stats);
  const [advertisers, setAdvertisers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrain, setSelectedTrain] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setError(null);

      try {
        const local = window.localStorage.getItem("latest_plan");
        if (local) {
          try {
            const obj = JSON.parse(local);
            if (obj && Array.isArray(obj.results)) {
              const adapted = adaptRows(obj.results);
              if (!mounted) return;
              setRows(adapted);
              setGroups(groupByDuty(adapted));
              setAdvertisers(buildAdvertiserSummary(adapted));
              setStats({
                total: adapted.length,
                deploy: adapted.filter(r => (r.duty||"").toLowerCase() === "deploy").length,
                standby: adapted.filter(r => (r.duty||"").toLowerCase() === "standby").length,
                ibl: adapted.filter(r => (r.duty||"").toLowerCase() === "ibl").length,
              });
              setLoading(false);
              return;
            }
          } catch (e) {
            console.warn("Invalid local latest_plan, ignoring", e);
          }
        }

        const plans = await getJSON("/plans");
        if (!mounted) return;

        if (Array.isArray(plans) && plans.length > 0) {
          let planId = plans[0].id;
          try {
            const sorted = plans.slice().sort((a,b) => {
              const ta = a.timestamp ? new Date(a.timestamp).getTime() : 0;
              const tb = b.timestamp ? new Date(b.timestamp).getTime() : 0;
              return tb - ta;
            });
            planId = sorted[0].id;
          } catch (e) {
            planId = plans[0].id;
          }

          try {
            const planDetail = await getJSON(`/plans/${encodeURIComponent(planId)}`);
            const planRows = Array.isArray(planDetail.plan) ? planDetail.plan : (planDetail.plan_json ?? []);
            const adapted = adaptRows(planRows);
            if (!mounted) return;
            setRows(adapted);
            setGroups(groupByDuty(adapted));
            setAdvertisers(buildAdvertiserSummary(adapted));
            setStats({
              total: adapted.length,
              deploy: adapted.filter(r => (r.duty||"").toLowerCase() === "deploy").length,
              standby: adapted.filter(r => (r.duty||"").toLowerCase() === "standby").length,
              ibl: adapted.filter(r => (r.duty||"").toLowerCase() === "ibl").length,
            });
            try { window.localStorage.setItem("latest_plan", JSON.stringify({ fetched_at: Date.now(), plan_id: planId, results: planRows })); } catch(e){}
            setLoading(false);
            return;
          } catch (errPlanFetch) {
            console.warn("Failed to fetch plan detail (maybe requires API key):", errPlanFetch);
          }
        }

        try {
          const snap = await getJSON("/snapshots/latest");
          if (!mounted) return;
          if (Array.isArray(snap) && snap.length > 0) {
            const adapted = adaptRows(snap);
            setRows(adapted);
            setGroups(groupByDuty(adapted));
            setAdvertisers(buildAdvertiserSummary(adapted));
            setStats({
              total: adapted.length,
              deploy: adapted.filter(r => (r.duty||"").toLowerCase() === "deploy").length,
              standby: adapted.filter(r => (r.duty||"").toLowerCase() === "standby").length,
              ibl: adapted.filter(r => (r.duty||"").toLowerCase() === "ibl").length,
            });
            setLoading(false);
            return;
          }
        } catch (errSnap) {
          console.warn("Failed to fetch snapshots/latest:", errSnap);
        }

        setRows(MOCK.rows);
        setGroups(MOCK.groups);
        setAdvertisers([]);
        setStats(MOCK.stats);
        setLoading(false);
      } catch (err) {
        console.error("Dashboard load failed:", err);
        setError(String(err));
        setRows(MOCK.rows);
        setGroups(MOCK.groups);
        setAdvertisers([]);
        setStats(MOCK.stats);
        setLoading(false);
      }
    }

    load();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="min-h-screen bg-[#0b0f14] text-[#ecf3ff] font-sans p-8 space-y-8">
      <h2 className="text-2xl font-bold mb-4 text-center text-purple-400 drop-shadow-md">
        🚆 Train Summary (Compact View)
      </h2>

      <div className="backdrop-blur-lg bg-white/10 border border-purple-400/30 rounded-2xl shadow-xl p-6">
        <TrainModel
          deploy={groups.find(g => g.name.toLowerCase() === "deploy")?.trains.map(t => t.train_id) ?? []}
          standby={groups.find(g => g.name.toLowerCase() === "standby")?.trains.map(t => t.train_id) ?? []}
          ibl={groups.find(g => g.name.toLowerCase() === "ibl")?.trains.map(t => t.train_id) ?? []}
        />
      </div>

      <div className="backdrop-blur-lg bg-white/10 border border-purple-400/30 rounded-2xl shadow-xl p-6">
        <Stats stats={stats} />
      </div>

      <div className="backdrop-blur-lg bg-white/10 border border-purple-400/30 rounded-2xl shadow-xl p-6">
        <AdvertiserSummary advertisers={advertisers} />
      </div>

      {loading ? (
        <div className="backdrop-blur-lg bg-white/10 border border-purple-400/30 rounded-2xl shadow-xl p-6 flex items-center">
          <div className="relative mr-6">
            <div className="w-12 h-12 border-4 border-purple-500 border-t-transparent rounded-full animate-spin"></div>
            <div
              className="w-12 h-12 border-4 border-purple-300 border-t-transparent rounded-full absolute top-0 left-0 animate-spin"
              style={{ animationDirection: "reverse", animationDuration: "0.8s" }}
            />
          </div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold mb-1 text-purple-300">Fetching Data...</h2>
            <div className="w-full bg-gray-700 rounded-full h-2.5">
              <div className="bg-purple-500 h-2.5 rounded-full animate-pulse" style={{ width: "70%" }} />
            </div>
            <p className="text-sm text-gray-400 mt-1">Loading latest plan / snapshot from backend...</p>
            {error && <p className="text-sm text-red-400 mt-2">Error: {error}</p>}
          </div>
        </div>
      ) : (
        <>
          <div className="backdrop-blur-lg bg-white/10 border border-purple-400/30 rounded-2xl shadow-xl p-6">
            <TrainGroups groups={groups} />
          </div>

          <div className="backdrop-blur-lg bg-white/10 border border-purple-400/30 rounded-2xl shadow-xl p-6">
            <InductionTable rows={rows} />
          </div>
        </>
      )}

      {selectedTrain && <TrainDetailsModal train={selectedTrain} onClose={() => setSelectedTrain(null)} />}
    </div>
  );
}
