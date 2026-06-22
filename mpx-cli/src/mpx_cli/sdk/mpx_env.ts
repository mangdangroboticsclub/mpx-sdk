/**
 * mpx_env.ts — MPX-Dog WASM Host Function Declarations (AssemblyScript)
 *
 * Import host functions from the "env" module into your skill:
 *
 *   import {
 *     print, robot_gait, robot_delay_ms,
 *     robot_set_config, robot_ping_servo,
 *   } from "../include/mpx_env";
 *
 * All functions are registered under the "env" module by the ESP32 firmware.
 */

// ── SDK / Logging ───────────────────────────────────────────────
@external("env", "print")
export declare function print(ptr: usize, len: i32): void;

// ── High-Level Gait Control ─────────────────────────────────────
@external("env", "robot_gait")
export declare function robot_gait(name_ptr: usize): void;
@external("env", "robot_get_mode")
export declare function robot_get_mode(): i32;

// ── Configuration ───────────────────────────────────────────────
@external("env", "robot_set_config")
export declare function robot_set_config(
    period: i32, height: i32,
    up_height: i32, stride: i32, tilt: i32,
): void;
@external("env", "robot_get_period")
export declare function robot_get_period(): i32;
@external("env", "robot_get_height")
export declare function robot_get_height(): i32;
@external("env", "robot_get_up_height")
export declare function robot_get_up_height(): i32;
@external("env", "robot_get_stride")
export declare function robot_get_stride(): i32;
@external("env", "robot_get_tilt")
export declare function robot_get_tilt(): i32;

// ── Low-Level Servo Control ─────────────────────────────────────
@external("env", "robot_set_servo_angle")
export declare function robot_set_servo_angle(id: i32, centideg: i32): void;
@external("env", "robot_flush")
export declare function robot_flush(): void;
@external("env", "robot_set_servo_speed")
export declare function robot_set_servo_speed(id: i32, speed: i32): void;
@external("env", "robot_read_position")
export declare function robot_read_position(id: i32): i32;

// ── Calibration ─────────────────────────────────────────────────
@external("env", "robot_set_offset")
export declare function robot_set_offset(id: i32, centideg: i32): void;
@external("env", "robot_get_offset")
export declare function robot_get_offset(id: i32): i32;
@external("env", "robot_ping_servo")
export declare function robot_ping_servo(id: i32): i32;

// ── Utility ─────────────────────────────────────────────────────
@external("env", "robot_delay_ms")
export declare function robot_delay_ms(ms: i32): void;
