    # ----------------------------------
import requests
import time

DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
URL = DB + "latest.json"

last_ts = None

print("Reading /latest from Firebase (Ctrl+C to stop)\n")

while True:
    try:
        r = requests.get(URL, timeout=5)
        r.raise_for_status()
        data = r.json()

        if data is None:
            print("No data yet in /latest")
        else:
            ts = data.get("ts")

            # Only react to new data
            if ts != last_ts:
                last_ts = ts

                fall = data.get("fall", False)
                event = data.get("event", "NONE")
                state = data.get("fall_state", "UNKNOWN")

                a = data["accel_mps2"]
                g = data["gyro_rads"]

                print(
                    f"ts={ts:.3f} | "
                    f"FALL={fall} | EVENT={event} | STATE={state} | "
                    f"az={a['z']:.2f} m/s^2 | "
                    f"gz={g['z']:.3f} rad/s"
                )

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)

    time.sleep(0.5)  # polling rate (2 Hz is plenty)