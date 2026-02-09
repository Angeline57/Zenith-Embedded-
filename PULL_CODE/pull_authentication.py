# -*- coding: utf-8 -*-
import time
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# ===================== Firebase config =====================
DB = "https://esexample-ccdba-default-rtdb.europe-west1.firebasedatabase.app/"

KEYFILE = "/home/pi/src/esexample-ccdba-firebase-adminsdk.json"  
# ↑ change to the actual path of your service account key

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/firebase.database",
]

# ===================== Authenticated session =====================
credentials = service_account.Credentials.from_service_account_file(
    KEYFILE, scopes=SCOPES
)

session = AuthorizedSession(credentials)

# ===================== Read latest =====================
def read_latest():
    r = session.get(DB + "latest.json", timeout=5)
    r.raise_for_status()
    return r.json()

# ===================== Main loop =====================
if __name__ == "__main__":
    print("Reading authenticated latest.json (Ctrl+C to stop)\n")

    try:
        while True:
            data = read_latest()

            if data is None:
                print("No data yet.")
            else:
                print(
                    f"ts={data.get('ts'):.3f} | "
                    f"fall={data.get('fall')} | "
                    f"tof={data.get('tof_mm')} mm | "
                    f"tmp={data.get('tmp_die_c')} C | "
                    f"accel={data.get('accel_mps2')}"
                )

            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopped.")
