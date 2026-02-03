'''
import requests
import time
import matplotlib.pyplot as plt


# 1. Setup Constants
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
URL_LATEST = DB + "latest.json"
# Note: To get history, we hit the timeseries node
URL_HISTORY = DB + "timeseries.json?orderBy=\"$key\"&limitToLast=20"

# 2. Setup Plotting
plt.ion() 
fig, ax = plt.subplots()
ax.set_ylim(0, 40) # Spikes can be high!
ax.set_ylabel('Total Acceleration (m/s^2)')
ax.axhline(y=25, color='r', linestyle='--', label='Fall Threshold')
line, = ax.plot([], [], 'b-')
plt.legend()

last_ts = None
accel_history = []

print("Starting Monitor...")

while True:
    try:
        # Fetch the latest point
        r = requests.get(URL_LATEST, timeout=5)
        data = r.json()

        
        if data and data.get("ts") != last_ts:
            last_ts = data.get("ts")
            a = data["accel_mps2"] # This dictionary contains x, y, and z

            # 1. Extract all three components
            ax_val = a['x']
            ay_val = a['y']
            az_val = a['z']

            # 2. Calculate the Total Magnitude (SMV)
            # This captures the impact no matter which way the sensor hits the floor
            total_accel = (ax_val**2 + ay_val**2 + az_val**2)**0.5

            # 3. Print all axes to the terminal
            print(
                f"ts={last_ts:.3f} | "
                f"ACC: X={ax_val:>6.2f}, Y={ay_val:>6.2f}, Z={az_val:>6.2f} | "
                f"TOTAL: {total_accel:.2f} m/s^2"
            )

    except Exception as e:
        print("Error:", e)

    plt.pause(0.1) # Essential for Matplotlib to stay responsive

'''

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