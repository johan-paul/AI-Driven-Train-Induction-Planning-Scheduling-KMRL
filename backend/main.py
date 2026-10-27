# backend/main.py
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Query, Body
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from . import models, crud, ingestion, utils
from .schemas import TrainSnapshotIn, RunInductionRequest, InductionResponse
import uvicorn
from typing import List, Any
from fastapi.encoders import jsonable_encoder
import math
import numpy as np
import pandas as pd
from datetime import datetime
from .auth import get_api_key
import os, json
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect


# create DB tables (if not already)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="KMRL Induction Backend")
# add near top of backend/main.py
from fastapi.middleware.cors import CORSMiddleware

# after `app = FastAPI(...)` add:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # your Vite dev origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ----------------------------
# Sanitizer helper
# ----------------------------
def _sanitize_value(v: Any):
    """Sanitize a single scalar/list/dict recursively for JSON responses and DB storage."""
    if v is None:
        return None
    if isinstance(v, (pd.Timestamp, pd.Timedelta, datetime)):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if not np.isfinite(v):
            return None
        return float(v)
    if isinstance(v, (np.bool_, bool)):
        return bool(v)
    if isinstance(v, (np.ndarray,)):
        return [_sanitize_value(x) for x in v.tolist()]
    if isinstance(v, (list, tuple)):
        return [_sanitize_value(x) for x in v]
    if isinstance(v, dict):
        return {str(k): _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, float):
        if not math.isfinite(v):
            return None
        return float(v)
    if isinstance(v, (int, str, bool)):
        return v
    try:
        return jsonable_encoder(v)
    except Exception:
        return str(v)

# ----------------------------
# Endpoints for ingest / snapshots
# ----------------------------
# existing code above...
@app.post("/ingest/auto")
def ingest_auto(db: Session = Depends(get_db), mode: str = Query("mock"), cfg: dict = Body(None)):
    """
    Ingest auto snapshot.
    Query param mode: "mock" (default) | "pull" | "mqtt" | "uns"
    When mode == "pull", supply cfg like {"endpoint":"https://iot.example/api/snapshot", "api_key":"xxx"}
    When mode == "mqtt", supply cfg like {"broker":"mqtt.example", "topic":"kmrl/iot", "timeout":5}
    """
    # call ingestion with configs
    try:
        if cfg is None:
            cfg = {}
        if mode not in ("mock", "pull", "mqtt", "uns"):
            mode = "mock"
        rows = ingestion.build_combined_snapshot(mode=mode, http_cfg=cfg.get("http_cfg"), mqtt_cfg=cfg.get("mqtt_cfg"))
        n = crud.bulk_save_snapshots(db, rows)
        return {"saved": n, "mode": mode}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/uns_push")
async def ingest_uns_push(payload: dict = Body(...)):
    """
    Simple webhook for UNS events. KMRL's UNS (or external systems) can POST notifications here.
    Example: POST JSON { "T01": {...}, "T02": {...} } or { "train_id": "T01", ... }
    """
    ok = ingestion.buffer_uns_event(payload)
    if not ok:
        raise HTTPException(status_code=503, detail="Buffer full, try later")
    return {"accepted": True}


@app.websocket("/ws/train/{train_id}/telemetry")
async def websocket_telemetry(websocket: WebSocket, train_id: str):
    await websocket.accept()
    try:
        # Hook this to your ingestion.buffer or MQTT bridge to send JSON messages
        async for msg in ingestion.yield_telemetry_for_train(train_id):
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        pass



@app.post("/ingest/upload_csv")
async def ingest_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    bytes_data = await file.read()
    rows = utils.csv_to_rows(bytes_data)
    n = crud.bulk_save_snapshots(db, rows)
    return {"saved": n}

@app.get("/snapshots/latest")
def latest_snapshot(db: Session = Depends(get_db)):
    rows = crud.get_latest_snapshot(db)
    out = []
    for r in rows:
        out.append({
            "train_id": r.train_id,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
            "cert_rolling": r.cert_rolling.isoformat() if r.cert_rolling else None,
            "cert_signalling": r.cert_signalling.isoformat() if r.cert_signalling else None,
            "cert_telecom": r.cert_telecom.isoformat() if r.cert_telecom else None,
            "jobcard_severity": r.jobcard_severity,
            "pred_fail": float(r.pred_fail) if r.pred_fail is not None else None,
            "branding_req_hours": r.branding_req_hours,
            "branding_done": r.branding_done,
            "branding_shortfall": getattr(r, "branding_shortfall", None),
            "advertiser": r.advertiser if hasattr(r, "advertiser") else None,
            "advertiser_total_shortfall": getattr(r, "advertiser_total_shortfall", None),
            "advertiser_sla_risk": getattr(r, "advertiser_sla_risk", None),
            "odometer_km": r.odometer_km,
            "last_clean_days": r.last_clean_days,
            "stabling_index": r.stabling_index,
            "vibration": float(r.vibration) if r.vibration is not None else None,
            "temp": float(r.temp) if r.temp is not None else None,
            "humidity": float(r.humidity) if r.humidity is not None else None,
            "manual_blocked": bool(r.manual_blocked)
        })
    return out

# Add optimizer import (assumes module exists)
from core import branding_optimizer as branding_optimizer

# ----------------------------
# Run induction (main endpoint)
# ----------------------------
@app.post("/run_induction", response_model=InductionResponse)
def run_induction_api(req: RunInductionRequest, db: Session = Depends(get_db)):
    # fetch latest snapshot rows from DB
    rows_objs = crud.get_latest_snapshot(db)
    if not rows_objs:
        raise HTTPException(status_code=404, detail="No snapshots available. Run /ingest/auto or upload CSV first.")

    # Build a plain list-of-dicts (we'll sanitize & compute totals below)
    rows = []
    for r in rows_objs:
        # robustly extract advertiser (stored or inside raw->branding)
        if hasattr(r, "advertiser") and r.advertiser not in (None, "None", ""):
            advertiser = r.advertiser
        elif isinstance(r.raw, dict):
            advertiser = (r.raw.get("branding", {}) or {}).get("advertiser")
            if advertiser in (None, "None", ""):
                advertiser = None
        else:
            advertiser = None

        rows.append({
            "train_id": r.train_id,
            "cert_rolling": r.cert_rolling.isoformat() if r.cert_rolling else None,
            "cert_signalling": r.cert_signalling.isoformat() if r.cert_signalling else None,
            "cert_telecom": r.cert_telecom.isoformat() if r.cert_telecom else None,
            "jobcard_severity": int(r.jobcard_severity or 0),
            "pred_fail": float(r.pred_fail) if r.pred_fail is not None else 0.0,
            # preserve original per-train requirement
            "branding_req_train": int(r.branding_req_hours or 0),
            "branding_done": int(r.branding_done or 0),
            "advertiser": advertiser,
            "odometer_km": int(r.odometer_km or 0),
            "last_clean_days": int(r.last_clean_days or 0),
            "stabling_index": int(r.stabling_index or 0),
            "vibration": float(r.vibration or 0.0),
            "temp": float(r.temp or 0.0),
            "humidity": float(r.humidity or 0.0),
            "manual_blocked": bool(r.manual_blocked),
            # preserve any fields used later (reasons/duty etc.)
            "decision_reasons": getattr(r, "decision_reasons", None),
            "duty": getattr(r, "duty", None),
            "rank": getattr(r, "rank", None),
            "RiskScore": getattr(r, "RiskScore", None),
        })

    # -------------------------
    # CONSOLIDATE advertiser totals (correct approach: SUM of per-train requirements)
    # -------------------------
    df_tmp = pd.DataFrame(rows)

    # initialize advertiser columns to avoid KeyErrors
    df_tmp['advertiser_total_required'] = 0
    df_tmp['advertiser_total_done'] = 0
    df_tmp['advertiser_total_shortfall'] = 0

    adv_rows = df_tmp[df_tmp['advertiser'].notna() & (df_tmp['advertiser'].astype(str).str.strip() != '')].copy()
    if not adv_rows.empty:
        grp = adv_rows.groupby('advertiser').agg(
            advertiser_total_required=('branding_req_train', lambda s: int(pd.to_numeric(s, errors='coerce').fillna(0).astype(int).sum())),
            advertiser_total_done=('branding_done', lambda s: int(pd.to_numeric(s, errors='coerce').fillna(0).astype(int).sum()))
        ).reset_index()

        adv_map_totals = grp.set_index('advertiser').to_dict(orient='index')

        # attach totals back to original rows list
        for rec in rows:
            adv = rec.get("advertiser")
            if adv and adv in adv_map_totals:
                rec["advertiser_total_required"] = int(adv_map_totals[adv]['advertiser_total_required'])
                rec["advertiser_total_done"] = int(adv_map_totals[adv]['advertiser_total_done'])
                rec["advertiser_total_shortfall"] = max(0, rec["advertiser_total_required"] - rec["advertiser_total_done"])
            else:
                rec["advertiser_total_required"] = 0
                rec["advertiser_total_done"] = 0
                rec["advertiser_total_shortfall"] = 0
    else:
        for rec in rows:
            rec["advertiser_total_required"] = 0
            rec["advertiser_total_done"] = 0
            rec["advertiser_total_shortfall"] = 0

    # -------------------------
    # Set display-level branding_req_hours to advertiser_total_required when advertiser exists
    # Keep original per-train requirement in branding_req_train for shortfall calculation
    # -------------------------
    for rec in rows:
        adv = rec.get("advertiser")
        if adv and rec.get("advertiser_total_required", 0) > 0:
            rec["branding_req_hours"] = int(rec["advertiser_total_required"])
        else:
            rec["branding_req_hours"] = int(rec.get("branding_req_train", 0))

    # -------------------------
    # Compute per-train shortfalls using original per-train requirement (branding_req_train)
    # -------------------------
    for rec in rows:
        orig_req = int(rec.get("branding_req_train", 0))
        done = int(rec.get("branding_done", 0))
        rec["branding_shortfall"] = max(0, orig_req - done)

    # -------------------------
    # Run branding allocation (if any shortfall exists)
    # -------------------------
    total_shortfall = sum(int(r.get("branding_shortfall", 0)) for r in rows)
    # keep previous heuristic (50% of total shortfall available)
    total_hours_available = int(total_shortfall * 0.5)
    if total_hours_available > 0:
        alloc_df = branding_optimizer.allocate_branding_hours(rows, total_hours_available)
        alloc_map = alloc_df.set_index('train_id').to_dict(orient='index')
        for rec in rows:
            tid = rec['train_id']
            alloc = int(alloc_map.get(tid, {}).get('alloc', 0))
            rec['alloc'] = alloc
            rec['branding_done'] = int(rec.get('branding_done', 0)) + alloc
            # recompute per-train shortfall after allocation (against original per-train req)
            rec['branding_shortfall'] = max(0, int(rec.get('branding_req_train', 0)) - int(rec['branding_done']))
    else:
        for rec in rows:
            rec['alloc'] = 0
            rec['branding_shortfall'] = max(0, int(rec.get('branding_req_train', 0)) - int(rec.get('branding_done', 0)))

    # -------------------------
    # After allocation: recompute advertiser totals so returned results reflect allocated hours
    # -------------------------
    df_post = pd.DataFrame(rows)
    adv_rows_post = df_post[df_post['advertiser'].notna() & (df_post['advertiser'].astype(str).str.strip() != '')].copy()
    if not adv_rows_post.empty:
        grp_post = adv_rows_post.groupby('advertiser').agg(
            advertiser_total_required=('branding_req_train', lambda s: int(pd.to_numeric(s, errors='coerce').fillna(0).astype(int).sum())),
            advertiser_total_done=('branding_done', lambda s: int(pd.to_numeric(s, errors='coerce').fillna(0).astype(int).sum()))
        ).reset_index()
        adv_map_post = grp_post.set_index('advertiser').to_dict(orient='index')
        for rec in rows:
            adv = rec.get("advertiser")
            if adv and adv in adv_map_post:
                rec["advertiser_total_required"] = int(adv_map_post[adv]['advertiser_total_required'])
                rec["advertiser_total_done"] = int(adv_map_post[adv]['advertiser_total_done'])
                rec["advertiser_total_shortfall"] = max(0, rec["advertiser_total_required"] - rec["advertiser_total_done"])
            else:
                rec["advertiser_total_required"] = 0
                rec["advertiser_total_done"] = 0
                rec["advertiser_total_shortfall"] = 0
    else:
        for rec in rows:
            rec["advertiser_total_required"] = 0
            rec["advertiser_total_done"] = 0
            rec["advertiser_total_shortfall"] = 0

    # -------------------------
    # Now run the induction logic (duty allocation). Provide the updated rows as a DataFrame.
    # -------------------------
    import core.logic as logic
    df = pd.DataFrame(rows)
    df_out = logic.run_induction(df,
                                service_count=req.service_count,
                                lambda_risk=req.lambda_risk,
                                today=None,
                                forced_failed_ids=req.forced_failed_ids or [],
                                use_ml=req.use_ml)

    out_raw = df_out.to_dict(orient='records')
    out_sanitized = [_sanitize_value(rec) for rec in out_raw]

    summary = {
        "total_trains": int(len(df_out)),
        "deployed": int((df_out['duty'] == 'Deploy').sum()),
        "standby": int((df_out['duty'] == 'Standby').sum()),
        "ibl": int((df_out['duty'] == 'IBL').sum())
    }

    crud.create_induction_plan(db,
                               service_count=req.service_count,
                               lambda_risk=req.lambda_risk,
                               use_ml=req.use_ml,
                               summary=_sanitize_value(summary),
                               plan_json=out_sanitized)

    return {"summary": _sanitize_value(summary), "results": out_sanitized}

# ----------------------------
# Other endpoints (plans, compare, model info, optimize/branding)
# ----------------------------
@app.get("/plans")
def list_plans(db: Session = Depends(get_db)):
    plans = crud.get_induction_plans(db)
    return [{"id": p.id, "timestamp": p.timestamp.isoformat(), "summary": p.summary} for p in plans]

@app.get("/plans/{plan_id}", dependencies=[Depends(get_api_key)])
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = crud.get_induction_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"id": plan.id, "timestamp": plan.timestamp.isoformat(), "summary": plan.summary, "plan": plan.plan_json}

@app.get("/plans/compare/{id1}/{id2}", dependencies=[Depends(get_api_key)])
def compare_plans(id1: int, id2: int, db: Session = Depends(get_db)):
    p1 = crud.get_induction_plan(db, id1)
    p2 = crud.get_induction_plan(db, id2)
    if not p1 or not p2:
        raise HTTPException(status_code=404, detail="Plan(s) not found")

    def map_duty(plan):
        return {row["train_id"]: row["duty"] for row in plan.plan_json}

    m1, m2 = map_duty(p1), map_duty(p2)
    changes = [
        {"train_id": tid, "plan1": m1.get(tid), "plan2": m2.get(tid)}
        for tid in set(m1) | set(m2) if m1.get(tid) != m2.get(tid)
    ]
    return {"plan1": p1.id, "plan2": p2.id, "changes": changes}

@app.get("/model/info", dependencies=[Depends(get_api_key)])
def model_info():
    path = os.path.join("models", "model_info.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"message": "Model info not available"}

@app.post("/optimize/branding")
def optimize_branding(total_hours: int = Query(..., ge=0), db: Session = Depends(get_db)):
    rows_objs = crud.get_latest_snapshot(db)
    if not rows_objs:
        raise HTTPException(404, "No snapshots available")
    rows = []
    for r in rows_objs:
        days_to_cert = (r.cert_rolling - r.timestamp).days if r.cert_rolling and r.timestamp else 0
        rows.append({
            "train_id": r.train_id,
            "advertiser": r.raw.get("branding", {}).get("advertiser") if isinstance(r.raw, dict) else None,
            "branding_req_hours": r.branding_req_hours or 0,
            "branding_done": r.branding_done or 0,
            "days_to_cert": days_to_cert,
            "jobcard_severity": r.jobcard_severity or 0,
            "odometer_km": r.odometer_km or 0,
            "last_clean_days": r.last_clean_days or 0,
            "stabling_index": r.stabling_index or 0,
            "branding_shortfall": max(0, (r.branding_req_hours or 0) - (r.branding_done or 0)),
            "vibration": float(r.vibration or 0.0),
            "temp": float(r.temp or 0.0),
            "humidity": float(r.humidity or 0.0),
        })
    from core.branding_optimizer import allocate_branding_hours
    alloc_df = allocate_branding_hours(rows, total_hours_available=total_hours)
    return {"allocations": alloc_df.to_dict(orient='records')}

# Run app
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
