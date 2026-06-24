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

// ── Additional Servo Read Functions ──────────────────────────────
@external("env", "robot_read_speed")
export declare function robot_read_speed(id: i32): i32;
@external("env", "robot_read_load")
export declare function robot_read_load(id: i32): i32;
@external("env", "robot_read_voltage")
export declare function robot_read_voltage(id: i32): i32;
@external("env", "robot_read_temperature")
export declare function robot_read_temperature(id: i32): i32;
@external("env", "robot_read_moving")
export declare function robot_read_moving(id: i32): i32;
@external("env", "robot_read_current")
export declare function robot_read_current(id: i32): i32;

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

// ── Inverse Kinematics (per-leg) ─────────────────────────────────
@external("env", "robot_ik_fr")
export declare function robot_ik_fr(x: f32, th0: f32, z: f32): void;
@external("env", "robot_ik_fl")
export declare function robot_ik_fl(x: f32, th0: f32, z: f32): void;
@external("env", "robot_ik_rr")
export declare function robot_ik_rr(x: f32, th0: f32, z: f32): void;
@external("env", "robot_ik_rl")
export declare function robot_ik_rl(x: f32, th0: f32, z: f32): void;

// ── IMU ──────────────────────────────────────────────────────────
@external("env", "robot_imu_read")
export declare function robot_imu_read(buffer_ptr: usize): void;
@external("env", "robot_imu_print")
export declare function robot_imu_print(): void;


// ═══════════════════════════════════════════════════════════════════
//  Part 2 — High-Level Abstractions
// ═══════════════════════════════════════════════════════════════════

// ──── 1. Gait enum ──────────────────────────────────────────────

export const enum Gait {
    NONE     = 0,
    INIT     = 1,
    STEP     = 2,
    ROLL     = 3,
    PITCH    = 4,
    STRETCH  = 5,
    ADVANCE  = 6,
    BACK     = 7,
    LEFT     = 8,
    RIGHT    = 9,
    TURN_L   = 10,
    TURN_R   = 11,
    TWERK    = 12,
    JUMP     = 13,
    JUMP_FWD = 14,
    TEST_SPD = 15,
}

const GAIT_NAMES: StaticArray<u8[]> = [
    [0x6e, 0x6f, 0x6e, 0x65],                               // "none"
    [0x69, 0x6e, 0x69, 0x74],                               // "init"
    [0x73, 0x74, 0x65, 0x70],                               // "step"
    [0x72, 0x6f, 0x6c, 0x6c],                               // "roll"
    [0x70, 0x69, 0x74, 0x63, 0x68],                         // "pitch"
    [0x73, 0x74, 0x72, 0x65, 0x74, 0x63, 0x68],             // "stretch"
    [0x61, 0x64, 0x76, 0x61, 0x6e, 0x63, 0x65],             // "advance"
    [0x62, 0x61, 0x63, 0x6b],                               // "back"
    [0x6c, 0x65, 0x66, 0x74],                               // "left"
    [0x72, 0x69, 0x67, 0x68, 0x74],                         // "right"
    [0x74, 0x75, 0x72, 0x6e, 0x4c],                         // "turnL"
    [0x74, 0x75, 0x72, 0x6e, 0x52],                         // "turnR"
    [0x74, 0x77, 0x65, 0x72, 0x6b],                         // "twerk"
    [0x6a, 0x75, 0x6d, 0x70],                               // "jump"
    [0x6a, 0x75, 0x6d, 0x70, 0x66, 0x77, 0x64],             // "jumpfwd"
    [0x74, 0x65, 0x73, 0x74, 0x73, 0x70, 0x65, 0x65, 0x64], // "testspeed"
];

/** Start a gait using the type-safe enum. */
export function robotGait(g: Gait): void {
    const idx = g as i32;
    if (idx < 0 || idx > 15) return;
    const name = GAIT_NAMES[idx];
    robot_gait(changetype<usize>(name));
}

// ──── 2. Named servo IDs ────────────────────────────────────────

export const enum Servo {
    FR_HIP      = 1,
    FR_SHOULDER = 2,
    FR_KNEE     = 3,
    FL_HIP      = 4,
    FL_SHOULDER = 5,
    FL_KNEE     = 6,
    RR_HIP      = 7,
    RR_SHOULDER = 8,
    RR_KNEE     = 9,
    RL_HIP      = 10,
    RL_SHOULDER = 11,
    RL_KNEE     = 12,
}

// ──── 3. Degree-based servo control ─────────────────────────────

/** Set servo angle in degrees (auto-converts to centidegrees). */
export function setServoDeg(id: Servo, deg: f32): void {
    robot_set_servo_angle(id as i32, (deg * 100.0) as i32);
}

/** Set servo angle + speed in one call. */
export function setServo(id: Servo, deg: f32, speed: i32): void {
    robot_set_servo_speed(id as i32, speed);
    setServoDeg(id, deg);
}

// ──── 4. Config struct ─────────────────────────────────────────

export class RobotConfig {
    constructor(
        public period: i32 = 80,
        public height: i32 = 70,
        public upHeight: i32 = 10,
        public stride: i32 = 10,
        public tilt: i32 = 10,
    ) {}
}

/** Set config from a RobotConfig object. */
export function setRobotConfig(cfg: RobotConfig): void {
    robot_set_config(cfg.period, cfg.height, cfg.upHeight, cfg.stride, cfg.tilt);
}

/** Get current config as a RobotConfig object. */
export function getRobotConfig(): RobotConfig {
    return new RobotConfig(
        robot_get_period(),
        robot_get_height(),
        robot_get_up_height(),
        robot_get_stride(),
        robot_get_tilt(),
    );
}

// ──── 5. Choreography helpers ──────────────────────────────────

export function walkForward(ms: i32): void {
    robotGait(Gait.ADVANCE);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function walkBackward(ms: i32): void {
    robotGait(Gait.BACK);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function turnLeft(ms: i32): void {
    robotGait(Gait.TURN_L);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function turnRight(ms: i32): void {
    robotGait(Gait.TURN_R);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function strafeLeft(ms: i32): void {
    robotGait(Gait.LEFT);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function strafeRight(ms: i32): void {
    robotGait(Gait.RIGHT);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function jump(): void {
    robotGait(Gait.JUMP);
    robot_delay_ms(2000);
    robotGait(Gait.NONE);
}

export function stand(): void {
    robotGait(Gait.INIT);
    robot_delay_ms(2000);
}

export function dance(ms: i32): void {
    robot_set_config(60, 60, 15, 8, 15);
    robotGait(Gait.TWERK);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function stepInPlace(ms: i32): void {
    robotGait(Gait.STEP);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

// ──── 6. Pose helper ───────────────────────────────────────────

export class RobotPose {
    constructor(
        public frHip: f32 = 0, public frShoulder: f32 = 0, public frKnee: f32 = 0,
        public flHip: f32 = 0, public flShoulder: f32 = 0, public flKnee: f32 = 0,
        public rrHip: f32 = 0, public rrShoulder: f32 = 0, public rrKnee: f32 = 0,
        public rlHip: f32 = 0, public rlShoulder: f32 = 0, public rlKnee: f32 = 0,
    ) {}
}

/** Apply a complete pose — sets all 12 servos and flushes. */
export function applyPose(p: RobotPose): void {
    robot_set_servo_angle(Servo.FR_HIP,      (p.frHip      * 100.0) as i32);
    robot_set_servo_angle(Servo.FR_SHOULDER,  (p.frShoulder * 100.0) as i32);
    robot_set_servo_angle(Servo.FR_KNEE,      (p.frKnee     * 100.0) as i32);
    robot_set_servo_angle(Servo.FL_HIP,      (p.flHip      * 100.0) as i32);
    robot_set_servo_angle(Servo.FL_SHOULDER,  (p.flShoulder * 100.0) as i32);
    robot_set_servo_angle(Servo.FL_KNEE,      (p.flKnee     * 100.0) as i32);
    robot_set_servo_angle(Servo.RR_HIP,      (p.rrHip      * 100.0) as i32);
    robot_set_servo_angle(Servo.RR_SHOULDER,  (p.rrShoulder * 100.0) as i32);
    robot_set_servo_angle(Servo.RR_KNEE,      (p.rrKnee     * 100.0) as i32);
    robot_set_servo_angle(Servo.RL_HIP,      (p.rlHip      * 100.0) as i32);
    robot_set_servo_angle(Servo.RL_SHOULDER,  (p.rlShoulder * 100.0) as i32);
    robot_set_servo_angle(Servo.RL_KNEE,      (p.rlKnee     * 100.0) as i32);
    robot_flush();
}

// ──── 7. IK helper ──────────────────────────────────────────────

/** Per-leg IK target. */
export class ikTarget {
    constructor(
        public x: f32 = 0,   /**< Forward/backward position in mm */
        public th0: f32 = 0, /**< Hip rotation in degrees */
        public z: f32 = 0,   /**< Height in mm */
    ) {}
}

/** Set front-right leg IK from an ikTarget. */
export function ikFR(t: ikTarget): void {
    robot_ik_fr(t.x, t.th0, t.z);
}
/** Set front-left leg IK from an ikTarget. */
export function ikFL(t: ikTarget): void {
    robot_ik_fl(t.x, t.th0, t.z);
}
/** Set rear-right leg IK from an ikTarget. */
export function ikRR(t: ikTarget): void {
    robot_ik_rr(t.x, t.th0, t.z);
}
/** Set rear-left leg IK from an ikTarget. */
export function ikRL(t: ikTarget): void {
    robot_ik_rl(t.x, t.th0, t.z);
}

// ──── 8. IMU data ───────────────────────────────────────────────

export class ImuData {
    constructor(
        public ax: f32 = 0, /**< Accel X (g) */
        public ay: f32 = 0, /**< Accel Y (g) */
        public az: f32 = 0, /**< Accel Z (g) */
        public gx: f32 = 0, /**< Gyro X (dps) */
        public gy: f32 = 0, /**< Gyro Y (dps) */
        public gz: f32 = 0, /**< Gyro Z (dps) */
    ) {}
}

/** Read IMU data into an ImuData object. */
export function readImu(): ImuData {
    const buf = new Float32Array(6);
    robot_imu_read(changetype<usize>(buf));
    return new ImuData(buf[0], buf[1], buf[2], buf[3], buf[4], buf[5]);
}
