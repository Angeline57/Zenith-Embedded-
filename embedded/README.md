# 📟 Embedded System (Raspberry Pi Layer)

The Embedded Layer acts as the "Intelligent Edge" of the SafeSleep system. It is responsible for real-time sensor fusion and safety-critical decision-making.

## 📡 Sensor Integration
The system utilizes two primary sensors interfaced via the **I2C protocol**:

* **9DOF IMU (LSM9DS1):** Combines a 3-axis accelerometer, gyroscope, and magnetometer. This provides the raw motion data required to track orientation and sudden impacts.
* **Time-of-Flight (ToF) Distance Sensor (VL53L1X):** Uses laser pulsing to measure precise distance. In this project, it is used to detect "Bed Exit" by monitoring the proximity between the wearable and the mattress surface.



## 🧠 Edge Processing vs. Cloud Latency
A core architectural decision of SafeSleep is performing **Fall Detection locally on the Raspberry Pi** rather than in the cloud.

### The Frequency Challenge
* **High-Frequency Sampling:** Accurate fall detection requires monitoring acceleration peaks at frequencies up to **100Hz - 200Hz**. 
* **HTTP/Network Bottleneck:** Standard cloud databases and HTTP protocols struggle to maintain consistent stability when receiving 100+ requests per second. Attempting to stream raw data at this rate would result in packet loss and significant "jitter."
* **The Solution (Edge Computing):** By processing the 9DOF data locally, the Pi samples at high speed but only sends a **high-level state change** (e.g., `FALL_DETECTED: true`) via HTTP. This ensures the system remains responsive while staying within the bandwidth limitations of the cloud layer.



## 🛠️ Local Logic & Detection
1.  **Motion Analysis:** Filters raw noise from the IMU to distinguish between normal sleep movements and abnormal events.
2.  **Fall Detection:** Utilizes a threshold-based algorithm that triggers when a specific G-force magnitude is followed by a sudden change in orientation.
3.  **Bed Exit & Wandering:** Combines ToF distance data and motion trends to determine if the patient has safely left the bed or is wandering in an unsafe state.

## 🚀 How to Run
1. Connect sensors to the Pi's GPIO pins (SDA/SCL).
2. Install libraries: `pip install adafruit-circuitpython-lsm9ds1 adafruit-circuitpython-vl53l1x`
3. Run the acquisition script: `python pi_main.py`