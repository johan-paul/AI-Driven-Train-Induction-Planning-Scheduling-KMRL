# app.py
# Run:
#   pip install -r requirements.txt
#   pip install requests python-dotenv
#   streamlit run app.py

import os
import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from core.sample_data import get_sample_df

st.set_page_config(page_title="KMRL Induction — Backend-driven UI", layout="wide", initial_sidebar_state="expanded")

# ---------- CSS (white card placeholder restored) ----------
st.markdown("""
<style>
/* Card container */
.card {
  border-radius: 10px;
  border: 1px solid rgba(0,0,0,0.06);
  padding: 14px;
  margin-bottom: 12px;
  background: #ffffff;
  color: #111111 !important;
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
  min-height: 160px;           /* restored to keep the original white-card shape */
  overflow-wrap: break-word;
  word-break: break-word;
}

/* Ensure every child inside card is dark text (overrides theme) */
.card, .card * { color: #111111 !important; }

/* Badge styles */
.badge {
  display:inline-block;
  padding:6px 12px;
  border-radius:999px;
  font-weight:700;
  font-size:13px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
.badge-deploy { background:#0bb07a; color:#fff !important; }
.badge-standby { background:#ffb845; color:#2b1f00 !important; }
.badge-ibl { background:#ff6b6b; color:#fff !important; }

/* small muted text */
.small-muted { color: #5b646a !important; font-size:13px; }

/* Card header train id (bolder & visible) */
.card .card-header {
  font-weight:800;
  font-size:18px;
  color:#0b2540 !important;
}

/* Progress bar base (outer) and inner fill */
.progress-outer { width:100%; border-radius:8px; background:#e9ecef; height:12px; overflow:hidden; }
.progress-inner { height:12px; background:#4a90e2; border-radius:8px 0 0 8px; }

/* Advertiser summary tile */
.adv-tile {
  background: rgba(255,255,255,0.02);
  padding: 12px;
  border-radius: 10px;
  margin-bottom: 12px;
}

/* Name box */
.adv-name-box {
  background: #d1f2d1; /* light green */
  color: #0b3d0b !important;
  font-weight: 700;
  font-size: 1rem;
  padding: 6px 10px;
  border-radius: 6px;
  display: inline-block;
  margin-bottom: 8px;
}

/* White hrs text */
.adv-numbers {
  color: #ffffff !important;
  font-weight: 700;
  font-size: 0.95rem;
}

/* details summary style */
.details-summary {
  cursor:pointer;
  margin-top:6px;
  font-weight:600;
  color:#1a73e8;
}

/* ensure small-muted inside details remains readable on dark theme */
.details-body { margin-top:6px; color:#5b646a; font-size:13px; }

/* Small pass/fail badge used in expander */
.pf-badge {
  display:inline-block;
  padding:6px 10px;
  border-radius:6px;
  color:#fff;
  font-weight:700;
  font-size:0.85rem;
  margin-left:6px;
}
.pf-pass { background:#2ea44f; }   /* green */
.pf-fail { background:#d73a49; }   /* red */
.pf-unk  { background:#6a737d; }   /* grey */

/* white placeholder box (keeps the original large white rectangle) */
.card-placeholder {
  height: 140px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.04);
  box-shadow: inset 0 0 0 1px rgba(0,0,0,0.02);
  margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("🚆 KMRL Nightly Induction — Backend-driven (ML-first)")
st.markdown("This UI talks to the FastAPI backend. If the backend is unreachable it falls back to sample data for demo purposes.")

# ---------- Sidebar: Backend & Controls (branding budget removed) ----------
with st.sidebar:
    st.header("Backend")
    default_backend = os.getenv("BACKEND_URL") or st.secrets.get("backend", {}).get("url") if "backend" in st.secrets else "http://localhost:8000"
    BACKEND_URL = st.text_input("Backend URL", value=default_backend)
    default_key = os.getenv("KMRL_API_KEY") or st.secrets.get("backend", {}).get("api_key") if "backend" in st.secrets else ""
    API_KEY = st.text_input("API Key (x-api-key)", value=default_key, type="password")
    st.markdown("---")
    st.header("Controls")
    use_sample = st.checkbox("Use sample data (ingest mock snapshot)", value=True)
    ingest_mode = st.selectbox("Ingest mode", options=["mock","pull","mqtt","uns"], index=0, help="mock: local sample; pull: HTTP IoT pull; mqtt: short MQTT collect; uns: wait for UNS/webhook events (or call /ingest/uns_push)")
    # extra config UI for pull/mqtt
    http_endpoint = None
    mqtt_broker = None
    mqtt_topic = None
    if ingest_mode == "pull":
        http_endpoint = st.text_input("IoT HTTP endpoint", value=os.getenv("IOT_HTTP_ENDPOINT",""))
        http_api_key = st.text_input("IoT HTTP API Key (optional)", value=os.getenv("IOT_HTTP_API_KEY",""), type="password")
    elif ingest_mode == "mqtt":
        mqtt_broker = st.text_input("MQTT Broker (host:port)", value=os.getenv("MQTT_BROKER","localhost"))
        mqtt_topic = st.text_input("MQTT Topic", value=os.getenv("MQTT_TOPIC","kmrl/iot"))
    uploaded = st.file_uploader("Upload CSV snapshot (optional)", type=["csv"])

    service_count = st.slider("Service rakes required (SERVICE_COUNT)", min_value=1, max_value=40, value=8)
    st.markdown("---")
    lambda_risk = st.number_input("λ (risk weight in composite)", value=1.5, step=0.1, format="%.2f")
    use_ml = st.checkbox("Use ML predictor to fill missing pred_fail", value=True)
    st.markdown("---")
    st.subheader("What-if")
    force_fail_select = st.multiselect("Force-fail trains (select from snapshot)", options=[])
    st.markdown("---")
    run_button = st.button("Run Induction (backend)")

# ---------- HTTP helpers ----------
HEADERS = {}
if API_KEY:
    HEADERS["x-api-key"] = API_KEY

def api_post(path: str, json_payload: dict = None, files: dict = None, timeout: int = 30):
    url = BACKEND_URL.rstrip("/") + path
    try:
        if files:
            r = requests.post(url, files=files, headers=HEADERS, timeout=timeout)
        else:
            r = requests.post(url, json=json_payload, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        try:
            return True, r.json()
        except Exception:
            return True, r.text
    except requests.HTTPError:
        try:
            return False, r.json()
        except Exception:
            return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, f"Request failed: {e}"

def api_get(path: str, timeout: int = 30):
    url = BACKEND_URL.rstrip("/") + path
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        try:
            return True, r.json()
        except Exception:
            return True, r.text
    except requests.HTTPError:
        try:
            return False, r.json()
        except Exception:
            return False, f"HTTP {r.status_code}: {r.text}"
    except Exception as e:
        return False, f"Request failed: {e}"

# ---------- Try to fetch latest snapshot from backend to populate UI options ----------
snapshot_df = None
ok, resp = api_get("/snapshots/latest")
if ok and isinstance(resp, list) and len(resp) > 0:
    try:
        snapshot_df = pd.DataFrame(resp)
    except Exception:
        snapshot_df = None
else:
    snapshot_df = None

# populate force-fail options
if snapshot_df is not None and 'train_id' in snapshot_df.columns:
    train_ids = list(snapshot_df['train_id'].astype(str).unique())
    force_fail_select = st.sidebar.multiselect("Force-fail trains (select from snapshot)", options=train_ids, default=force_fail_select)

# ---------- Input snapshot preview ----------
st.subheader("Input snapshot (preview)")
col1, col2 = st.columns([3,2])
with col1:
    if uploaded is not None:
        try:
            df_preview = pd.read_csv(uploaded)
            st.dataframe(df_preview.head(10), use_container_width=True)
        except Exception:
            st.info("Uploaded file will be sent to backend when you run the job.")
    elif snapshot_df is not None:
        st.dataframe(snapshot_df.head(10), use_container_width=True)
    else:
        st.info("No snapshot from backend. If 'Use sample data' is checked, backend ingest will create mock snapshot on Run.")

with col2:
    st.markdown("**Quick tips**")
    st.markdown("- Ensure Backend URL and API Key (x-api-key) are set in the sidebar.")
    st.markdown("- Click *Run Induction (backend)* to ingest (if requested) and generate a plan.")
    st.markdown("- Upload CSV to replace snapshot for a single run (optional).")

# ---------- Helper: render progress bar (customizable label color) ----------
def render_progress_html(done_hours: int, req_hours: int, max_width_px: int = 720, label_color: str = "#1a73e8") -> str:
    try:
        done = int(done_hours or 0)
    except Exception:
        done = 0
    try:
        req = int(req_hours or 0)
    except Exception:
        req = 0

    pct = 0.0
    if req > 0:
        pct = max(0.0, min(1.0, done / req))
    fill_pct = int(pct * 100)

    # label color configurable (white for advertiser tiles, blue/dark for train cards)
    label_html = f"<div style='font-size:0.95rem;color:{label_color};font-weight:700'>{done}/{req} hrs</div>"
    html = f"""
    <div style="max-width:{max_width_px}px;width:100%;margin-top:6px;margin-bottom:6px;">
      <div style="display:flex;justify-content:flex-end;align-items:center;margin-bottom:6px;">{label_html}</div>
      <div class="progress-outer">
        <div class="progress-inner" style="width:{fill_pct}%;"></div>
      </div>
    </div>
    """
    return html

# ---------- Ensure session state keys ----------
if 'selected_train_id' not in st.session_state:
    st.session_state['selected_train_id'] = None

# ---------- Run logic ----------
if run_button:
    # Step 1: ingest snapshot (upload or auto)
    if uploaded is not None:
        try:
            files = {"file": ("snapshot.csv", uploaded.getvalue(), "text/csv")}
            ok, resp = api_post("/ingest/upload_csv", files=files)
            if not ok:
                st.error(f"Ingest failed: {resp}")
                st.stop()
            st.success(f"Ingested CSV snapshot: saved {resp.get('saved', 'N/A')}")
        except Exception as e:
            st.error(f"Upload failed: {e}")
            st.stop()
    elif use_sample:
        # choose mode and optional cfg
        mode = "mock"
        cfg = {}
        if ingest_mode != "mock":
            mode = ingest_mode
            if ingest_mode == "pull":
                cfg = {"http_cfg": {"endpoint": http_endpoint, "api_key": http_api_key}}
            elif ingest_mode == "mqtt":
                cfg = {"mqtt_cfg": {"broker": mqtt_broker, "topic": mqtt_topic, "timeout": 5}}
            elif ingest_mode == "uns":
                cfg = {}
        # call backend with mode as query param and cfg as json body
        ok, resp = api_post(f"/ingest/auto?mode={mode}", json_payload=cfg)
        if not ok:
            st.error(f"Ingest mock snapshot failed: {resp}")
            st.stop()
        st.success(f"Ingested sample snapshot: saved {resp.get('saved', 'N/A')}")

    # Step 2: run induction
    forced_failed_ids = force_fail_select or []
    payload = {
        "service_count": int(service_count),
        "lambda_risk": float(lambda_risk),
        "use_ml": bool(use_ml),
        "forced_failed_ids": forced_failed_ids
    }

    st.info("Running induction on backend...")
    ok, resp = api_post("/run_induction", json_payload=payload)
    if not ok:
        if isinstance(resp, dict) and resp.get("detail"):
            st.error(f"Induction error: {resp.get('detail')}")
        else:
            st.error(f"Induction failed: {resp}")
        st.stop()

    results = resp.get("results") if isinstance(resp, dict) else None
    if results is None:
        st.error("Backend returned no results.")
        st.stop()

    df_out = pd.DataFrame(results)
    if df_out.empty:
        st.error("No trains in plan (empty result).")
        st.stop()

    # ---------- Normalize & cast columns ----------
    df_out['pred_fail'] = pd.to_numeric(df_out.get('pred_fail', 0), errors='coerce').fillna(0.0).astype(float)
    df_out['rank'] = pd.to_numeric(df_out.get('rank'), errors='coerce')
    df_out['odometer_km'] = pd.to_numeric(df_out.get('odometer_km', 0), errors='coerce').fillna(0).astype(int)
    df_out['last_clean_days'] = pd.to_numeric(df_out.get('last_clean_days', 0), errors='coerce').fillna(0).astype(int)
    df_out['stabling_index'] = pd.to_numeric(df_out.get('stabling_index', 0), errors='coerce').fillna(0).astype(int)

    # ensure both per-train original req and display req exist
    if 'branding_req_train' in df_out.columns:
        df_out['branding_req_train'] = pd.to_numeric(df_out.get('branding_req_train', 0), errors='coerce').fillna(0).astype(int)
    else:
        df_out['branding_req_train'] = pd.to_numeric(df_out.get('branding_req_hours', 0), errors='coerce').fillna(0).astype(int)

    if 'branding_req_hours' in df_out.columns:
        df_out['branding_req_hours'] = pd.to_numeric(df_out.get('branding_req_hours', 0), errors='coerce').fillna(0).astype(int)
    else:
        df_out['branding_req_hours'] = df_out['branding_req_train']

    if 'branding_done' in df_out.columns:
        df_out['branding_done'] = pd.to_numeric(df_out.get('branding_done', 0), errors='coerce').fillna(0).astype(int)
    else:
        df_out['branding_done'] = 0

    # ensure advertiser totals exist (frontend trusts backend authoritative totals)
    df_out['advertiser'] = df_out.get('advertiser', None)
    df_out['advertiser'] = df_out['advertiser'].apply(lambda x: None if x in (None, 'None', '-', '') else str(x).strip())
    df_out['advertiser_total_required'] = pd.to_numeric(df_out.get('advertiser_total_required', 0), errors='coerce').fillna(0).astype(int)
    df_out['advertiser_total_done'] = pd.to_numeric(df_out.get('advertiser_total_done', 0), errors='coerce').fillna(0).astype(int)
    df_out['advertiser_total_shortfall'] = pd.to_numeric(df_out.get('advertiser_total_shortfall', 0), errors='coerce').fillna(0).astype(int)

    # ensure branding_shortfall is per-train shortfall (backend calculates this)
    if 'branding_shortfall' in df_out.columns:
        df_out['branding_shortfall'] = pd.to_numeric(df_out.get('branding_shortfall', 0), errors='coerce').fillna(0).astype(int)
    else:
        df_out['branding_shortfall'] = (df_out['branding_req_train'] - df_out['branding_done']).clip(lower=0).astype(int)

    # ensure alloc column exists
    if 'alloc' not in df_out.columns:
        df_out['alloc'] = 0
    df_out['alloc'] = pd.to_numeric(df_out['alloc'], errors='coerce').fillna(0).astype(int)

    # ---------- Result header & KPI ----------
    deployed = int((df_out['duty']=='Deploy').sum()) if 'duty' in df_out else 0
    standby = int((df_out['duty']=='Standby').sum()) if 'duty' in df_out else 0
    ibl = int((df_out['duty']=='IBL').sum()) if 'duty' in df_out else 0
    st.markdown(f"### Result Summary  •  Deploy: **{deployed}**  •  Standby: **{standby}**  •  IBL: **{ibl}**")

    k1,k2,k3,k4 = st.columns(4)
    k1.metric("Total trains", len(df_out))
    k2.metric("Deploy", deployed)
    k3.metric("Standby", standby)
    k4.metric("IBL", ibl)

    # ---------- Advertiser Summary ----------
    adv_summary = df_out[df_out['advertiser'].notna()].groupby('advertiser').agg(
        total_required=('advertiser_total_required', 'max'),
        total_done=('advertiser_total_done', 'max'),
        train_count=('train_id', 'count')
    ).reset_index()

    if not adv_summary.empty:
        BUFFER_HOURS = 10
        adv_summary['display_required'] = adv_summary.apply(lambda r: max(int(r['total_required'] or 0), int(r['total_done'] or 0) + BUFFER_HOURS), axis=1)
        adv_summary['pct'] = adv_summary.apply(lambda r: 0.0 if r['display_required'] <= 0 else (r['total_done'] / r['display_required']), axis=1)
        adv_summary = adv_summary.sort_values(by=['pct', 'train_count'], ascending=[True, False]).reset_index(drop=True)

        st.markdown("### 📊 Advertiser Summary")
        cols = st.columns(2)
        for i, arow in adv_summary.iterrows():
            col = cols[i % 2]
            with col:
                adv_name = arow['advertiser']
                canonical_req = int(arow['total_required'] or 0)
                canonical_done = int(arow['total_done'] or 0)
                disp_req = int(arow['display_required'] or 0)

                st.markdown("<div class='adv-tile'>", unsafe_allow_html=True)
                st.markdown(f"<div class='adv-name-box'>{adv_name}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='adv-numbers' style='margin-top:6px;margin-bottom:6px'>{canonical_done}/{disp_req} hrs</div>", unsafe_allow_html=True)
                st.markdown(render_progress_html(canonical_done, disp_req, max_width_px=520, label_color="#ffffff"), unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("---")

    # ---------- Cards grouped by duty ----------
    for duty in ["Deploy","Standby","IBL"]:
        group = df_out[df_out['duty']==duty] if 'duty' in df_out else pd.DataFrame()
        if len(group) == 0:
            continue
        st.markdown(f"#### {duty} — {len(group)}")
        cols = st.columns(3)
        idx = 0
        for _, row in group.iterrows():
            col = cols[idx % 3]
            idx += 1
            with col:
                badge_class = "badge-deploy" if duty=="Deploy" else ("badge-standby" if duty=="Standby" else "badge-ibl")
                train_id = row.get('train_id', '-')
                rank_display = int(row['rank']) if pd.notna(row.get('rank')) else '-'
                pred_display = float(row.get('pred_fail') or 0.0)
                adv_val = row.get('advertiser')
                advertiser_display = adv_val if adv_val not in (None, 'None') else "-"
                alloc_display = int(row.get('alloc') or 0)

                # display-level advertiser canonical required (cards show this so they match summary)
                adv_req_display = int(row.get('branding_req_hours') or 0)
                # original per-train requirement (used for shortfall)
                adv_req_train = int(row.get('branding_req_train') or 0)
                adv_done_train = int(row.get('branding_done') or 0)
                shortfall_train = int(row.get('branding_shortfall') or 0)

                # construct alloc string only when > 0
                alloc_str = f" (alloc:+{alloc_display})" if alloc_display and alloc_display > 0 else ""

                st.markdown(f"""
                  <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                      <div class="card-header">🚆 {train_id}</div>
                      <div class="badge {badge_class}">{duty}</div>
                    </div>
                    <div class="small-muted">Rank: {rank_display} • PredFail: {pred_display:.3f}</div>
                    <div style="margin-top:8px;">
                      <div><strong>Km:</strong> {int(row.get('odometer_km') or 0)} &nbsp; 
                           <strong>Brand shortfall:</strong> {shortfall_train} hrs</div>
                      <div style="margin-top:6px;"><strong>Advertiser:</strong> {advertiser_display}</div>
                      <div class="small-muted" style="margin-top:6px;">
                           Stabling idx: {int(row.get('stabling_index') or 0)} • 
                           Last clean: {int(row.get('last_clean_days') or 0)} days
                      </div>
                      <div style="margin-top:8px;font-weight:700;">
                           Brand req/done (train): {adv_req_display}/{adv_done_train} hrs{alloc_str}
                      </div>
                      {render_progress_html(adv_done_train, adv_req_display, max_width_px=360, label_color="#1a73e8")}
                """, unsafe_allow_html=True)

                # ---------- EXPANDER: details (no telemetry) ----------
                # note: do not pass key arg for compatibility
                with st.expander("View details", expanded=False):
                    # safe getter
                    def safe_get(field, cast=None, default=None):
                        val = row.get(field, None)
                        try:
                            if pd.isna(val):
                                return default
                        except Exception:
                            pass
                        if val is None:
                            return default
                        if cast:
                            try:
                                return cast(val)
                            except Exception:
                                return default
                        return val

                    # thresholds (tweak as needed)
                    fitness_ok_days = 3
                    cleaning_ok_days = 3
                    stabling_good_index = 6
                    mileage_tolerance_km = 500

                    days_to_cert = safe_get('days_to_cert', cast=float, default=None)
                    jobcard_severity = safe_get('jobcard_severity', cast=float, default=None)
                    branding_shortfall = safe_get('branding_shortfall', cast=float, default=None)
                    odometer_km = safe_get('odometer_km', cast=float, default=None)
                    last_clean_days = safe_get('last_clean_days', cast=float, default=None)
                    stabling_index = safe_get('stabling_index', cast=float, default=None)

                    # fleet median if available
                    fleet_median_odometer = None
                    try:
                        fleet_median_odometer = float(df_out['odometer_km'].median())
                    except Exception:
                        fleet_median_odometer = None

                    # compute statuses and reasons
                    if days_to_cert is None:
                        fitness_status, fitness_reason = None, "days_to_cert missing"
                    else:
                        if days_to_cert <= 0:
                            fitness_status, fitness_reason = False, f"Certificate expired ({int(days_to_cert)} days to cert)."
                        elif days_to_cert <= fitness_ok_days:
                            fitness_status, fitness_reason = False, f"Certificate near expiry ({int(days_to_cert)} days left)."
                        else:
                            fitness_status, fitness_reason = True, f"Certificate valid ({int(days_to_cert)} days left)."

                    if jobcard_severity is None:
                        jobcard_status, jobcard_reason = None, "jobcard_severity missing"
                    else:
                        jobcard_status = (int(jobcard_severity) == 0)
                        jobcard_reason = "No open job-cards." if jobcard_status else f"Open job-cards with severity {int(jobcard_severity)}."

                    if branding_shortfall is None:
                        branding_status, branding_reason = None, "branding_shortfall missing"
                    else:
                        branding_status = (branding_shortfall == 0)
                        branding_reason = "Branding satisfied." if branding_status else f"Brand shortfall: {int(branding_shortfall)} hrs."

                    if odometer_km is None:
                        mileage_status, mileage_reason = None, "odometer_km missing"
                    else:
                        if fleet_median_odometer is None:
                            mileage_status, mileage_reason = None, "fleet median missing"
                        else:
                            deviation = abs(odometer_km - fleet_median_odometer)
                            mileage_status = (deviation <= mileage_tolerance_km)
                            mileage_reason = f"Deviation {int(deviation)} km from fleet median ({int(fleet_median_odometer)} km)."

                    if last_clean_days is None:
                        cleaning_status, cleaning_reason = None, "last_clean_days missing"
                    else:
                        cleaning_status = (last_clean_days <= cleaning_ok_days)
                        cleaning_reason = "Recently cleaned." if cleaning_status else f"Last clean {int(last_clean_days)} days ago."

                    if stabling_index is None:
                        stabling_status, stabling_reason = None, "stabling_index missing"
                    else:
                        stabling_status = (stabling_index <= stabling_good_index)
                        stabling_reason = ("Good stabling (close to turnout)." if stabling_status
                                          else f"Stabled far back (index {int(stabling_index)}).")

                    def pf_html(s):
                        if s is True:
                            return "<span class='pf-badge pf-pass'>PASS</span>"
                        if s is False:
                            return "<span class='pf-badge pf-fail'>FAIL</span>"
                        return "<span class='pf-badge pf-unk'>UNKNOWN</span>"

                    # Checklist summary
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**1. Fitness Certificates** {pf_html(fitness_status)}", unsafe_allow_html=True)
                        st.markdown(f"<small>{fitness_reason}</small>", unsafe_allow_html=True)
                        st.markdown(f"**2. Job-Card Status** {pf_html(jobcard_status)}", unsafe_allow_html=True)
                        st.markdown(f"<small>{jobcard_reason}</small>", unsafe_allow_html=True)
                        st.markdown(f"**3. Branding priorities** {pf_html(branding_status)}", unsafe_allow_html=True)
                        st.markdown(f"<small>{branding_reason}</small>", unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"**4. Mileage balancing** {pf_html(mileage_status)}", unsafe_allow_html=True)
                        st.markdown(f"<small>{mileage_reason}</small>", unsafe_allow_html=True)
                        st.markdown(f"**5. Cleaning & detailing** {pf_html(cleaning_status)}", unsafe_allow_html=True)
                        st.markdown(f"<small>{cleaning_reason}</small>", unsafe_allow_html=True)
                        st.markdown(f"**6. Stabling geometry** {pf_html(stabling_status)}", unsafe_allow_html=True)
                        st.markdown(f"<small>{stabling_reason}</small>", unsafe_allow_html=True)

                    st.markdown("---")
                    # Decision reasons (why selected/rejected) + full train details
                    st.subheader("Decision reasons & metadata")
                    # show whatever backend put into decision_reasons (if any)
                    decision_reasons = row.get('decision_reasons') or row.get('reason') or ""
                    if decision_reasons:
                        st.markdown("**Why this train was chosen / rejected:**")
                        st.write(decision_reasons)
                    else:
                        st.markdown("<small>No decision reasons provided by backend.</small>", unsafe_allow_html=True)

                    # show other key metadata in a vertical table
                    meta_cols = ['train_id','duty','rank','pred_fail','odometer_km','last_clean_days',
                                 'stabling_index','advertiser','branding_req_train','branding_done',
                                 'branding_shortfall','alloc','jobcard_severity','days_to_cert']
                    meta_cols = [c for c in meta_cols if c in row]
                    if meta_cols:
                        meta_df = pd.DataFrame({k: [row.get(k)] for k in meta_cols})
                        st.table(meta_df.T)

                    st.markdown("---")
                    st.subheader("Raw data & downloads")
                    st.json(row.to_dict())
                    import io, json as _json
                    csv_buf = io.StringIO(); pd.DataFrame([row]).to_csv(csv_buf, index=False)
                    st.download_button("Download CSV", csv_buf.getvalue().encode('utf-8'), file_name=f"train_{train_id}.csv", mime="text/csv")
                    st.download_button("Download JSON", _json.dumps(row.to_dict(), default=str, indent=2).encode('utf-8'), file_name=f"train_{train_id}.json", mime="application/json")

                st.markdown("</div>", unsafe_allow_html=True)

    # ---------- Full plan table & download ----------
    st.markdown("#### Full Plan (table)")
    df_show = df_out.copy()
    df_show['pred_fail'] = df_show['pred_fail'].map(lambda x: round(float(x),4))
    visible_cols = [c for c in ['train_id','advertiser','advertiser_total_required','advertiser_total_done','duty','rank','pred_fail','branding_shortfall','branding_req_train','branding_req_hours','branding_done','alloc','odometer_km','last_clean_days','stabling_index','decision_reasons'] if c in df_show.columns]
    st.dataframe(df_show[visible_cols], use_container_width=True)
    csv = df_show[visible_cols].to_csv(index=False).encode('utf-8')
    st.download_button("Download Induction Plan CSV", csv, file_name="induction_plan.csv", mime="text/csv")

else:
    st.info("Set backend URL and API Key in the sidebar, optionally upload a CSV snapshot, toggle Use ML, then click *Run Induction (backend)*.")

# ---------- Plan history ----------
st.markdown("---")
st.subheader("Plan History (latest saved plans on backend)")
ok, plans = api_get("/plans")
if not ok:
    st.info(f"Plan history not available from backend: {plans}")
else:
    if isinstance(plans, list) and len(plans)>0:
        df_plans = pd.DataFrame(plans)
        if 'timestamp' in df_plans.columns:
            df_plans['timestamp'] = pd.to_datetime(df_plans['timestamp'], errors='coerce')
        st.dataframe(df_plans, use_container_width=True)
        sel = st.selectbox("Inspect plan id", options=df_plans['id'].tolist())
        if sel is not None:
            ok2, plan_detail = api_get(f"/plans/{sel}")
            if not ok2:
                st.error(f"Failed to fetch plan {sel}: {plan_detail}")
            else:
                st.markdown(f"#### Plan {sel} — {plan_detail.get('summary')}")
                plan_df = pd.DataFrame(plan_detail.get("plan") or [])
                if not plan_df.empty:
                    if 'advertiser' not in plan_df.columns:
                        plan_df['advertiser'] = None
                    st.dataframe(plan_df.head(200), use_container_width=True)
    else:
        st.info("No plans saved on backend yet.")
 