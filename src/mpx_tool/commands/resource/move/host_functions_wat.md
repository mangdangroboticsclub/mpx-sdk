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
(import "env" "robot_flush"           (func $robot_flush))
(import "env" "robot_set_servo_speed" (func $robot_set_servo_speed (param i32 i32)))
(import "env" "robot_read_position"   (func $robot_read_position
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
