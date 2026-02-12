# -*- coding: utf-8 -*-
"""
ML_device_worn.py

Adds an ML-based device_on_person signal on top of final_code.py output
without modifying final_code.py.

How it works:
1) final_code.py uploads /latest.json (incl. tmp_die_c).
2) This script polls /latest.json, computes ML features from temperature
   history, predicts on-person, and PATCHes the result back to Firebase.

Replace the placeholder MODEL weights with trained values.
"""

import time
from collections import deque
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession


# ===================== Firebase (Authenticated HTTP) =====================
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
KEYFILE = "/home/pi/embedded-zenith-firebase-adminsdk-fbsvc-92e37b3ef2.json"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/firebase.database",
]

credentials = service_account.Credentials.from_service_account_file(
    KEYFILE, scopes=SCOPES
)
session = AuthorizedSession(credentials)

LATEST_URL = DB + "latest.json"


# ===================== ML Model (placeholder) =====================
# Simple logistic regression: p = sigmoid(b0 + b1*temp + b2*mean + b3*slope)
# Replace with your trained weights.
MODEL = {
    "b0": -3.821346,
    "b1": 1.776240,
    "b2": -1.725786,
    "b3": 0.232956,
    "threshold": 0.5,
}

def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + pow(2.718281828, -x))


def predict_on_person(temp_c: float, mean_c: float, slope_c_s: float) -> bool:
    z = (
        MODEL["b0"]
        + MODEL["b1"] * temp_c
        + MODEL["b2"] * mean_c
        + MODEL["b3"] * slope_c_s
    )
    p = sigmoid(z)
    return p >= MODEL["threshold"]


def main():
    window_s = 20.0
    poll_interval_s = 1.0
    max_len = int(window_s / poll_interval_s)
    temps = deque(maxlen=max_len)
    times = deque(maxlen=max_len)

    last_ts = None

print("ML_device_worn.py started: polling /latest.json and writing device_on_person")

    while True:
        try:
            r = session.get(LATEST_URL, timeout=10)
            r.raise_for_status()
            data = r.json() or {}

            ts = data.get("ts")
            tmp = data.get("tmp_die_c")
            if tmp is None:
                time.sleep(poll_interval_s)
                continue

            # Only process new data
            if ts is not None and ts == last_ts:
                time.sleep(poll_interval_s)
                continue
            last_ts = ts

            now = time.time()
            temps.append(float(tmp))
            times.append(now)

            if len(temps) < 3:
                time.sleep(poll_interval_s)
                continue

            mean_c = sum(temps) / len(temps)
            # slope: delta temp / delta time (last 2 points)
            dt = max(1e-6, times[-1] - times[-2])
            slope_c_s = (temps[-1] - temps[-2]) / dt

            on_person = predict_on_person(temps[-1], mean_c, slope_c_s)

            patch = {
                "device_on_person": on_person,
                "device_on_person_ml": True,
                "device_on_person_score": None,
            }

            session.patch(LATEST_URL, json=patch, timeout=10)
        except Exception as e:
            print("ML update failed:", e)

        time.sleep(poll_interval_s)


if __name__ == "__main__":
    main()
