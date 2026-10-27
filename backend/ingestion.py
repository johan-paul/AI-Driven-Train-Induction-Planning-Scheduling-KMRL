# backend/ingestion.py
"""
Extended ingestion with real IoT + UNS support.

Usage:
    build_combined_snapshot(mode="mock")        # existing behavior (random mocks)
    build_combined_snapshot(mode="pull", http_cfg={...})
    build_combined_snapshot(mode="mqtt", mqtt_cfg={...})
    - For UNS, you can POST to /ingest/uns_push; the endpoint will buffer events which build_combined_snapshot(mode="uns") will consume.
"""

from datetime import datetime, timedelta
import random
import time
import json
import threading
import queue
import os

# optional import for MQTT — add paho-mqtt in requirements if using MQTT
try:
    import paho.mqtt.client as mqtt
    HAS_MQTT = True
except Exception:
    HAS_MQTT = False

# --- keep existing DEFAULT_TRAINS for backward compat ---
DEFAULT_TRAINS = [f"T{str(i).zfill(2)}" for i in range(1, 26)]

# --- existing mock connectors (kept) ---
def fetch_maximo_jobcards():
    res = {}
    for t in DEFAULT_TRAINS:
        sev = random.randint(0, 10)
        res[t] = {"severity": sev, "description": "Mock jobcard"}
    return res

def fetch_branding_contracts():
    res = {}
    for t in DEFAULT_TRAINS:
        required = random.choice([0, 20, 40, 60, 100, 120])
        done = max(0, required - random.randint(0, required))
        adv = random.choice(["Pepsi", "Adani", None, "Nike", "Amazon"])
        res[t] = {"required_hours": required, "done_hours": done, "advertiser": adv}
    return res

# ----------------------------
# IoT connectors
# ----------------------------
def fetch_iot_http(endpoint: str, api_key: str = None, timeout: int = 10):
    """
    Pull an HTTP JSON snapshot from IoT backend.
    Expected JSON shape: { "T01": {...}, "T02": {...}, ... }
    Each train object should contain fields: odometer_km, last_clean_days, stabling_index,
    vibration, temp, humidity, cert_rolling, cert_signalling, cert_telecom
    """
    import requests
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        r = requests.get(endpoint, headers=headers, timeout=timeout)
        r.raise_for_status()
        body = r.json()
        # normalize to our internal per-train dict
        out = {}
        for tid, data in (body.items() if isinstance(body, dict) else []):
            out[tid] = {
                "odometer_km": int(data.get("odometer_km", 0)),
                "last_clean_days": int(data.get("last_clean_days", 0)),
                "stabling_index": int(data.get("stabling_index", 0)),
                "vibration": float(data.get("vibration", 0.0)),
                "temp": float(data.get("temp", 0.0)),
                "humidity": float(data.get("humidity", 0.0)),
                "cert_rolling": data.get("cert_rolling"),
                "cert_signalling": data.get("cert_signalling"),
                "cert_telecom": data.get("cert_telecom"),
            }
        return out
    except Exception as e:
        # return empty dict on failure — caller will fall back to mock
        return {}

def fetch_iot_mqtt(broker: str, topic: str, client_id: str = "kmrl_ingest", qos: int = 1, timeout: int = 5):
    """
    Subscribe to an MQTT topic and collect retained messages for a short window.
    Topic payload must be JSON mapping train_id -> sensor dict or individual messages per train.
    Requires 'paho-mqtt' in requirements.
    """
    if not HAS_MQTT:
        return {}

    collected = {}
    lock = threading.Lock()

    def on_connect(client, userdata, flags, rc):
        client.subscribe(topic, qos=qos)

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            # If topic is per-train payload, ensure mapping
            # payload may be {"train_id": "T01", ...} or {"T01": {..}, "T02": {...}}
            if isinstance(payload, dict) and "train_id" in payload:
                tid = payload.get("train_id")
                with lock:
                    collected[tid] = payload
            elif isinstance(payload, dict):
                # assume mapping
                with lock:
                    for k, v in payload.items():
                        collected[k] = v
        except Exception:
            pass

    client = mqtt.Client(client_id=client_id)
    client.on_connect = on_connect
    client.on_message = on_message

    # Allow optional broker credentials from env
    user = os.getenv("MQTT_USER")
    pwd = os.getenv("MQTT_PASS")
    if user and pwd:
        client.username_pw_set(user, pwd)

    try:
        client.connect(broker)
        client.loop_start()
        # wait a short window to gather retained/last-will messages
        time.sleep(timeout)
    except Exception:
        return {}
    finally:
        client.loop_stop()
        client.disconnect()

    # normalize collected payloads
    out = {}
    with lock:
        for tid, data in collected.items():
            out[tid] = {
                "odometer_km": int(data.get("odometer_km", 0)),
                "last_clean_days": int(data.get("last_clean_days", 0)),
                "stabling_index": int(data.get("stabling_index", 0)),
                "vibration": float(data.get("vibration", 0.0)),
                "temp": float(data.get("temp", 0.0)),
                "humidity": float(data.get("humidity", 0.0)),
                "cert_rolling": data.get("cert_rolling"),
                "cert_signalling": data.get("cert_signalling"),
                "cert_telecom": data.get("cert_telecom"),
            }
    return out

# ----------------------------
# UNS (push/webhook) simple buffer
# ----------------------------
# This in-memory buffer is simple and OK for demo. In production persist events to DB or queue.
_UNS_BUFFER = queue.Queue(maxsize=10000)

def buffer_uns_event(event: dict):
    """Called by webhook endpoint to store incoming UNS events."""
    try:
        _UNS_BUFFER.put_nowait({"ts": datetime.utcnow().isoformat(), "event": event})
        return True
    except queue.Full:
        return False

def drain_uns_buffer(max_events: int = 1000):
    """Return up to max_events from buffer (non-blocking)."""
    events = []
    while len(events) < max_events:
        try:
            item = _UNS_BUFFER.get_nowait()
            events.append(item)
        except Exception:
            break
    return events

# ----------------------------
# Compose combined snapshot
# ----------------------------
def build_combined_snapshot(mode: str = "mock", http_cfg: dict = None, mqtt_cfg: dict = None):
    """
    mode: "mock" | "pull" | "mqtt" | "uns"
    http_cfg: {"endpoint": "...", "api_key": "..."}
    mqtt_cfg: {"broker": "mqtt.example", "topic": "kmrl/iot"}
    """
    # existing connectors (jobcards, branding) — keep using mocks for Maximo/Branding for now
    jobcards = fetch_maximo_jobcards()
    brands = fetch_branding_contracts()

    iots = {}
    if mode == "pull" and http_cfg:
        iots = fetch_iot_http(http_cfg.get("endpoint"), api_key=http_cfg.get("api_key"))
    elif mode == "mqtt" and mqtt_cfg:
        iots = fetch_iot_mqtt(mqtt_cfg.get("broker"), mqtt_cfg.get("topic"), client_id=mqtt_cfg.get("client_id", "kmrl_ingest"), timeout=mqtt_cfg.get("timeout", 5))
    elif mode == "uns":
        # consume UNS buffer events and attempt to merge them into a mapping
        events = drain_uns_buffer(max_events=500)
        for e in events:
            payload = e.get("event") or {}
            # payload may be mapping per-train or a single train
            if isinstance(payload, dict):
                # unify behavior: if top keys are train ids, use as mapping
                sample_keys = list(payload.keys())[:5]
                if sample_keys and all(k.startswith("T") for k in sample_keys):
                    for tid, data in payload.items():
                        iots[tid] = data
                else:
                    # expect single train payload with "train_id"
                    tid = payload.get("train_id")
                    if tid:
                        iots[tid] = payload
    # else mode=="mock" or no data: fallback to randomized mocks
    if not iots:
        # existing mock iots (random)
        iots = {}
        for idx, t in enumerate(DEFAULT_TRAINS):
            iots[t] = {
                "odometer_km": int(max(0, random.normalvariate(1000 + idx * 10, 300))),
                "last_clean_days": random.randint(0, 12),
                "stabling_index": random.randint(1, 12),
                "vibration": max(0.0, random.normalvariate(0.4, 0.25)),
                "temp": round(random.normalvariate(30, 2.5), 1),
                "humidity": round(random.normalvariate(60, 6), 1),
                "cert_rolling": (datetime.utcnow() + timedelta(days=random.randint(-3, 180))).isoformat(),
                "cert_signalling": (datetime.utcnow() + timedelta(days=random.randint(-3, 180))).isoformat(),
                "cert_telecom": (datetime.utcnow() + timedelta(days=random.randint(-3, 180))).isoformat(),
            }

    # Normalize advertiser hours (same logic as prior code)
    advertiser_hours = {}
    for t, br in brands.items():
        adv = br.get("advertiser")
        if adv and adv not in ("None", "-"):
            if adv not in advertiser_hours:
                advertiser_hours[adv] = br.get("required_hours", 0)

    rows = []
    for t in DEFAULT_TRAINS:
        jc = jobcards.get(t, {"severity": 0})
        io = iots.get(t, {})
        br = brands.get(t, {"required_hours": 0, "done_hours": 0, "advertiser": None})

        adv = br.get("advertiser")
        if adv in (None, "None", "-"):
            req = 0
            done = 0
            adv = None
        else:
            req = advertiser_hours.get(adv, br.get("required_hours", 0))
            done = max(0, br.get("done_hours", 0))

        row = {
            "train_id": t,
            "cert_rolling": io.get("cert_rolling"),
            "cert_signalling": io.get("cert_signalling"),
            "cert_telecom": io.get("cert_telecom"),
            "jobcard_severity": jc.get("severity", 0),
            "pred_fail": 0.0,
            "branding_req_hours": req,
            "branding_done": done,
            "advertiser": adv,
            "odometer_km": int(io.get("odometer_km", 0)),
            "last_clean_days": int(io.get("last_clean_days", 0)),
            "stabling_index": int(io.get("stabling_index", 0)),
            "vibration": float(io.get("vibration", 0.0)),
            "temp": float(io.get("temp", 0.0)),
            "humidity": float(io.get("humidity", 0.0)),
            "raw_iot": io
        }
        rows.append(row)

    return rows
