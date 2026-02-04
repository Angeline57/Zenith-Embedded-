# -*- coding: utf-8 -*-
import time
import math
import smbus2
import requests
from collections import deque

# ===================== Firebase (HTTP) =====================
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
TIMESERIES_NODE = "timeseries"
session = requests.Session()

UPLOAD_HZ = 1.0
UPLOAD_PERIOD = 1.0 / UPLOAD_HZ

def upload_timeseries(payload):
    ts_ms = int(payload["ts"] * 1000)
    path = f"{TIMESERIES_NODE}/{ts_ms}.json"
    r = session.put(DB + path, json=payload, timeout=5)
    if not r.ok:
        raise ConnectionError(f"Timeseries write failed: {r.status_code} {r.text}")

def upload_latest(payload):
    r = session.put(DB + "latest.json", json=payload, timeout=5)
    if not r.ok:
        raise ConnectionError(f"Latest write failed: {r.status_code} {r.text}")

# ===================== I2C setup =====================
bus = smbus2.SMBus(1)

FXOS_ADDR = 0x1F   # accel + mag (try 0x1E if not found)
FXAS_ADDR = 0x21   # gyro       (try 0x20 if not found)

# ---------------- FXOS8700 registers ----------------
FXOS_WHOAMI = 0x0D
FXOS_CTRL_REG1 = 0x2A
FXOS_OUT_X_MSB = 0x01
FXOS_M_CTRL_REG1 = 0x5B
FXOS_M_CTRL_REG2 = 0x5C

# ---------------- FXAS21002C registers ----------------
FXAS_WHOAMI = 0x0C
FXAS_CTRL_REG0 = 0x0D
FXAS_CTRL_REG1 = 0x13
FXAS_OUT_X_MSB = 0x01

# ===================== Scaling =====================
ACC_COUNTS_PER_G = 4096.0
G = 9.80665
G0 = 9.80665
GYRO_COUNTS_PER_DPS = 16.4

# ===================== Helpers =====================
def read_u8(addr, reg):
    return bus.read_byte_data(addr, reg)

def write_u8(addr, reg, val):
    bus.write_byte_data(addr, reg, val & 0xFF)

def read_block(addr, reg, length):
    return bus.read_i2c_block_data(addr, reg, length)

def twos_complement(val, bits):
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

def accel_raw_to_mps2(raw):
    return (raw / ACC_COUNTS_PER_G) * G

def gyro_raw_to_rads(raw):
    return (raw / GYRO_COUNTS_PER_DPS) * (math.pi / 180.0)

def mag3(x, y, z):
    return math.sqrt(x*x + y*y + z*z)

def variance(vals):
    if len(vals) < 5:
        return 999.0
    m = sum(vals) / len(vals)
    return sum((v - m) ** 2 for v in vals) / (len(vals) - 1)

# ===================== Sensor init =====================
def fxos_init():
    ctrl1 = read_u8(FXOS_ADDR, FXOS_CTRL_REG1)
    write_u8(FXOS_ADDR, FXOS_CTRL_REG1, ctrl1 & ~0x01)  # standby
    time.sleep(0.05)
    write_u8(FXOS_ADDR, FXOS_M_CTRL_REG1, 0x1F)
    write_u8(FXOS_ADDR, FXOS_M_CTRL_REG2, 0x20)
    write_u8(FXOS_ADDR, FXOS_CTRL_REG1, (ctrl1 & 0xFE) | 0x01)  # active
    time.sleep(0.05)

def fxas_init():
    write_u8(FXAS_ADDR, FXAS_CTRL_REG1, 0x00)  # standby
    time.sleep(0.05)
    write_u8(FXAS_ADDR, FXAS_CTRL_REG0, 0x00)  # ±2000 dps
    write_u8(FXAS_ADDR, FXAS_CTRL_REG1, 0x0E)  # active
    time.sleep(0.05)

def fxos_read_accel_mps2():
    d = read_block(FXOS_ADDR, FXOS_OUT_X_MSB, 6)
    ax = twos_complement((d[0] << 8) | d[1], 16) >> 2
    ay = twos_complement((d[2] << 8) | d[3], 16) >> 2
    az = twos_complement((d[4] << 8) | d[5], 16) >> 2
    return (accel_raw_to_mps2(ax), accel_raw_to_mps2(ay), accel_raw_to_mps2(az))

def fxas_read_gyro_rads():
    d = read_block(FXAS_ADDR, FXAS_OUT_X_MSB, 6)
    gx = twos_complement((d[0] << 8) | d[1], 16)
    gy = twos_complement((d[2] << 8) | d[3], 16)
    gz = twos_complement((d[4] << 8) | d[5], 16)
    return (gyro_raw_to_rads(gx), gyro_raw_to_rads(gy), gyro_raw_to_rads(gz))

# ===================== Fall detector thresholds =====================
FREEFALL_G_MAX = 0.4
IMPACT_G_MIN = 2.5
POST_STILL_GYRO_MAX = 0.35
POST_STILL_VAR_MAX = 0.20
FREEFALL_WINDOW_S = 0.35
IMPACT_WINDOW_S = 0.8
POST_STILL_WINDOW_S = 1.2

# States
IDLE = 0
FREEFALL = 1
IMPACT = 2
CONFIRM = 3
STATE_NAME = {IDLE: "IDLE", FREEFALL: "FREEFALL", IMPACT: "IMPACT", CONFIRM: "CONFIRM"}

# ===================== Main =====================
def main():
    try:
        print(f"FXOS WHOAMI: 0x{read_u8(FXOS_ADDR, FXOS_WHOAMI):02X}")
        print(f"FXAS WHOAMI: 0x{read_u8(FXAS_ADDR, FXAS_WHOAMI):02X}")
    except OSError:
        print("I2C error - check wiring/I2C/addresses.")
        return

    fxos_init()
    fxas_init()

    print("\nFall detection @50Hz, uploads @1Hz (Ctrl+C to stop)")
    print(f"DB: {DB}\n")

    # detection sampling
    sample_hz = 50.0
    dt = 1.0 / sample_hz
    next_sample_t = time.time()

    # upload timing
    next_upload_t = time.time()

    # fall state machine
    state = IDLE
    t_state = time.time()

    a_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    gyro_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))

    cooldown_until = 0.0

    # last computed values (for 1Hz upload)
    latest_payload = None

    try:
        while True:
            # fixed-rate sampling
            now = time.time()
            if now < next_sample_t:
                time.sleep(next_sample_t - now)
            next_sample_t += dt

            t = time.time()

            ax, ay, az = fxos_read_accel_mps2()
            gx, gy, gz = fxas_read_gyro_rads()

            a_mag = mag3(ax, ay, az)
            a_g = a_mag / G0
            w_mag = mag3(gx, gy, gz)

            a_mag_buf.append(a_mag)
            gyro_mag_buf.append(w_mag)

            event = "NONE"
            fall_detected_now = False

            # cooldown suppresses repeated triggers
            if t < cooldown_until:
                state = IDLE

            # ----- state machine -----
            if state == IDLE:
                if a_g <= FREEFALL_G_MAX:
                    state = FREEFALL
                    t_state = t
                    a_mag_buf.clear()
                    gyro_mag_buf.clear()

            elif state == FREEFALL:
                if (t - t_state) > FREEFALL_WINDOW_S:
                    state = IDLE
                elif a_g >= IMPACT_G_MIN:
                    state = IMPACT
                    t_state = t
                    a_mag_buf.clear()
                    gyro_mag_buf.clear()

            elif state == IMPACT:
                if (t - t_state) > IMPACT_WINDOW_S:
                    state = CONFIRM
                    t_state = t

            elif state == CONFIRM:
                if (t - t_state) >= POST_STILL_WINDOW_S and len(a_mag_buf) >= 10:
                    var_a = variance(list(a_mag_buf))
                    mean_w = sum(gyro_mag_buf) / max(1, len(gyro_mag_buf))

                    if mean_w <= POST_STILL_GYRO_MAX and var_a <= POST_STILL_VAR_MAX:
                        fall_detected_now = True
                        event = "FALL_DETECTED"
                        cooldown_until = t + 2.0  # keep alarm true for 2s

                        print("\n?? FALL DETECTED")
                        print(f"  a_g(last)={a_g:.2f}g | mean gyro={mean_w:.3f} rad/s | accel var={var_a:.3f}\n")

                    state = IDLE

            fall_status = (t < cooldown_until)

            # Build the latest computed payload (this updates at 50Hz)
            latest_payload = {
                "sensor": "nxp_9dof_fall",
                "ts": t,
                "accel_mps2": {"x": round(ax, 4), "y": round(ay, 4), "z": round(az, 4)},
                "gyro_rads": {"x": round(gx, 6), "y": round(gy, 6), "z": round(gz, 6)},
                "a_g": round(a_g, 3),
                "w_rads": round(w_mag, 3),
                "fall": bool(fall_status),          # current (sticky) alarm status
                "event": event,                     # "FALL_DETECTED" only on trigger moment
                "fall_state": STATE_NAME[state],
            }

            # Upload only at 1 Hz
            if t >= next_upload_t and latest_payload is not None:
                next_upload_t += UPLOAD_PERIOD
                try:
                    upload_timeseries(latest_payload)
                    upload_latest(latest_payload)
                    print(f"Uploaded 1Hz @ {latest_payload['ts']:.3f} | fall={latest_payload['fall']} | event={latest_payload['event']}")
                except Exception as e:
                    print("Upload failed:", e)

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
