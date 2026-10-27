# backend/crud.py
from sqlalchemy.orm import Session
from . import models
from typing import List, Any
from datetime import datetime, date
import pandas as pd
import numpy as np
from decimal import Decimal

def _to_dt(v, fallback=None):
    """Convert ISO string or other to python datetime or None."""
    if v is None:
        return fallback
    # if already datetime-like, return as is
    if isinstance(v, datetime):
        return v
    try:
        # pandas.to_datetime handles many formats and returns Timestamp (subclass of datetime)
        ts = pd.to_datetime(v)
        if pd.isna(ts):
            return fallback
        return ts.to_pydatetime()
    except Exception:
        return fallback

def bulk_save_snapshots(db: Session, rows: List[dict], ts: datetime=None):
    """
    Save a list of snapshot rows (dict) into TrainSnapshot table.
    Coerces/parse common types (dates -> datetime objects), and accepts
    advertiser-level fields if present.
    """
    if ts is None:
        ts = datetime.utcnow()

    objs = []
    for r in rows:
        # safe parsing of date-like fields
        cert_rolling_dt = _to_dt(r.get('cert_rolling'), fallback=None)
        cert_signalling_dt = _to_dt(r.get('cert_signalling'), fallback=None)
        cert_telecom_dt = _to_dt(r.get('cert_telecom'), fallback=None)

        # safe numeric coercions with fallbacks
        try:
            jobcard_sev = int(r.get('jobcard_severity') or 0)
        except Exception:
            jobcard_sev = 0

        try:
            pred_fail = float(r.get('pred_fail') or 0.0)
        except Exception:
            pred_fail = 0.0

        try:
            branding_req = int(r.get('branding_req_hours') or 0)
        except Exception:
            branding_req = 0

        try:
            branding_done = int(r.get('branding_done') or 0)
        except Exception:
            branding_done = 0

        # if branding_shortfall provided, use it, else compute from req/done
        try:
            branding_shortfall = int(r.get('branding_shortfall')) if r.get('branding_shortfall') is not None else max(0, branding_req - branding_done)
        except Exception:
            branding_shortfall = max(0, branding_req - branding_done)

        try:
            odometer_km = int(r.get('odometer_km') or 0)
        except Exception:
            odometer_km = 0

        try:
            last_clean_days = int(r.get('last_clean_days') or 0)
        except Exception:
            last_clean_days = 0

        try:
            stabling_index = int(r.get('stabling_index') or 0)
        except Exception:
            stabling_index = 0

        try:
            vibration = float(r.get('vibration') or 0.0)
        except Exception:
            vibration = 0.0

        try:
            temp = float(r.get('temp') or 0.0)
        except Exception:
            temp = 0.0

        try:
            humidity = float(r.get('humidity') or 0.0)
        except Exception:
            humidity = 0.0

        manual_blocked = bool(r.get('manual_blocked', False))

        # advertiser-level fields (optional)
        advertiser = r.get('advertiser')
        if isinstance(advertiser, str) and advertiser.strip().lower() in ("none", ""):
            advertiser = None

        try:
            advertiser_total_shortfall = int(r.get('advertiser_total_shortfall') or 0)
        except Exception:
            advertiser_total_shortfall = 0

        advertiser_sla_risk = bool(r.get('advertiser_sla_risk')) if 'advertiser_sla_risk' in r else (advertiser_total_shortfall > 0)

        # Build SQLAlchemy model instance
        obj = models.TrainSnapshot(
            timestamp = ts,
            train_id = r.get('train_id'),
            cert_rolling = cert_rolling_dt,
            cert_signalling = cert_signalling_dt,
            cert_telecom = cert_telecom_dt,
            jobcard_severity = jobcard_sev,
            pred_fail = pred_fail,
            branding_req_hours = branding_req,
            branding_done = branding_done,
            branding_shortfall = branding_shortfall if hasattr(models.TrainSnapshot, "branding_shortfall") else None,
            advertiser = advertiser if hasattr(models.TrainSnapshot, "advertiser") else None,
            advertiser_total_shortfall = advertiser_total_shortfall if hasattr(models.TrainSnapshot, "advertiser_total_shortfall") else None,
            advertiser_sla_risk = advertiser_sla_risk if hasattr(models.TrainSnapshot, "advertiser_sla_risk") else None,
            odometer_km = odometer_km,
            last_clean_days = last_clean_days,
            stabling_index = stabling_index,
            vibration = vibration,
            temp = temp,
            humidity = humidity,
            manual_blocked = manual_blocked,
            raw = r
        )

        objs.append(obj)

    # bulk add and commit
    db.add_all(objs)
    db.commit()
    return len(objs)



    db.add_all(objs)
    db.commit()
    return len(objs)



# -------------- rest of file (sanitize helpers / create_plan / queries) --------------
def _sanitize_value(v):
    """Convert a single value to JSON-serializable Python native type."""
    # None
    if v is None:
        return None
    # pandas Timestamp / datetime
    if isinstance(v, (pd.Timestamp, datetime, date)):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    # numpy types
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        # convert nan to None
        if np.isnan(v):
            return None
        return float(v)
    if isinstance(v, (np.bool_ , bool)):
        return bool(v)
    if isinstance(v, (np.ndarray, )):
        return [_sanitize_value(x) for x in v.tolist()]
    # pandas / numpy scalar NaN/NA
    if (isinstance(v, float) and (v != v)) or (v is pd.NA):
        return None
    # Decimal
    if isinstance(v, Decimal):
        return float(v)
    # builtin types: str, int, float already OK
    if isinstance(v, (str, int, float, bool)):
        return v
    # dict / list / tuple -> recurse
    if isinstance(v, dict):
        return {str(k): _sanitize_value(val) for k, val in v.items()}
    if isinstance(v, (list, tuple)):
        return [_sanitize_value(x) for x in v]
    # fallback: try to cast to str
    try:
        return str(v)
    except Exception:
        return None

def _sanitize_obj(obj):
    """Sanitize arbitrarily nested obj (dict/list/primitive) for JSON storage."""
    return _sanitize_value(obj)

def get_induction_plan(db: Session, plan_id: int):
    return db.query(models.InductionPlan).filter(models.InductionPlan.id == plan_id).first()

def create_induction_plan(db: Session, service_count: int, lambda_risk: float, use_ml: bool, summary: dict, plan_json: list):
    """
    Persist InductionPlan row. Sanitizes `summary` and `plan_json` to ensure JSON-serializable types.
    """
    safe_summary = _sanitize_obj(summary)
    safe_plan = _sanitize_obj(plan_json)

    obj = models.InductionPlan(
        service_count=service_count,
        lambda_risk=lambda_risk,
        use_ml=use_ml,
        summary=safe_summary,
        plan_json=safe_plan
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj

def get_latest_snapshot(db: Session):
    # returns all snapshots for the latest timestamp
    latest = db.query(models.TrainSnapshot.timestamp).order_by(models.TrainSnapshot.timestamp.desc()).first()
    if not latest:
        return []
    ts = latest[0]
    rows = db.query(models.TrainSnapshot).filter(models.TrainSnapshot.timestamp==ts).all()
    return rows

def get_induction_plans(db: Session, limit=20):
    return db.query(models.InductionPlan).order_by(models.InductionPlan.timestamp.desc()).limit(limit).all()
