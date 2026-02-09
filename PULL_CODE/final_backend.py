# -*- coding: utf-8 -*-
import time
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# ===================== Firebase config =====================
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
KEYFILE = "embedded-zenith-firebase-adminsdk-fbsvc-92e37b3ef2.json"  

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/firebase.database",
]

# ===================== Logic Constants =====================
# You can change these values here without touching the Raspberry Pi!
TEMP_THRESHOLD = 23  # Celsius

# ===================== Authenticated session =====================
credentials = service_account.Credentials.from_service_account_file(
    KEYFILE, scopes=SCOPES
)
session = AuthorizedSession(credentials)

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

# ===================== Main Logic Loop =====================
if __name__ == "__main__":
    print(f"Backend Engine Active. Monitoring Temp Threshold: {TEMP_THRESHOLD}C\n")

    try:
        while True:
            data = read_latest()

            if data and 'tmp_die_c' in data:
                current_temp = data['tmp_die_c']
                
                # --- THE PROCESSING STEP ---
                # This is the logic you moved off the Raspberry Pi
                on_person = current_temp > TEMP_THRESHOLD
                
                # Update Firebase with the new calculation
                update_patient_status(on_person)

                print(f"Input Temp: {current_temp}C | Result: {'ON-PERSON' if on_person else 'OFF'}")
            else:
                print("Waiting for temperature data from Pi...")

            time.sleep(1) # Check once per second

    except KeyboardInterrupt:
        print("\nBackend Stopped.")