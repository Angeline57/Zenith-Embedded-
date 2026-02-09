# -*- coding: utf-8 -*-
import time
import math
import smbus2
import requests
from collections import deque

# ===================== Firebase (HTTP) =====================
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
TIMESERIES_NODE = "timeseries"
session = requests.Session()    # request a communication session for connection with firebase 

UPLOAD_HZ = 1.0
UPLOAD_PERIOD = 1.0 / UPLOAD_HZ

# saves data with unique timestamp key (for historical record)
def upload_timeseries(payload):
    ts_ms = int(payload["ts"] * 1000)
    path = f"{TIMESERIES_NODE}/{ts_ms}.json"
    r = session.put(DB + path, json=payload, timeout=5)
    if not r.ok:
        raise ConnectionError(f"Timeseries write failed: {r.status_code} {r.text}")

# saves data to /latest (overwrites previous, for easy retrieval of most recent state)
def upload_latest(payload):
    r = session.put(DB + "latest.json", json=payload, timeout=5)
    if not r.ok:
        raise ConnectionError(f"Latest write failed: {r.status_code} {r.text}")

# ===================== I2C (communication protocol) setup =====================
bus = smbus2.SMBus(1)

# ---- 9DOF (NXP) ----
FXOS_ADDR = 0x1F   # accel + mag (try 0x1E if not found)
FXAS_ADDR = 0x21   # gyro       (try 0x20 if not found)

# FXOS8700 registers
FXOS_WHOAMI = 0x0D
FXOS_CTRL_REG1 = 0x2A
FXOS_OUT_X_MSB = 0x01
FXOS_M_CTRL_REG1 = 0x5B
FXOS_M_CTRL_REG2 = 0x5C

# FXAS21002C registers
FXAS_WHOAMI = 0x0C
FXAS_CTRL_REG0 = 0x0D
FXAS_CTRL_REG1 = 0x13
FXAS_OUT_X_MSB = 0x01

# ---- VL53L0X (ToF) ----
VL53_ADDR = 0x29
VL53_MEAS_WAIT_S = 0.040  # working method: trigger + fixed wait

# ---- TMP006 ----
TMP006_ADDR = 0x40  # default (alt 0x41)
TMP006_REG_VOBJ = 0x00
TMP006_REG_TDIE = 0x01

# ===================== Scaling =====================
# scaling factors tell the code how to convert the raw electrical signal into actual $9.8 m/s^2$ gravity units.
ACC_COUNTS_PER_G = 4096.0
G = 9.80665
G0 = 9.80665
GYRO_COUNTS_PER_DPS = 16.4

# ===================== Helpers =====================
def read_u8(addr, reg):
    return bus.read_byte_data(addr, reg & 0xFF)

def write_u8(addr, reg, val):
    bus.write_byte_data(addr, reg & 0xFF, val & 0xFF)

def read_block(addr, reg, length):
    return bus.read_i2c_block_data(addr, reg & 0xFF, length)

# two's complement helper for signed values (e.g. accel/gyro readings) 
# that come as unsigned integers from the sensor
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

# FXOS: accel and mag on same chip, read together in one block read
# the NXP 9-axis sensor system has this two chip system
def fxos_read_accel_mps2():
    d = read_block(FXOS_ADDR, FXOS_OUT_X_MSB, 6)
    ax = twos_complement((d[0] << 8) | d[1], 16) >> 2
    ay = twos_complement((d[2] << 8) | d[3], 16) >> 2
    az = twos_complement((d[4] << 8) | d[5], 16) >> 2
    return (accel_raw_to_mps2(ax), accel_raw_to_mps2(ay), accel_raw_to_mps2(az))

# FXAS: gyro on separate chip, read in its own block read
def fxas_read_gyro_rads():
    d = read_block(FXAS_ADDR, FXAS_OUT_X_MSB, 6)
    gx = twos_complement((d[0] << 8) | d[1], 16)
    gy = twos_complement((d[2] << 8) | d[3], 16)
    gz = twos_complement((d[4] << 8) | d[5], 16)
    return (gyro_raw_to_rads(gx), gyro_raw_to_rads(gy), gyro_raw_to_rads(gz))

# ===================== VL53L0X (working single-shot read) =====================
def vl53_write8(reg, val):
    bus.write_byte_data(VL53_ADDR, reg & 0xFF, val & 0xFF)

def vl53_read8(reg):
    return bus.read_byte_data(VL53_ADDR, reg & 0xFF)

def vl53_single_shot_mm():
    vl53_write8(0x00, 0x01)           # SYSRANGE_START
    time.sleep(VL53_MEAS_WAIT_S)      # wait for measurement
    hi = vl53_read8(0x1E)
    lo = vl53_read8(0x1F)
    return (hi << 8) | lo

# ===================== TMP006 =====================
def tmp006_read_u16(reg):
    d = bus.read_i2c_block_data(TMP006_ADDR, reg & 0xFF, 2)
    return (d[0] << 8) | d[1]

def tmp006_read_die_temp_c():
    raw = tmp006_read_u16(TMP006_REG_TDIE)
    signed = twos_complement(raw, 16)
    temp_counts = signed >> 2
    return temp_counts * 0.03125

def tmp006_read_vobj_uV():
    raw = tmp006_read_u16(TMP006_REG_VOBJ)
    signed = twos_complement(raw, 16)
    return signed * 0.15625  # uV

# ===================== Fall detector thresholds =====================
FREEFALL_G_MAX = 0.4
IMPACT_G_MIN = 2.5
POST_STILL_GYRO_MAX = 0.35
POST_STILL_VAR_MAX = 0.20
FREEFALL_WINDOW_S = 0.35
IMPACT_WINDOW_S = 0.8
POST_STILL_WINDOW_S = 1.2

# ===================== On-Person Detection Config =====================
ambient_temp = 25.0  # Default starting value
on_person_threshold = 30.0  # Dynamically changes to ambient + TEMP_OFFSET
TEMP_OFFSET = 4.0    # How many degrees above room temp is "On Person"

# States
IDLE = 0
FREEFALL = 1    # in freefall, acceleration is below 0.4g, waiting for impact
IMPACT = 2      # detected impact (acceleration above 2.5g), waiting for stillness to confirm fall
CONFIRM = 3     # checking for stillness after impact to confirm fall (gyro below 0.35 rad/s and accel variance below 0.2 (g^2) in 1.2s window)
STATE_NAME = {IDLE: "IDLE", FREEFALL: "FREEFALL", IMPACT: "IMPACT", CONFIRM: "CONFIRM"}

# ===================== Main =====================
def main():
    # Presence check
    try:
        print(f"FXOS WHOAMI: 0x{read_u8(FXOS_ADDR, FXOS_WHOAMI):02X}")
        print(f"FXAS WHOAMI: 0x{read_u8(FXAS_ADDR, FXAS_WHOAMI):02X}")
        print(f"VL53 MODEL_ID: 0x{vl53_read8(0xC0):02X} (often 0xEE)")
        _ = tmp006_read_u16(TMP006_REG_TDIE)
        print("TMP006: read OK")
    except OSError:
        print("I2C error - check wiring/I2C/addresses.")
        return

    fxos_init()
    fxas_init()

    print("\nFall detection @50Hz, ToF @1Hz, TMP006 @1Hz, uploads @1Hz (Ctrl+C to stop)")
    print(f"DB: {DB}\n")

    # detection sampling
    sample_hz = 50.0
    dt = 1.0 / sample_hz
    next_sample_t = time.time()

    # 1 Hz tasks timing
    next_slow_t = time.time()   # ToF + TMP006 + Upload in one 1Hz block

    # fall state machine
    state = IDLE
    t_state = time.time()

    a_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    gyro_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))

    cooldown_until = 0.0

    # Latest sensor values (persist between uploads)
    latest_tof_mm = None
    ts_tof = None

    latest_tmp_die_c = None
    latest_tmp_vobj_uV = None
    ts_tmp = None

    latest_payload = None

    # --- CALIBRATION STEP ---
    print("Calibrating ambient temperature... keep device on table.")
    temp_samples = []
    for _ in range(3):
        try:
            temp_samples.append(tmp006_read_die_temp_c())
        except OSError:
            pass
        time.sleep(1)
    
    if temp_samples:
        ambient_temp = sum(temp_samples) / len(temp_samples)
        on_person_threshold = ambient_temp + TEMP_OFFSET
        print(f"Calibration Done. Ambient: {ambient_temp:.1f}C. Threshold: {on_person_threshold:.1f}C")


    try:
        while True:
            # fixed-rate sampling (50 Hz loop)
            now = time.time()
            if now < next_sample_t:
                time.sleep(next_sample_t - now)
            next_sample_t += dt

            t = time.time()

            # ---- 9DOF read @50Hz ----
            ax, ay, az = fxos_read_accel_mps2()
            gx, gy, gz = fxas_read_gyro_rads()

            a_mag = mag3(ax, ay, az)
            a_g = a_mag / G0
            w_mag = mag3(gx, gy, gz)

            a_mag_buf.append(a_mag)
            gyro_mag_buf.append(w_mag)

            event = "NONE"

            # cooldown suppresses repeated triggers
            if t < cooldown_until:
                state = IDLE

            # ----- fall detection state machine -----
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
                        event = "FALL_DETECTED"
                        cooldown_until = t + 2.0  # keep alarm true for 2s
                        print("\n?? FALL DETECTED")
                        print(f"  a_g(last)={a_g:.2f}g | mean gyro={mean_w:.3f} rad/s | accel var={var_a:.3f}\n")

                    state = IDLE

            fall_status = (t < cooldown_until)

            # ---- 1 Hz block: ToF + TMP006 + Upload ----
            if t >= next_slow_t:
                next_slow_t += 1.0

                # ToF @1 Hz (working method)
                try:
                    latest_tof_mm = int(vl53_single_shot_mm())
                    ts_tof = time.time()
                except OSError:
                    pass

                # TMP006 @1 Hz
                try:
                    latest_tmp_die_c = round(float(tmp006_read_die_temp_c()), 3)
                    latest_tmp_vobj_uV = round(float(tmp006_read_vobj_uV()), 3)
                    ts_tmp = time.time()
                except OSError:
                    pass

                # Inside the 'if t >= next_slow_t:' block (Device on-person check using TMP006)
                try:
                    latest_tmp_die_c = round(float(tmp006_read_die_temp_c()), 3)
                    
                    # LOGIC: Check if it's on the person
                    device_on_person = latest_tmp_die_c > on_person_threshold
                    
                    latest_tmp_vobj_uV = round(float(tmp006_read_vobj_uV()), 3)
                    ts_tmp = time.time()
                except OSError:
                    device_on_person = False

                # Build payload for upload
                latest_payload = {
                    "sensor": "imu50_fall_tof1_tmp1",
                    "ts": time.time(),
                    "device_on_person": bool(device_on_person), 
                    "fall": bool(fall_status),
                    "event": event,
                    "fall_state": STATE_NAME[state],

                    # IMU Data
                    "accel_mps2": {"x": round(ax, 4), "y": round(ay, 4), "z": round(az, 4)},
                    "gyro_rads": {"x": round(gx, 6), "y": round(gy, 6), "z": round(gz, 6)},
                    "a_g": round(a_g, 3),
                    "w_rads": round(w_mag, 3),

                    # ToF + Temperature
                    "tof_mm": latest_tof_mm,
                    "tmp_die_c": latest_tmp_die_c,
                    "tmp_vobj_uV": latest_tmp_vobj_uV,

                    "meta": {
                        "ts_imu": t,
                        "ts_tof": ts_tof,
                        "ts_tmp": ts_tmp,
                        "rates_hz": {"imu": 50, "tof": 1, "tmp": 1, "upload": 1},
                    }
                }

                # Upload @1 Hz
                try:
                    upload_timeseries(latest_payload)
                    upload_latest(latest_payload)
                    print(
                        f"Uploaded @ {latest_payload['ts']:.3f} | "
                        f"fall={latest_payload['fall']} | event={latest_payload['event']} | "
                        f"tof={latest_payload['tof_mm']}mm | tmp={latest_payload['tmp_die_c']}C"
                    )
                except Exception as e:
                    print("Upload failed:", e)

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
