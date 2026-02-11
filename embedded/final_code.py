# -*- coding: utf-8 -*-
"""
Final code

9 DOF + temp
Sleepwaling + fall detection
http-> firebase
"""

import time
import math
import smbus2
from collections import deque
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# Firebase HTTP
DB = "https://embedded-zenith-default-rtdb.firebaseio.com/"
TIMESERIES_NODE = "timeseries"

KEYFILE = "/home/pi/embedded-zenith-firebase-adminsdk-fbsvc-92e37b3ef2.json"
SCOPES = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/firebase.database",
]

credentials = service_account.Credentials.from_service_account_file(KEYFILE, scopes=SCOPES)
session = AuthorizedSession(credentials)

 
UPLOAD_PERIOD = 1.0 


def upload_timeseries(payload: dict) -> None:
    """Write a timestamped record into /timeseries/<epoch_ms>."""
    ts_ms = int(payload["ts"] * 1000)
    path = f"{TIMESERIES_NODE}/{ts_ms}.json"
    r = session.put(DB + path, json=payload, timeout=10)
    if not r.ok:
        raise ConnectionError(f"Timeseries write failed: {r.status_code} {r.text}")


def upload_latest(payload: dict) -> None:
    """Overwrite /latest (the app usually reads this)."""
    r = session.put(DB + "latest.json", json=payload, timeout=10)
    if not r.ok:
        raise ConnectionError(f"Latest write failed: {r.status_code} {r.text}")


# I2C setup 
bus = smbus2.SMBus(1)

#  9DOF (NXP) 
FXOS_ADDR = 0x1F   # accel 
FXAS_ADDR = 0x21   # gyro   

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

#  TMP006 temperature sensor 
TMP006_ADDR = 0x40  # 
TMP006_REG_VOBJ = 0x00
TMP006_REG_TDIE = 0x01

# Scaling for units
ACC_COUNTS_PER_G = 4096.0
G = 9.80665
G0 = 9.80665
GYRO_COUNTS_PER_DPS = 16.4


# I2C helpers 
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


# Math helpers/ converstions
def accel_raw_to_mps2(raw):
    return (raw / ACC_COUNTS_PER_G) * G


def gyro_raw_to_rads(raw):
    return (raw / GYRO_COUNTS_PER_DPS) * (math.pi / 180.0)


def mag3(x, y, z):
    return math.sqrt(x * x + y * y + z * z)


def variance(vals):
    if len(vals) < 5:
        return 999.0
    m = sum(vals) / len(vals)
    return sum((v - m) ** 2 for v in vals) / (len(vals) - 1)


#  IMU init + reads 
def fxos_init():
    # Put accel in standby before config
    ctrl1 = read_u8(FXOS_ADDR, FXOS_CTRL_REG1)
    write_u8(FXOS_ADDR, FXOS_CTRL_REG1, ctrl1 & ~0x01)
    time.sleep(0.05)

    # Enable hybrid mode (accel + mag)
    write_u8(FXOS_ADDR, FXOS_M_CTRL_REG1, 0x1F)
    write_u8(FXOS_ADDR, FXOS_M_CTRL_REG2, 0x20)

    # Back to active mode
    write_u8(FXOS_ADDR, FXOS_CTRL_REG1, (ctrl1 & 0xFE) | 0x01)
    time.sleep(0.05)


def fxas_init():
    # Gyro standby
    write_u8(FXAS_ADDR, FXAS_CTRL_REG1, 0x00)
    time.sleep(0.05)

    # +-2000 dps
    write_u8(FXAS_ADDR, FXAS_CTRL_REG0, 0x00)

    # Active
    write_u8(FXAS_ADDR, FXAS_CTRL_REG1, 0x0E)
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


# TMP006 reads 
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
    return signed * 0.15625


# Fall detection parameters 
# Freefall -> impact -> confirm stillness

FREEFALL_G_MAX = 0.4
IMPACT_G_MIN = 2.5
POST_STILL_GYRO_MAX = 0.35
POST_STILL_VAR_MAX = 0.20
FREEFALL_WINDOW_S = 0.35
IMPACT_WINDOW_S = 0.8
POST_STILL_WINDOW_S = 1.2

IDLE = 0
FREEFALL = 1
IMPACT = 2
CONFIRM = 3
FALL_STATE_NAME = {IDLE: "IDLE", FREEFALL: "FREEFALL", IMPACT: "IMPACT", CONFIRM: "CONFIRM"}


# Sleepwalking parameters 
SLEEP_GYRO_MAX = 0.12
SLEEP_VAR_MAX = 0.0060      # var(a_g) in g^2
SLEEP_MIN_TIME = 12 * 60    # set to 15.0 for desk testing

MOBILE_GYRO_MIN = 0.18
MOBILE_VAR_MIN = 0.0080     # g^2


WALK_GYRO_MIN = 0.22
WALK_GYRO_MAX = 3.0
WALK_VAR_MIN = 0.0120      

SW_WALK_WINDOW_S = 1.5     
SLEEPWALK_CONFIRM_TIME = 30.0  

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
    try:
        print(f"FXOS WHOAMI: 0x{read_u8(FXOS_ADDR, FXOS_WHOAMI):02X}")
        print(f"FXAS WHOAMI: 0x{read_u8(FXAS_ADDR, FXAS_WHOAMI):02X}")
        _ = tmp006_read_u16(TMP006_REG_TDIE)
        print("TMP006: read OK")
    except OSError:
        print("I2C error: check wiring, I2C enabled, addresses.")
        return

    fxos_init()
    fxas_init()

    print("\nRunning: IMU 50Hz | fall + sleepwalking | TMP006 1Hz | Firebase upload 1Hz")
    print(f"DB: {DB}\n")

    # Timing 
    sample_hz = 50.0
    dt = 1.0 / sample_hz
    next_sample_t = time.time()
    next_slow_t = time.time()  # 1 Hz tasks: temp + upload

    # Fall detector state 
    fall_state = IDLE
    fall_t_state = time.time()
    fall_a_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    fall_w_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    cooldown_until = 0.0

    # Sleepwalking state + buffers 
    SW_SLEEP_WINDOW_S = 20.0
    sw_sleep_ag_buf = deque(maxlen=int(SW_SLEEP_WINDOW_S * sample_hz))
    sw_sleep_w_buf = deque(maxlen=int(SW_SLEEP_WINDOW_S * sample_hz))

    sw_walk_ag_buf = deque(maxlen=int(SW_WALK_WINDOW_S * sample_hz))
    sw_walk_w_buf = deque(maxlen=int(SW_WALK_WINDOW_S * sample_hz))

    sw_state = SW_AWAKE
    still_start_t = None
    walk_start_t = None
    sleepwalking_event = "NONE"

    #  TMP006 cached values
    latest_tmp_die_c = None
    latest_tmp_vobj_uV = None
    ts_tmp = None

    try:
        while True:
            # Keep a steady 50 Hz IMU loop
            now = time.time()
            if now < next_sample_t:
                time.sleep(next_sample_t - now)
            next_sample_t += dt
            t = time.time()

            # read IMU
            ax, ay, az = fxos_read_accel_mps2()
            gx, gy, gz = fxas_read_gyro_rads()

            a_mag = mag3(ax, ay, az)
            a_g = a_mag / G0
            w_mag = mag3(gx, gy, gz)

        
            # Sleepwalking detector (runs @50hz)
            
            sleepwalking_event = "NONE"

            #  buffers (for stillness detection)
            sw_sleep_ag_buf.append(a_g)
            sw_sleep_w_buf.append(w_mag)

            #  short-window buffers (for movement + walking-like detection)
            sw_walk_ag_buf.append(a_g)
            sw_walk_w_buf.append(w_mag)

            # Long window features: "am I basically still?"
            sleep_var_ag = variance(list(sw_sleep_ag_buf)) if len(sw_sleep_ag_buf) >= 25 else 999.0
            sleep_mean_w = (sum(sw_sleep_w_buf) / len(sw_sleep_w_buf)) if len(sw_sleep_w_buf) >= 25 else 999.0
            is_still = (sleep_mean_w <= SLEEP_GYRO_MAX) and (sleep_var_ag <= SLEEP_VAR_MAX)

            # Short window features: "am I moving right now?"
            walk_var_ag = variance(list(sw_walk_ag_buf)) if len(sw_walk_ag_buf) >= 10 else 999.0
            walk_mean_w = (sum(sw_walk_w_buf) / len(sw_walk_w_buf)) if len(sw_walk_w_buf) >= 10 else 999.0

            mobile_like = (walk_mean_w >= MOBILE_GYRO_MIN) or (walk_var_ag >= MOBILE_VAR_MIN)

            walking_like = (
                (WALK_GYRO_MIN <= walk_mean_w <= WALK_GYRO_MAX)
                and (walk_var_ag >= WALK_VAR_MIN)
                and (not is_still)  # must be actively moving (prevents "trigger when put down")
            )

            # State machine
            if sw_state == SW_AWAKE:
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= SLEEP_MIN_TIME:
                        sw_state = SW_ASLEEP
                        walk_start_t = None
                else:
                    still_start_t = None

            elif sw_state == SW_ASLEEP:
                if mobile_like and not is_still:
                    sw_state = SW_MOBILE
                    still_start_t = None
                    walk_start_t = None

            elif sw_state == SW_MOBILE:
                # if still go back to sleep
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= 10.0:
                        sw_state = SW_ASLEEP
                        walk_start_t = None
                else:
                    still_start_t = None

                # Confirm sleepwalking while walking is true
                if walking_like:
                    if walk_start_t is None:
                        walk_start_t = t
                    elif (t - walk_start_t) >= SLEEPWALK_CONFIRM_TIME:
                        sw_state = SW_SLEEPWALKING
                        sleepwalking_event = "SLEEPWALKING_DETECTED"
                else:
                    walk_start_t = None

            elif sw_state == SW_SLEEPWALKING:
                # Drop back to ASLEEP after being still for a while
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= 30.0:
                        sw_state = SW_ASLEEP
                        walk_start_t = None
                else:
                    still_start_t = None

            sleepwalking_flag = (sw_state == SW_SLEEPWALKING)

  
            # Fall detector (runs @50hertz)
      
            fall_event = "NONE"

            fall_a_mag_buf.append(a_mag)
            fall_w_mag_buf.append(w_mag)

            # make fall alram for 2 seconds
            if t < cooldown_until:
                fall_state = IDLE

            if fall_state == IDLE:
                if a_g <= FREEFALL_G_MAX:
                    fall_state = FREEFALL
                    fall_t_state = t
                    fall_a_mag_buf.clear()
                    fall_w_mag_buf.clear()

            elif fall_state == FREEFALL:
                if (t - fall_t_state) > FREEFALL_WINDOW_S:
                    fall_state = IDLE
                elif a_g >= IMPACT_G_MIN:
                    fall_state = IMPACT
                    fall_t_state = t
                    fall_a_mag_buf.clear()
                    fall_w_mag_buf.clear()

            elif fall_state == IMPACT:
                if (t - fall_t_state) > IMPACT_WINDOW_S:
                    fall_state = CONFIRM
                    fall_t_state = t

            elif fall_state == CONFIRM:
                if (t - fall_t_state) >= POST_STILL_WINDOW_S and len(fall_a_mag_buf) >= 10:
                    var_a = variance(list(fall_a_mag_buf))
                    mean_w = sum(fall_w_mag_buf) / max(1, len(fall_w_mag_buf))
                    if mean_w <= POST_STILL_GYRO_MAX and var_a <= POST_STILL_VAR_MAX:
                        fall_event = "FALL_DETECTED"
                        cooldown_until = t + 2.0
                        print("\nFALL DETECTED\n")
                    fall_state = IDLE

            fall_status = (t < cooldown_until)

       
            # 1 Hz block: temperature read + upload
           
            if t >= next_slow_t:
                next_slow_t += 1.0

                # Temperature read 
                try:
                    latest_tmp_die_c = round(float(tmp006_read_die_temp_c()), 3)
                    latest_tmp_vobj_uV = round(float(tmp006_read_vobj_uV()), 3)
                    ts_tmp = time.time()
                except OSError:
                    pass

                payload = {
                    "sensor": "imu50_fall_sleepwalk_tmp1",
                    "ts": time.time(),

                    # IMU snapshot (latest 50 Hz sample)
                    "accel_mps2": {"x": round(ax, 4), "y": round(ay, 4), "z": round(az, 4)},
                    "gyro_rads": {"x": round(gx, 6), "y": round(gy, 6), "z": round(gz, 6)},
                    "a_g": round(a_g, 3),
                    "w_rads": round(w_mag, 3),

                    # Fall detection output
                    "fall": bool(fall_status),
                    "event": fall_event,
                    "fall_state": FALL_STATE_NAME[fall_state],

                    # Sleepwalking output
                    "sleepwalking": bool(sleepwalking_flag),
                    "sleep_event": sleepwalking_event,
                    "sleep_state": SW_STATE_NAME[sw_state],

                    # Helpful debug so you can tune later
                    "sleep_features": {
                        "sleep_mean_w": round(sleep_mean_w, 6),
                        "sleep_var_ag": round(sleep_var_ag, 6),
                        "walk_mean_w": round(walk_mean_w, 6),
                        "walk_var_ag": round(walk_var_ag, 6),
                    },

                    # Temperature snapshot
                    "tmp_die_c": latest_tmp_die_c,
                    "tmp_vobj_uV": latest_tmp_vobj_uV,

                    "meta": {
                        "ts_imu": t,
                        "ts_tmp": ts_tmp,
                        "rates_hz": {"imu": 50, "tmp": 1, "upload": 1},
                    }
                }

                try:
                    upload_timeseries(payload)
                    upload_latest(payload)
                    print(
                        f"Uploaded @ {payload['ts']:.3f} | "
                        f"fall={payload['fall']} ({payload['event']}) | "
                        f"sleepwalking={payload['sleepwalking']} ({payload['sleep_event']}) | "
                        f"tmp={payload['tmp_die_c']}C"
                    )
                except Exception as e:
                    print("Upload failed:", e)

    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
