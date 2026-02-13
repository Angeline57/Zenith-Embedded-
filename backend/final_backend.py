import time
import os
import math
from collections import deque
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# Firebase config
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
KEYFILE = os.path.join(
    os.path.dirname(__file__),
    "embedded-zenith-firebase-adminsdk-fbsvc-92e37b3ef2.json",
)

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/firebase.database",
]

# Wear detection options
USE_ML = True
TEMP_THRESHOLD_C = 27.0  # fallback threshold (Celsius)

# ML Model (trained weights; keep in sync with embedded/ML_device_worn.py)
MODEL = {
    "b0": -3.821346,
    "b1": 1.776240,   # temp
    "b2": -1.725786,  # mean temp
    "b3": 0.232956,   # slope
    "threshold": 0.5,
}

# Authenticated session
credentials = service_account.Credentials.from_service_account_file(
    KEYFILE, scopes=SCOPES
)
session = AuthorizedSession(credentials)

# ML helpers
def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def predict_on_person(temp_c: float, mean_c: float, slope_c_s: float) -> bool:
    z = (
        MODEL["b0"]
        + MODEL["b1"] * temp_c
        + MODEL["b2"] * mean_c
        + MODEL["b3"] * slope_c_s
    )
    return sigmoid(z) >= MODEL["threshold"]

def update_patient_status(is_on_person):
    """Sends ONLY the status update back to Firebase."""
    try:
        r = session.patch(DB + "latest.json", json={"device_on_person": is_on_person}, timeout=5)
        r.raise_for_status()
    except Exception as e:
        print(f"Failed to update status: {e}")

def read_latest():
    r = session.get(DB + "latest.json", timeout=5)
    r.raise_for_status()
    return r.json()

# Main
if __name__ == "__main__":
    mode = "ML" if USE_ML else "THRESHOLD"
    print(f"Backend Engine Active. Wear detection mode: {mode}\n")

    try:
        window_s = 20.0
        poll_interval_s = 1.0
        max_len = int(window_s / poll_interval_s)
        temps = deque(maxlen=max_len)
        times = deque(maxlen=max_len)

        while True:
            data = read_latest()

            if data and 'tmp_die_c' in data:
                current_temp = data['tmp_die_c']

                if USE_ML:
                    temps.append(float(current_temp))
                    times.append(time.time())
                    if len(temps) >= 3:
                        mean_c = sum(temps) / len(temps)
                        dt = max(1e-6, times[-1] - times[-2])
                        slope_c_s = (temps[-1] - temps[-2]) / dt
                        on_person = predict_on_person(temps[-1], mean_c, slope_c_s)
                    else:
                        on_person = float(current_temp) >= TEMP_THRESHOLD_C
                else:
                    on_person = float(current_temp) >= TEMP_THRESHOLD_C
                
                # Update Firebase with the new calculation
                update_patient_status(on_person)

                print(f"Input Temp: {current_temp}C | Result: {'ON-PERSON' if on_person else 'OFF'}")
            else:
                print("Waiting for temperature data from Pi...")

            time.sleep(poll_interval_s) # Check once per second

    except KeyboardInterrupt:
        print("\nBackend Stopped.")


