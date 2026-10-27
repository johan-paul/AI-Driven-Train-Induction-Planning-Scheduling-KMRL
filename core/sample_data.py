# core/sample_data.py
import pandas as pd

def get_sample_df():
    # sample data matching the fields required by logic.py
    sample = [
        {"train_id":"T01","cert_rolling":"2025-10-21","cert_signalling":"2025-11-10","cert_telecom":"2025-09-13","jobcard_severity":1,"pred_fail":0.02,"branding_req_hours":100,"branding_done":80,"odometer_km":1200,"last_clean_days":3,"stabling_index":1},
        {"train_id":"T02","cert_rolling":"2025-09-10","cert_signalling":"2025-09-16","cert_telecom":"2025-09-16","jobcard_severity":9,"pred_fail":0.12,"branding_req_hours":50,"branding_done":50,"odometer_km":900,"last_clean_days":10,"stabling_index":6},
        {"train_id":"T03","cert_rolling":"2025-09-13","cert_signalling":"2025-09-13","cert_telecom":"2025-09-13","jobcard_severity":2,"pred_fail":0.05,"branding_req_hours":80,"branding_done":30,"odometer_km":1400,"last_clean_days":1,"stabling_index":2},
        {"train_id":"T04","cert_rolling":"2026-01-01","cert_signalling":"2026-01-01","cert_telecom":"2026-01-01","jobcard_severity":0,"pred_fail":0.01,"branding_req_hours":0,"branding_done":0,"odometer_km":600,"last_clean_days":8,"stabling_index":3},
        {"train_id":"T05","cert_rolling":"2025-09-16","cert_signalling":"2025-09-16","cert_telecom":"2025-09-16","jobcard_severity":5,"pred_fail":0.07,"branding_req_hours":40,"branding_done":10,"odometer_km":1800,"last_clean_days":4,"stabling_index":10},
        {"train_id":"T06","cert_rolling":"2025-09-12","cert_signalling":"2025-09-12","cert_telecom":"2025-09-12","jobcard_severity":8,"pred_fail":0.15,"branding_req_hours":20,"branding_done":5,"odometer_km":300,"last_clean_days":12,"stabling_index":4},
        {"train_id":"T07","cert_rolling":"2025-10-01","cert_signalling":"2025-10-01","cert_telecom":"2025-10-01","jobcard_severity":0,"pred_fail":0.02,"branding_req_hours":200,"branding_done":150,"odometer_km":950,"last_clean_days":2,"stabling_index":5},
        {"train_id":"T08","cert_rolling":"2025-09-14","cert_signalling":"2025-09-14","cert_telecom":"2025-09-14","jobcard_severity":3,"pred_fail":0.04,"branding_req_hours":0,"branding_done":0,"odometer_km":2000,"last_clean_days":6,"stabling_index":8},
        {"train_id":"T09","cert_rolling":"2025-09-21","cert_signalling":"2025-09-21","cert_telecom":"2025-09-11","jobcard_severity":4,"pred_fail":0.03,"branding_req_hours":60,"branding_done":55,"odometer_km":1100,"last_clean_days":0,"stabling_index":9},
        {"train_id":"T10","cert_rolling":"2026-03-01","cert_signalling":"2026-03-01","cert_telecom":"2026-03-01","jobcard_severity":0,"pred_fail":0.005,"branding_req_hours":0,"branding_done":0,"odometer_km":400,"last_clean_days":1,"stabling_index":7},
        {"train_id":"T11","cert_rolling":"2025-09-18","cert_signalling":"2025-09-13","cert_telecom":"2025-09-13","jobcard_severity":6,"pred_fail":0.09,"branding_req_hours":120,"branding_done":100,"odometer_km":1350,"last_clean_days":5,"stabling_index":11},
        {"train_id":"T12","cert_rolling":"2025-09-26","cert_signalling":"2025-09-26","cert_telecom":"2025-09-26","jobcard_severity":0,"pred_fail":0.02,"branding_req_hours":30,"branding_done":5,"odometer_km":700,"last_clean_days":9,"stabling_index":12}
    ]
    return pd.DataFrame(sample)
