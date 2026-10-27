# scripts/train_failure_model.py
# Usage:
#   python -m pip install scikit-learn pandas joblib
#   python scripts/train_failure_model.py
import numpy as np, pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report
import joblib, os

# ---------- Synthetic dataset (demo) ----------
def make_row():
    days_to_cert = np.random.randint(-5, 120)
    job_sev = np.random.choice([0,1,2,3,4,5,6,7,8,9,10], p=[0.25,0.1,0.1,0.1,0.1,0.08,0.08,0.07,0.05,0.04,0.03])
    odometer = np.random.normal(1000, 400)
    last_clean = np.random.randint(0,20)
    stabling = np.random.randint(1,13)
    branding_short = max(0, int(np.random.normal(20,30)))
    vib = abs(np.random.normal(0.5,0.3))
    temp = np.random.normal(30,3)
    humidity = np.random.normal(60,10)
    p = 0.01
    if days_to_cert <= 0:
        p += 0.25
    elif days_to_cert < 3:
        p += 0.12
    elif days_to_cert < 10:
        p += 0.04
    p += 0.02 * job_sev
    if odometer > 1600:
        p += 0.05
    if last_clean > 10:
        p += 0.03
    p += min(0.3, vib*0.4)
    if temp>38 or temp<10:
        p += 0.02
    p = min(0.95, p)
    label = np.random.rand() < p
    return [days_to_cert, job_sev, odometer, last_clean, stabling, branding_short, vib, temp, humidity, int(label)]

def create_dataset(N=2000):
    cols = ['days_to_cert','jobcard_severity','odometer_km','last_clean_days','stabling_index','branding_shortfall','vibration','temp','humidity','failed_next_day']
    data = [make_row() for _ in range(N)]
    return pd.DataFrame(data, columns=cols)

def train_and_save(path='models/failure_predictor_rf.pkl'):
    df = create_dataset(2000)
    X = df.drop(columns=['failed_next_day'])
    y = df['failed_next_day']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    clf = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred_proba = clf.predict_proba(X_test)[:,1]
    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, clf.predict(X_test))
    print("Trained model: AUC=%.4f  Acc=%.4f" % (auc, acc))

    os.makedirs(os.path.dirname(path), exist_ok=True)
    joblib.dump(clf, path)
    print("Saved model to:", path)

if __name__ == "__main__":
    train_and_save()
