# core/ml_model.py
import joblib, os, numpy as np, pandas as pd

_MODEL_PATH = os.path.join("models", "failure_predictor_rf.pkl")

# load lazily
_model = None

def _load_model():
    global _model
    if _model is None:
        if not os.path.exists(_MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at {_MODEL_PATH}. Run scripts/train_failure_model.py first.")
        _model = joblib.load(_MODEL_PATH)
    return _model

def predict_failure_prob(df_features):
    """
    df_features: pandas.DataFrame with columns:
      ['days_to_cert','jobcard_severity','odometer_km','last_clean_days','stabling_index','branding_shortfall','vibration','temp','humidity']
    returns: numpy array of probabilities (shape: len(df_features),)
    """
    model = _load_model()
    # ensure columns order
    expected = ['days_to_cert','jobcard_severity','odometer_km','last_clean_days','stabling_index','branding_shortfall','vibration','temp','humidity']
    X = df_features.copy()
    for c in expected:
        if c not in X.columns:
            X[c] = 0.0
    X = X[expected].astype(float)
    probs = model.predict_proba(X)[:,1]
    return probs
