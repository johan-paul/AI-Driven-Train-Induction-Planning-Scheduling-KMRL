# core/logic.py
"""
Core induction logic for KMRL prototype (ML-first).

- Uses ML predictor to fill `pred_fail` when use_ml=True and pred_fail not present/near-zero.
- No longer requires manual α, β, γ weights — ML prediction is used directly.
- Keeps lambda_risk to control how much Risk (safety) influences the composite score.
- Robust parsing and explainability as before.
"""

from datetime import datetime
import pandas as pd
import numpy as np

# Try to import ML predictor; if missing, logic still runs using pred_fail from input.
try:
    from core import ml_model
    _ML_AVAILABLE = True
except Exception:
    ml_model = None
    _ML_AVAILABLE = False

DEFAULT_SERVICE_COUNT = 8

# ----------------------------
# Helpers
# ----------------------------
def _parse_date(val, today):
    if pd.isna(val) or val == "":
        return today
    try:
        return pd.to_datetime(val)
    except Exception:
        return today

def _safe_numeric_scalar(val, default=0.0):
    try:
        out = pd.to_numeric(val, errors='coerce')
        if pd.isna(out):
            return float(default)
        return float(out)
    except Exception:
        return float(default)

# ----------------------------
# Main function
# ----------------------------
def run_induction(
    df_in,
    service_count: int = DEFAULT_SERVICE_COUNT,
    lambda_risk: float = 1.5,
    today: datetime = None,
    forced_failed_ids: list = None,
    use_ml: bool = True
):
    """
    df_in : DataFrame-like
      Expected columns if present:
        train_id, cert_rolling, cert_signalling, cert_telecom,
        jobcard_severity, pred_fail, branding_req_hours, branding_done,
        odometer_km, last_clean_days, stabling_index, vibration, temp, humidity
    lambda_risk : float
      Weight of ML RiskScore (pred_fail) inside composite score.
    use_ml : bool
      Enable ML-prediction fill for pred_fail where missing/near-zero.
    """

    # default snapshot time (21:00)
    if today is None:
        today = datetime.now().replace(hour=21, minute=0, second=0, microsecond=0)

    df = pd.DataFrame(df_in).copy().reset_index(drop=True)

    # Ensure required columns exist
    required = [
        "train_id", "cert_rolling", "cert_signalling", "cert_telecom",
        "jobcard_severity", "pred_fail", "branding_req_hours", "branding_done",
        "odometer_km", "last_clean_days", "stabling_index"
    ]
    for c in required:
        if c not in df.columns:
            if c in ["cert_rolling", "cert_signalling", "cert_telecom"]:
                df[c] = pd.NaT
            else:
                df[c] = 0

    # optional sensor/environment columns
    for optional_col in ["vibration", "temp", "humidity"]:
        if optional_col not in df.columns:
            df[optional_col] = 0.0

    # parse cert dates
    df['cert_rolling'] = df['cert_rolling'].apply(lambda x: _parse_date(x, today))
    df['cert_signalling'] = df['cert_signalling'].apply(lambda x: _parse_date(x, today))
    df['cert_telecom'] = df['cert_telecom'].apply(lambda x: _parse_date(x, today))

    # days to earliest expiry
    def _days_to_earliest_cert(row):
        expiries = [row['cert_rolling'], row['cert_signalling'], row['cert_telecom']]
        deltas = [(exp - today).days for exp in expiries]
        return int(np.min(deltas))
    df['days_to_cert'] = df.apply(_days_to_earliest_cert, axis=1)

    # branding shortfall
    df['branding_shortfall'] = (
        pd.to_numeric(df['branding_req_hours'], errors='coerce').fillna(0)
        - pd.to_numeric(df['branding_done'], errors='coerce').fillna(0)
    ).clip(lower=0)

    # mileage dev
    df['odometer_km'] = pd.to_numeric(df['odometer_km'], errors='coerce').fillna(0)
    fleet_mean_km = float(df['odometer_km'].mean()) if len(df) > 0 else 0.0
    df['mileage_dev'] = (df['odometer_km'] - fleet_mean_km).abs()

    # ensure pred_fail numeric
    df['pred_fail'] = pd.to_numeric(df.get('pred_fail', 0), errors='coerce').fillna(0.0)

    # --------------------------
    # Fill pred_fail from ML model when needed
    # --------------------------
    if use_ml and _ML_AVAILABLE:
        try:
            need_ml_mask = df['pred_fail'] <= 1e-4  # treat near-zero as "unknown"
            if need_ml_mask.any():
                feat_cols = ['days_to_cert','jobcard_severity','odometer_km','last_clean_days','stabling_index','branding_shortfall','vibration','temp','humidity']
                X_ml = pd.DataFrame(index=df.index)
                for c in feat_cols:
                    X_ml[c] = df[c] if c in df.columns else 0.0
                X_needed = X_ml.loc[need_ml_mask, feat_cols].astype(float)
                try:
                    probs = ml_model.predict_failure_prob(X_needed)
                    df.loc[need_ml_mask, 'pred_fail'] = probs
                except FileNotFoundError:
                    # model artifact missing; skip ML gracefully
                    pass
                except Exception:
                    # any other ML error: skip ML
                    pass
        except Exception:
            pass

    # --------------------------
    # RiskScore: now simply the ML pred_fail (normalized)
    # --------------------------
    # we'll use pred_fail directly; for safety ensure it's numeric 0..1
    df['pred_fail'] = df['pred_fail'].apply(lambda v: float(v) if not pd.isna(v) else 0.0)
    df['pred_fail'] = df['pred_fail'].clip(lower=0.0, upper=1.0)
    # give friendly alias RiskScore for downstream
    df['RiskScore'] = df['pred_fail']

    # Also keep inv_days_to_cert & jobcard as debug info if desired
    def _inv_days(x):
        try:
            xi = int(x)
            return 1.0/xi if xi > 0 else 10.0
        except Exception:
            return 10.0
    df['inv_days_to_cert'] = df['days_to_cert'].apply(_inv_days)
    df['job_sev_norm'] = df['jobcard_severity'].apply(lambda v: _safe_numeric_scalar(v, 0.0) / 10.0)

    # --------------------------
    # Hard constraints
    # --------------------------
    def _hard_reasons(row):
        reasons = []
        job_sev = _safe_numeric_scalar(row.get('jobcard_severity', 0), 0.0)
        if int(row.get('days_to_cert', 0)) <= 0:
            reasons.append("Certificate expired or expires today")
        if job_sev >= 8:
            reasons.append("Open critical job-card (severity >=8)")
        if forced_failed_ids and row.get('train_id') in forced_failed_ids:
            reasons.append("Forced failed (what-if simulation)")
        return reasons

    df['hard_reasons'] = df.apply(_hard_reasons, axis=1)
    df['hard_block'] = df['hard_reasons'].apply(lambda x: len(x) > 0)

    # --------------------------
    # Normalize auxiliary terms
    # --------------------------
    max_brand = df['branding_shortfall'].max() if df['branding_shortfall'].max() > 0 else 1.0
    max_mileage_dev = df['mileage_dev'].max() if df['mileage_dev'].max() > 0 else 1.0
    max_clean = pd.to_numeric(df['last_clean_days'], errors='coerce').fillna(0).max()
    max_clean = max_clean if max_clean > 0 else 1.0
    max_stabling = pd.to_numeric(df['stabling_index'], errors='coerce').fillna(0).max()
    max_stabling = max_stabling if max_stabling > 0 else 1.0

    df['branding_shortfall_norm'] = df['branding_shortfall'] / max_brand
    df['mileage_dev_norm'] = df['mileage_dev'] / max_mileage_dev
    df['clean_urgency_norm'] = pd.to_numeric(df['last_clean_days'], errors='coerce').fillna(0) / max_clean
    df['stabling_penalty_norm'] = pd.to_numeric(df['stabling_index'], errors='coerce').fillna(0) / max_stabling

    # --------------------------
    # Composite score (lower better)
    # --------------------------
    df['composite_score'] = (
        lambda_risk * df['RiskScore']
        - 0.8 * df['branding_shortfall_norm']
        + 0.5 * df['mileage_dev_norm']
        + 0.6 * df['clean_urgency_norm']
        + 0.4 * df['stabling_penalty_norm']
    )

    # --------------------------
    # Assign duties
    # --------------------------
    df['duty'] = None
    df['rank'] = np.nan
    df.loc[df['hard_block'], 'duty'] = 'IBL'

    eligible = df[~df['hard_block']].sort_values('composite_score', ascending=True).copy().reset_index()
    eligible['rank'] = range(1, len(eligible) + 1)
    eligible.loc[eligible.index[:service_count], 'duty'] = 'Deploy'
    eligible.loc[eligible.index[service_count:], 'duty'] = 'Standby'

    for _, r in eligible.iterrows():
        idx = r['index']
        df.at[idx, 'duty'] = r['duty']
        df.at[idx, 'rank'] = r['rank']

    # --------------------------
    # Decision reasons
    # --------------------------
    def _build_reasons(row):
        reasons = []
        if row['duty'] == 'IBL':
            reasons.extend(row['hard_reasons'])
        else:
            reasons.append(f"PredFail={row['pred_fail']:.3f}")
            if row['branding_shortfall'] > 0:
                reasons.append(f"Branding shortfall={int(row['branding_shortfall'])} hrs")
            try:
                if row['mileage_dev'] > (fleet_mean_km * 0.2):
                    reasons.append(f"High mileage deviation ({int(row['mileage_dev'])} km)")
            except Exception:
                if row['mileage_dev'] > 0:
                    reasons.append(f"High mileage deviation ({int(row['mileage_dev'])} km)")
            if pd.to_numeric(row.get('last_clean_days', 0), errors='coerce') >= 7:
                reasons.append(f"Cleaning overdue ({int(row.get('last_clean_days',0))} days)")
            try:
                if pd.to_numeric(row.get('stabling_index', 0), errors='coerce') > (max_stabling * 0.75):
                    reasons.append("Stabled far back (higher shunting)")
            except Exception:
                pass
        return "; ".join(reasons)

    df['decision_reasons'] = df.apply(_build_reasons, axis=1)

    # final sort and return
    order = {'Deploy': 0, 'Standby': 1, 'IBL': 2, None: 3}
    df['duty_sort'] = df['duty'].apply(lambda x: order.get(x, 3))
    df = df.sort_values(['duty_sort', 'rank'], ascending=[True, True]).reset_index(drop=True)

    return df
