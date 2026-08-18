# MPX-Dog Host Functions — WAT Import Reference

All host functions are registered under the `"env"` module by the ESP32 firmware.
Import them in your `.wat` skill with `(import "env" ...)` declarations.

## SDK / Logging

```wat
(import "env" "print" (func $print (param i32 i32)))
```

## High-Level Gait Control

```wat
(import "env" "robot_gait"     (func $robot_gait     (param i32)))
(import "env" "robot_get_mode" (func $robot_get_mode (result i32)))
```

## Configuration

```wat
(import "env" "robot_set_config" (func $robot_set_config
    (param i32 i32 i32 i32 i32)))
(import "env" "robot_get_period"    (func $robot_get_period    (result i32)))
(import "env" "robot_get_height"    (func $robot_get_height    (result i32)))
(import "env" "robot_get_up_height" (func $robot_get_up_height (result i32)))
(import "env" "robot_get_stride"    (func $robot_get_stride    (result i32)))
(import "env" "robot_get_tilt"      (func $robot_get_tilt      (result i32)))
```

## Low-Level Servo Control

```wat
(import "env" "robot_set_servo_angle" (func $robot_set_servo_angle (param i32 i32)))
(import "env" "mpx_abi_version"   (func $mpx_abi_version (result i32)))
(import "env" "robot_set_body_pose" (func $robot_set_body_pose
    (param f32 f32 f32) (result i32)))
(import "env" "robot_set_attitude_speed" (func $robot_set_attitude_speed
    (param i32) (result i32)))
(import "env" "robot_set_attitude_speed_xyz" (func $robot_set_attitude_speed_xyz
    (param i32 i32 i32) (result i32)))
(import "env" "robot_flush"           (func $robot_flush))
(import "env" "robot_set_servo_speed" (func $robot_set_servo_speed (param i32 i32)))
;; AT32 frame (0..1023) — runs OPPOSITE to robot_set_servo_angle's frame.
(import "env" "robot_read_position"   (func $robot_read_position
    (param i32) (result i32)))
;; Same frame robot_set_servo_angle takes: signed centidegrees from centre.
;; Close control loops around THIS one. INT32_MIN on a bad id.
(import "env" "robot_read_angle_cdeg" (func $robot_read_angle_cdeg
    (param i32) (result i32)))
(import "env" "robot_read_speed"      (func $robot_read_speed
    (param i32) (result i32)))
(import "env" "robot_read_load"       (func $robot_read_load
    (param i32) (result i32)))
(import "env" "robot_read_voltage"    (func $robot_read_voltage
    (param i32) (result i32)))
(import "env" "robot_read_temperature" (func $robot_read_temperature
    (param i32) (result i32)))
(import "env" "robot_read_moving"     (func $robot_read_moving
    (param i32) (result i32)))
(import "env" "robot_read_current"    (func $robot_read_current
    (param i32) (result i32)))
```

## Calibration

```wat
(import "env" "robot_set_offset" (func $robot_set_offset (param i32 i32)))
(import "env" "robot_get_offset" (func $robot_get_offset
    (param i32) (result i32)))
(import "env" "robot_ping_servo" (func $robot_ping_servo
    (param i32) (result i32)))
```

## Utility

```wat
(import "env" "robot_delay_ms" (func $robot_delay_ms (param i32)))
```

## Inverse Kinematics (per-leg)

```wat
(import "env" "robot_ik_fr" (func $robot_ik_fr (param f32 f32 f32)))
(import "env" "robot_ik_fl" (func $robot_ik_fl (param f32 f32 f32)))
(import "env" "robot_ik_rr" (func $robot_ik_rr (param f32 f32 f32)))
(import "env" "robot_ik_rl" (func $robot_ik_rl (param f32 f32 f32)))
```

## IMU

```wat
(import "env" "robot_imu_read"  (func $robot_imu_read (param i32)))
(import "env" "robot_imu_print" (func $robot_imu_print))
```

## Low-Level Servo Control — AT32 driver boards (Unitree-style)

Direct joint control. Angles are the **raw AT32 angle, 0–270°**, with 135° at
mechanical centre — not the gait's calibrated frame, and not the ±90° relative
frame `robot_set_servo_angle` uses.

Every function here needs the bus lock EXCEPT `servo_read` and
`servo_read_all`, which are served from the feedback cache. `servo_scan` and
`servo_poll` do need it, despite reading — they put traffic on the bus.

Return codes: `0` ok, `-1` bad argument, `-2` bus not locked (or held by
Servo Studio rather than by you), `-3` board did not answer, `-4` read-only
parameter — `servo_set_gain` refuses params 1-3 (`MIN_POSITION_ADC`,
`MAX_POSITION_ADC`, `RANGE_POSITION_DEG`), which are the board's calibration
rather than control gains. Read them with `servo_get_gain`; change them from
Servo Studio, with a human watching the joint.

```wat
;; Bus ownership — servo_lock parks the gait; the sandbox force-releases it
;; when your skill ends, so a crash cannot leave the robot parked.
(import "env" "servo_lock"       (func $servo_lock       (result i32)))
(import "env" "servo_unlock"     (func $servo_unlock     (result i32)))
(import "env" "servo_is_locked"  (func $servo_is_locked  (result i32)))

;; Gains — the CONFIG path. ~1 ms per write and the gait must be parked, so
;; set these once at the top of a skill, never per tick.
;; param: 0 reverse_position_sensor, 1 min_position_adc, 2 max_position_adc,
;;        3 range_position_deg, 4 reverse_motor, 5 kp_position, 6 kd_position,
;;        7 kp_current, 8 kff_current, 9 max_pwm_duty
(import "env" "servo_set_gain"   (func $servo_set_gain
    (param i32 i32 f32) (result i32)))          ;; id, param, value
(import "env" "servo_get_gain"   (func $servo_get_gain
    (param i32 i32 i32) (result i32)))          ;; id, param, ptr to one f32
(import "env" "servo_save_config"    (func $servo_save_config
    (param i32) (result i32)))                  ;; id, or 0 for all four boards
(import "env" "servo_restore_config" (func $servo_restore_config
    (param i32) (result i32)))

;; Commands — the FAST path. Stage as many joints as you like, then commit
;; once: all twelve cost four SPI frames.
(import "env" "servo_stage"      (func $servo_stage
    (param i32 f32 f32 f32 f32) (result i32)))  ;; id, q_deg, tau_ma, kp, kd
(import "env" "servo_commit"     (func $servo_commit     (result i32)))
(import "env" "servo_write_all"  (func $servo_write_all
    (param i32 i32) (result i32)))              ;; ptr to cmd array, count 1..12
(import "env" "servo_direct"     (func $servo_direct
    (param i32 i32 f32 f32) (result i32)))      ;; id, mode, q_deg, tau_ma
                                                ;; mode: 0 idle, 1 position, 2 torque

;; State
(import "env" "servo_read"       (func $servo_read
    (param i32 i32) (result i32)))              ;; id, ptr to 4 f32
(import "env" "servo_read_all"   (func $servo_read_all
    (param i32) (result i32)))                  ;; ptr to 12 x 4 f32
(import "env" "servo_poll"       (func $servo_poll       (result i32)))
(import "env" "servo_scan"       (func $servo_scan       (result i32)))
```

### Memory layout

`servo_write_all` reads a packed array of 4 × `f32` per joint, index 0 = servo 1:

| offset | field | meaning |
|--------|-------|---------|
| +0 | `q_deg` | target angle, 0–270° |
| +4 | `tau_ma` | current limit in mA — a ceiling, not a demand |
| +8 | `kp` | per-frame gain, `0` = use the board's stored gain |
| +12 | `kd` | per-frame gain, `0` = use the board's stored gain |

`servo_read` / `servo_read_all` write 4 × `f32` per joint:

| offset | field | meaning |
|--------|-------|---------|
| +0 | `q_deg` | present angle, 0–270° |
| +4 | `tau_ma` | present motor current, mA (signed) |
| +8 | `temp_c` | NTC temperature °C, `NaN` if the servo never answered |
| +12 | `q_raw` | the same position on the SCS 0–1023 scale |

There is no velocity field: the boards do not measure one, and a hardcoded
zero named `dq` would be a lie. Differentiate `q_deg` yourself if you need it.

> **`kp`/`kd` in the command frame are experimental.** The fields exist in the
> wire protocol, but the stock AT32 firmware ignores them and uses its stored
> `sms_config` gains. Send `0` unless your board firmware is known to honour
> per-frame gains; use `servo_set_gain` otherwise.
