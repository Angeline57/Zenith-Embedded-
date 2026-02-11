# -*- coding: utf-8 -*-

import time
import math
import smbus2
import requests

# ---------------- Firebase config ----------------
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"

# Write mode:
# - True  -> PUT to timeseries/<ts_ms>.json  (timestamp as key)
# - False -> POST to postlist.json
USE_TIMESTAMP_KEY = True

TIMESERIES_NODE = "timeseries"
POSTLIST_NODE = "postlist"

# Upload rate (seconds)
UPLOAD_PERIOD_S = 0.1  # 10 Hz

# ---------------- I2C setup ----------------
bus = smbus2.SMBus(1)

FXOS_ADDR = 0x1F   # accel + mag
FXAS_ADDR = 0x21   # gyro

# ---------------- FXOS8700 registers ----------------
FXOS_WHOAMI = 0x0D
FXOS_CTRL_REG1 = 0x2A
FXOS_OUT_X_MSB = 0x01
FXOS_M_OUT_X_MSB = 0x33
FXOS_M_CTRL_REG1 = 0x5B
FXOS_M_CTRL_REG2 = 0x5C

# ---------------- FXAS21002C registers ----------------
FXAS_WHOAMI = 0x0C
FXAS_CTRL_REG0 = 0x0D
FXAS_CTRL_REG1 = 0x13
FXAS_OUT_X_MSB = 0x01

# ---------------- Scale factors ----------------
ACC_COUNTS_PER_G = 4096.0
G = 9.80665
GYRO_COUNTS_PER_DPS = 16.4
MAG_UT_PER_COUNT = 0.1
FALL_THRESHOLD_MPS2 = 25.0

# ---------------- Helpers ----------------
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

# ---------------- Unit conversions ----------------
def accel_raw_to_mps2(raw):
    return (raw / ACC_COUNTS_PER_G) * G

def gyro_raw_to_rads(raw):
    return (raw / GYRO_COUNTS_PER_DPS) * (math.pi / 180.0)

def mag_raw_to_uT(raw):
    return raw * MAG_UT_PER_COUNT

def total_accel_mps2(ax_mps2, ay_mps2, az_mps2):
    return math.sqrt(ax_mps2**2 + ay_mps2**2 + az_mps2**2)

# ---------------- Init functions ----------------
def fxos_init():
    ctrl1 = read_u8(FXOS_ADDR, FXOS_CTRL_REG1)
    write_u8(FXOS_ADDR, FXOS_CTRL_REG1, ctrl1 & ~0x01)
    time.sleep(0.05)
    write_u8(FXOS_ADDR, FXOS_M_CTRL_REG1, 0x1F)
    write_u8(FXOS_ADDR, FXOS_M_CTRL_REG2, 0x20)
    write_u8(FXOS_ADDR, FXOS_CTRL_REG1, (ctrl1 & 0xFE) | 0x01)
    time.sleep(0.05)

def fxas_init():
    write_u8(FXAS_ADDR, FXAS_CTRL_REG1, 0x00)
    time.sleep(0.05)
    write_u8(FXAS_ADDR, FXAS_CTRL_REG0, 0x00)
    write_u8(FXAS_ADDR, FXAS_CTRL_REG1, 0x0E)
    time.sleep(0.05)

# ---------------- Read functions ----------------
def fxos_read_accel():
    d = read_block(FXOS_ADDR, FXOS_OUT_X_MSB, 6)
    return (
        twos_complement((d[0] << 8) | d[1], 16) >> 2,
        twos_complement((d[2] << 8) | d[3], 16) >> 2,
        twos_complement((d[4] << 8) | d[5], 16) >> 2,
    )

def fxos_read_mag():
    d = read_block(FXOS_ADDR, FXOS_M_OUT_X_MSB, 6)
    return (
        twos_complement((d[0] << 8) | d[1], 16),
        twos_complement((d[2] << 8) | d[3], 16),
        twos_complement((d[4] << 8) | d[5], 16),
    )

def fxas_read_gyro():
    d = read_block(FXAS_ADDR, FXAS_OUT_X_MSB, 6)
    return (
        twos_complement((d[0] << 8) | d[1], 16),
        twos_complement((d[2] << 8) | d[3], 16),
        twos_complement((d[4] << 8) | d[5], 16),
    )

# ---------------- Firebase upload ----------------
def upload_timeseries(payload):
    if USE_TIMESTAMP_KEY:
        ts_ms = int(payload["ts"] * 1000)
        path = f"{TIMESERIES_NODE}/{ts_ms}.json"
        r = requests.put(DB + path, json=payload, timeout=5)
    else:
        r = requests.post(DB + f"{POSTLIST_NODE}.json", json=payload, timeout=5)

    if not r.ok:
        raise ConnectionError(r.text)

def upload_latest(payload):
    r = requests.put(DB + "latest.json", json=payload, timeout=5)
    if not r.ok:
        raise ConnectionError(r.text)

# ---------------- Main ----------------
def main():
    try:
        print(f"FXOS WHOAMI: 0x{read_u8(FXOS_ADDR, FXOS_WHOAMI):02X}")
        print(f"FXAS WHOAMI: 0x{read_u8(FXAS_ADDR, FXAS_WHOAMI):02X}")
    except OSError:
        print("I2C error - check wiring and addresses")
        return

    fxos_init()
    fxas_init()

    print("Uploading IMU data to Firebase (timeseries + latest)\n")

    next_t = time.time()

    while True:
        if time.time() < next_t:
            time.sleep(next_t - time.time())
        next_t += UPLOAD_PERIOD_S

        ax, ay, az = fxos_read_accel()
        gx, gy, gz = fxas_read_gyro()
        mx, my, mz = fxos_read_mag()

        payload = {
            "sensor": "nxp_9dof",
            "ts": time.time(),
            "accel_mps2": {
                "x": round(accel_raw_to_mps2(ax), 4),
                "y": round(accel_raw_to_mps2(ay), 4),
                "z": round(accel_raw_to_mps2(az), 4),
            },
            "gyro_rads": {
                "x": round(gyro_raw_to_rads(gx), 6),
                "y": round(gyro_raw_to_rads(gy), 6),
                "z": round(gyro_raw_to_rads(gz), 6),
            },
            "mag_uT": {
                "x": round(mag_raw_to_uT(mx), 3),
                "y": round(mag_raw_to_uT(my), 3),
                "z": round(mag_raw_to_uT(mz), 3),
            },
        }

        total_accel = total_accel_mps2(
            payload["accel_mps2"]["x"],
            payload["accel_mps2"]["y"],
            payload["accel_mps2"]["z"],
        )
        payload["total_accel_mps2"] = round(total_accel, 3)
        payload["fall"] = total_accel >= FALL_THRESHOLD_MPS2

        # ?? write BOTH
        upload_timeseries(payload)
        upload_latest(payload)

        print(f"Uploaded @ {payload['ts']:.3f}")

if __name__ == "__main__":
    main()
