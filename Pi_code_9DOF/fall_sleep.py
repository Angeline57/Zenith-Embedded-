# -*- coding: utf-8 -*-
import time
import math
import smbus2
from collections import deque
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# ===================== Firebase (Authenticated HTTP) =====================
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
TIMESERIES_NODE = "timeseries"

KEYFILE = "/home/pi/embedded-zenith-firebase-adminsdk-fbsvc-92e37b3ef2.json"

SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/firebase.database",
]

credentials = service_account.Credentials.from_service_account_file(
    KEYFILE, scopes=SCOPES
)
session = AuthorizedSession(credentials)

UPLOAD_HZ = 1.0
UPLOAD_PERIOD = 1.0 / UPLOAD_HZ

def upload_timeseries(payload):
    ts_ms = int(payload["ts"] * 1000)
    path = f"{TIMESERIES_NODE}/{ts_ms}.json"
    r = session.put(DB + path, json=payload, timeout=10)
    if not r.ok:
        raise ConnectionError(f"Timeseries write failed: {r.status_code} {r.text}")

def upload_latest(payload):
    r = session.put(DB + "latest.json", json=payload, timeout=10)
    if not r.ok:
        raise ConnectionError(f"Latest write failed: {r.status_code} {r.text}")

# ===================== I2C setup =====================
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

# ---- TMP006 ----
TMP006_ADDR = 0x40  # default (alt 0x41)
TMP006_REG_VOBJ = 0x00
TMP006_REG_TDIE = 0x01

# ===================== Scaling =====================
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

# ===================== Sensor init (IMU) =====================
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
FREEFALL_G_MAX = 0.55
IMPACT_G_MIN = 1.7
POST_STILL_GYRO_MAX = 0.35
POST_STILL_VAR_MAX = 0.20
FREEFALL_WINDOW_S = 0.35
IMPACT_WINDOW_S = 1
POST_STILL_WINDOW_S = 1.2

# Fall states
IDLE = 0
FREEFALL = 1
IMPACT = 2
CONFIRM = 3
STATE_NAME = {IDLE: "IDLE", FREEFALL: "FREEFALL", IMPACT: "IMPACT", CONFIRM: "CONFIRM"}

# ===================== Sleepwalking detector thresholds (NO time gating) =====================
SLEEP_GYRO_MAX = 0.06        # rad/s
SLEEP_VAR_MAX = 0.025        # (m/s^2)^2 variance of accel magnitude
SLEEP_MIN_TIME = 30     # seconds

UPRIGHT_G_MIN = 0.85         # g
UPRIGHT_G_MAX = 1.25         # g
UPRIGHT_GYRO_MIN = 0.12      # rad/s

WALK_GYRO_MIN = 0.18         # rad/s
WALK_GYRO_MAX = 1.6          # rad/s
WALK_VAR_MIN  = 0.05         # (m/s^2)^2
WALK_MIN_TIME = 5.0         # seconds

SLEEPWALK_CONFIRM_TIME = 10.0 # seconds

# Sleepwalking states
SW_AWAKE = 0
SW_ASLEEP = 1
SW_MOBILE = 2
SW_SLEEPWALKING = 3
SW_STATE_NAME = {
    SW_AWAKE: "AWAKE",
    SW_ASLEEP: "ASLEEP",
    SW_MOBILE: "MOBILE_AFTER_SLEEP",
    SW_SLEEPWALKING: "SLEEPWALKING",
}

# ===================== Main =====================
def main():
    # Presence check
    try:
        print(f"FXOS WHOAMI: 0x{read_u8(FXOS_ADDR, FXOS_WHOAMI):02X}")
        print(f"FXAS WHOAMI: 0x{read_u8(FXAS_ADDR, FXAS_WHOAMI):02X}")
        _ = tmp006_read_u16(TMP006_REG_TDIE)
        print("TMP006: read OK")
    except OSError:
        print("I2C error - check wiring/I2C/addresses.")
        return

    fxos_init()
    fxas_init()

    print("\nIMU @50Hz | Fall detection @50Hz | Sleepwalking detection (no time gating) | TMP006 @1Hz | Uploads @1Hz")
    print(f"DB: {DB}\n")

    # sampling
    sample_hz = 50.0
    dt = 1.0 / sample_hz
    next_sample_t = time.time()

    # 1 Hz tasks timing (TMP006 + upload)
    next_slow_t = time.time()

    # fall state machine
    state = IDLE
    t_state = time.time()

    a_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    gyro_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    cooldown_until = 0.0

    # sleepwalking state machine buffers/state
    SW_WINDOW_S = 20.0
    sw_a_mag_buf = deque(maxlen=int(SW_WINDOW_S * sample_hz))
    sw_w_mag_buf = deque(maxlen=int(SW_WINDOW_S * sample_hz))

    sw_state = SW_AWAKE
    still_start_t = None
    mobile_start_t = None
    walk_start_t = None
    sleepwalking_event = "NONE"
    sleepwalking_flag = False
    sw_var_a = 999.0
    sw_mean_w = 999.0

    # TMP006 values
    latest_tmp_die_c = None
    latest_tmp_vobj_uV = None
    ts_tmp = None

    latest_payload = None

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

            # buffers for fall confirm stage
            a_mag_buf.append(a_mag)
            gyro_mag_buf.append(w_mag)

            # ===================== Sleepwalking detection (NO time gating) =====================
            sleepwalking_event = "NONE"

            sw_a_mag_buf.append(a_mag)
            sw_w_mag_buf.append(w_mag)

            if len(sw_a_mag_buf) >= 25:
                sw_var_a = variance(list(sw_a_mag_buf))
                sw_mean_w = sum(sw_w_mag_buf) / max(1, len(sw_w_mag_buf))
            else:
                sw_var_a = 999.0
                sw_mean_w = 999.0

            is_still = (sw_mean_w <= SLEEP_GYRO_MAX) and (sw_var_a <= SLEEP_VAR_MAX)
            is_uprightish = (UPRIGHT_G_MIN <= a_g <= UPRIGHT_G_MAX) and (w_mag >= UPRIGHT_GYRO_MIN)

            walking_like = (
                (WALK_GYRO_MIN <= sw_mean_w <= WALK_GYRO_MAX) and
                (sw_var_a >= WALK_VAR_MIN) and
                (UPRIGHT_G_MIN <= a_g <= UPRIGHT_G_MAX)
            )

            if sw_state == SW_AWAKE:
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= SLEEP_MIN_TIME:
                        sw_state = SW_ASLEEP
                        mobile_start_t = None
                        walk_start_t = None
                else:
                    still_start_t = None

            elif sw_state == SW_ASLEEP:
                if is_uprightish and not is_still:
                    sw_state = SW_MOBILE
                    mobile_start_t = t
                    walk_start_t = None

            elif sw_state == SW_MOBILE:
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= 10.0:
                        sw_state = SW_ASLEEP
                        mobile_start_t = None
                        walk_start_t = None
                else:
                    still_start_t = None

                if walking_like:
                    if walk_start_t is None:
                        walk_start_t = t
                    else:
                        # Confirm sleepwalking when walking persists long enough
                        if (t - walk_start_t) >= SLEEPWALK_CONFIRM_TIME:
                            sw_state = SW_SLEEPWALKING
                            sleepwalking_event = "SLEEPWALKING_DETECTED"
                else:
                    walk_start_t = None

            elif sw_state == SW_SLEEPWALKING:
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= 30.0:
                        sw_state = SW_ASLEEP
                        mobile_start_t = None
                        walk_start_t = None
                else:
                    still_start_t = None

            sleepwalking_flag = (sw_state == SW_SLEEPWALKING)

            # ===================== Fall detection state machine =====================
            event = "NONE"

            # cooldown suppresses repeated triggers
            if t < cooldown_until:
                state = IDLE

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
                        print("\n⚠️ FALL DETECTED")
                        print(f"  a_g(last)={a_g:.2f}g | mean gyro={mean_w:.3f} rad/s | accel var={var_a:.3f}\n")

                    state = IDLE

            fall_status = (t < cooldown_until)

            # ===================== 1 Hz block: TMP006 + Upload =====================
            if t >= next_slow_t:
                next_slow_t += 1.0

                # TMP006 @1 Hz
                try:
                    latest_tmp_die_c = round(float(tmp006_read_die_temp_c()), 3)
                    latest_tmp_vobj_uV = round(float(tmp006_read_vobj_uV()), 3)
                    ts_tmp = time.time()
                except OSError:
                    pass

                # Build payload for upload (uses latest 50Hz IMU sample)
                latest_payload = {
                    "sensor": "imu50_fall_sleepwalk_tmp1",
                    "ts": time.time(),

                    # IMU (latest sample)
                    "accel_mps2": {"x": round(ax, 4), "y": round(ay, 4), "z": round(az, 4)},
                    "gyro_rads": {"x": round(gx, 6), "y": round(gy, 6), "z": round(gz, 6)},
                    "a_g": round(a_g, 3),
                    "w_rads": round(w_mag, 3),

                    # Fall detection
                    "fall": bool(fall_status),
                    "event": event,
                    "fall_state": STATE_NAME[state],

                    # Sleepwalking detection
                    "sleepwalking": bool(sleepwalking_flag),
                    "sleep_event": sleepwalking_event,
                    "sleep_state": SW_STATE_NAME[sw_state],
                    "sleep_features": {
                        "var_a": round(sw_var_a, 6),
                        "mean_w": round(sw_mean_w, 6),
                    },

                    # Temperature
                    "tmp_die_c": latest_tmp_die_c,
                    "tmp_vobj_uV": latest_tmp_vobj_uV,

                    "meta": {
                        "ts_imu": t,
                        "ts_tmp": ts_tmp,
                        "rates_hz": {"imu": 50, "tmp": 1, "upload": 1},
                    }
                }

                # Upload @1 Hz
                try:
                    upload_timeseries(latest_payload)
                    upload_latest(latest_payload)
                    print(
                        f"Uploaded @ {latest_payload['ts']:.3f} | "
                        f"fall={latest_payload['fall']} ({latest_payload['event']}) | "
                        f"sleepwalking={latest_payload['sleepwalking']} ({latest_payload['sleep_event']}) | "
                        f"tmp={latest_payload['tmp_die_c']}C"
                    )
                except Exception as e:
                    print("Upload failed:", e)

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
