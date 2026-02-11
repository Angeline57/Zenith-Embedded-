# -*- coding: utf-8 -*-
"""
NXP 9DOF (FXOS8700 accel + FXAS21002 gyro)
- Fall detection @50 Hz
- Sleepwalking detection @50 Hz (NO time gating)
- Desk-test friendly: triggers sleepwalking while you are moving it (not only after you put it down)
No HTTP / Firebase.
"""

import time
import math
import smbus2
from collections import deque

# ===================== I2C setup =====================
bus = smbus2.SMBus(1)

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

IDLE = 0
FREEFALL = 1
IMPACT = 2
CONFIRM = 3
FALL_STATE_NAME = {IDLE: "IDLE", FREEFALL: "FREEFALL", IMPACT: "IMPACT", CONFIRM: "CONFIRM"}

# ===================== Sleepwalking detector (DESK TEST + sensitive) =====================
# Stillness detection (desk)
SLEEP_GYRO_MAX = 0.12     # rad/s
SLEEP_VAR_MAX  = 0.0060   # var(a_g) in g^2
SLEEP_MIN_TIME = 15.0     # seconds (desk test)

# Movement-after-sleep trigger (short window)
MOBILE_GYRO_MIN = 0.18    # rad/s
MOBILE_VAR_MIN  = 0.0080  # g^2

# Walking-like detection (short window, no upright gating)
WALK_GYRO_MIN = 0.22
WALK_GYRO_MAX = 3.0
WALK_VAR_MIN  = 0.0120    # g^2

SW_WALK_WINDOW_S = 1.5    # seconds (very responsive)
SLEEPWALK_CONFIRM_TIME = 5.0  # seconds (desk test)

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
    try:
        print(f"FXOS WHOAMI: 0x{read_u8(FXOS_ADDR, FXOS_WHOAMI):02X}")
        print(f"FXAS WHOAMI: 0x{read_u8(FXAS_ADDR, FXAS_WHOAMI):02X}")
    except OSError:
        print("I2C error - check wiring/I2C/addresses.")
        return

    fxos_init()
    fxas_init()

    sample_hz = 50.0
    dt = 1.0 / sample_hz
    next_sample_t = time.time()

    # ---- Fall state machine ----
    fall_state = IDLE
    fall_t_state = time.time()
    fall_a_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    fall_w_mag_buf = deque(maxlen=int(POST_STILL_WINDOW_S * sample_hz))
    cooldown_until = 0.0

    # ---- Sleepwalking buffers ----
    SW_SLEEP_WINDOW_S = 20.0
    sw_sleep_ag_buf = deque(maxlen=int(SW_SLEEP_WINDOW_S * sample_hz))
    sw_sleep_w_buf  = deque(maxlen=int(SW_SLEEP_WINDOW_S * sample_hz))

    sw_walk_ag_buf = deque(maxlen=int(SW_WALK_WINDOW_S * sample_hz))
    sw_walk_w_buf  = deque(maxlen=int(SW_WALK_WINDOW_S * sample_hz))

    sw_state = SW_AWAKE
    still_start_t = None
    walk_start_t = None
    last_sw_state = sw_state

    next_status_print = time.time()

    print("\nRunning: IMU @50Hz | Fall + Sleepwalking (desk-test sensitive, no HTTP)")
    print("Desk test: hold still ~15s => ASLEEP, then move up/down ~5-8s => SLEEPWALKING\n")

    try:
        while True:
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

            # ===================== Sleepwalking detection =====================
            sw_sleep_ag_buf.append(a_g)
            sw_sleep_w_buf.append(w_mag)

            sw_walk_ag_buf.append(a_g)
            sw_walk_w_buf.append(w_mag)

            # Long window: stillness
            sleep_var_ag = variance(list(sw_sleep_ag_buf)) if len(sw_sleep_ag_buf) >= 25 else 999.0
            sleep_mean_w = (sum(sw_sleep_w_buf) / len(sw_sleep_w_buf)) if len(sw_sleep_w_buf) >= 25 else 999.0
            is_still = (sleep_mean_w <= SLEEP_GYRO_MAX) and (sleep_var_ag <= SLEEP_VAR_MAX)

            # Short window: movement + walking-like
            walk_var_ag = variance(list(sw_walk_ag_buf)) if len(sw_walk_ag_buf) >= 10 else 999.0
            walk_mean_w = (sum(sw_walk_w_buf) / len(sw_walk_w_buf)) if len(sw_walk_w_buf) >= 10 else 999.0

            mobile_like = (walk_mean_w >= MOBILE_GYRO_MIN) or (walk_var_ag >= MOBILE_VAR_MIN)

            walking_like = (
                (WALK_GYRO_MIN <= walk_mean_w <= WALK_GYRO_MAX) and
                (walk_var_ag >= WALK_VAR_MIN) and
                (not is_still)  # must be moving now
            )

            sleepwalking_event = "NONE"

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
                # go back to asleep if still for 10s
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= 10.0:
                        sw_state = SW_ASLEEP
                        walk_start_t = None
                else:
                    still_start_t = None

                # confirm sleepwalking only while walking_like is true
                if walking_like:
                    if walk_start_t is None:
                        walk_start_t = t
                    elif (t - walk_start_t) >= SLEEPWALK_CONFIRM_TIME:
                        sw_state = SW_SLEEPWALKING
                        sleepwalking_event = "SLEEPWALKING_DETECTED"
                else:
                    walk_start_t = None

            elif sw_state == SW_SLEEPWALKING:
                # drop back to asleep if still for 30s
                if is_still:
                    if still_start_t is None:
                        still_start_t = t
                    elif (t - still_start_t) >= 30.0:
                        sw_state = SW_ASLEEP
                        walk_start_t = None
                else:
                    still_start_t = None

            sleepwalking_flag = (sw_state == SW_SLEEPWALKING)

            if sw_state != last_sw_state:
                print(f"[SW] {SW_STATE_NAME[last_sw_state]} -> {SW_STATE_NAME[sw_state]} | "
                      f"sleep(mean_w={sleep_mean_w:.3f}, var_ag={sleep_var_ag:.5f}) | "
                      f"walk(mean_w={walk_mean_w:.3f}, var_ag={walk_var_ag:.5f})")
                last_sw_state = sw_state

            if sleepwalking_event == "SLEEPWALKING_DETECTED":
                print("🚶 SLEEPWALKING DETECTED")

            # ===================== Fall detection =====================
            fall_a_mag_buf.append(a_mag)
            fall_w_mag_buf.append(w_mag)

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
                        cooldown_until = t + 2.0
                        print("\n⚠️ FALL DETECTED\n")
                    fall_state = IDLE

            fall_status = (t < cooldown_until)

            # ===================== 1 Hz status print =====================
            if t >= next_status_print:
                next_status_print += 1.0
                print(
                    f"[STATUS] a_g={a_g:.2f} | w_mag={w_mag:.2f} | "
                    f"FALL={fall_status} ({FALL_STATE_NAME[fall_state]}) | "
                    f"SW={sleepwalking_flag} ({SW_STATE_NAME[sw_state]}) | "
                    f"sleep(mean_w={sleep_mean_w:.3f}, var={sleep_var_ag:.5f}) | "
                    f"walk(mean_w={walk_mean_w:.3f}, var={walk_var_ag:.5f})"
                )

    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
