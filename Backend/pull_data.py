import requests
import time

DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
URL = DB + "latest.json"

last_ts = None

while True:
    try:
        r = requests.get(URL, timeout=5)
        r.raise_for_status()
        data = r.json()

        if not data:
            print("No data yet")
        else:
            ts = data.get("ts")

            # Only print if it's new
            if ts != last_ts:
                last_ts = ts

                a = data["accel_mps2"]
                g = data["gyro_rads"]
                m = data["mag_uT"]

                print(
                    f"ts={ts:.3f} | "
                    f"ACC z={a['z']:.2f} m/s^2 | "
                    f"GYRO z={g['z']:.3f} rad/s | "
                    f"MAG x={m['x']:.1f} uT"
                )

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)

    time.sleep(0.2)  # poll rate (5 Hz)