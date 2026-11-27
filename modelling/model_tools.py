import sqlite3

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from paths import db_file, model_file


def load_samples(limit=1000):
    conn = sqlite3.connect(db_file())
    cur = conn.cursor()
    cur.execute("SELECT port, risk_flag FROM traffic_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return np.array(rows)


def train_model():
    samples = load_samples()
    if len(samples) < 50:
        print("[!] Not enough data to train model")
        return None
    clf = IsolationForest(contamination=0.05, random_state=42)
    clf.fit(samples)
    joblib.dump(clf, model_file())
    print(f"[*] Model trained on {len(samples)} samples")
    return clf


def load_model():
    return joblib.load(model_file()) if model_file().exists() else None
