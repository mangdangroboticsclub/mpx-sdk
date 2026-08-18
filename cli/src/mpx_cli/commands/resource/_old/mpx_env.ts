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

// ── ABI ─────────────────────────────────────────────────────────
// Returns the host ABI version (2 as of this file). A skill built against a
// different major version will fail to link its imports and trap on the first
// call, so checking this is cheaper than debugging that.
@external("env", "mpx_abi_version")
export declare function mpx_abi_version(): i32;

export const MPX_ABI_VERSION: i32 = 2;

// ── Error codes ─────────────────────────────────────────────────
// Every host function returns one of these, or a value >= 0 where it is
// documented to return data.
export const MPX_OK: i32             =  0;
export const MPX_ERR_ARG: i32        = -1;   // bad id, index or pointer
export const MPX_ERR_NOT_LOCKED: i32 = -2;   // YOU do not hold the servo bus
export const MPX_ERR_NO_REPLY: i32   = -3;   // driver board did not answer
export const MPX_ERR_READONLY: i32   = -4;   // calibration param, read-only
export const MPX_ERR_CANCELLED: i32  = -5;   // the skill was stopped mid-call
export const MPX_ERR_STATE: i32      = -6;   // right call, wrong time

// ── SDK / Logging ───────────────────────────────────────────────
@external("env", "print")
export declare function print(ptr: usize, len: i32): i32;

// ── High-Level Gait Control ─────────────────────────────────────
@external("env", "robot_gait")
export declare function robot_gait(name_ptr: usize): i32;
@external("env", "robot_get_mode")
export declare function robot_get_mode(): i32;

// These three existed in the firmware and in mpx_host.h from the start but
// were never declared here, so body attitude was simply unavailable from
// AssemblyScript.
@external("env", "robot_set_body_pose")
export declare function robot_set_body_pose(roll_deg: f32, pitch_deg: f32, yaw_deg: f32): i32;
@external("env", "robot_set_attitude_speed")
export declare function robot_set_attitude_speed(dps: i32): i32;
@external("env", "robot_set_attitude_speed_xyz")
export declare function robot_set_attitude_speed_xyz(roll_dps: i32, pitch_dps: i32, yaw_dps: i32): i32;

// ── Configuration ───────────────────────────────────────────────
@external("env", "robot_set_config")
export declare function robot_set_config(
    period: i32, height: i32,
    up_height: i32, stride: i32, tilt: i32,
): i32;
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
export declare function robot_set_servo_angle(id: i32, centideg: i32): i32;
@external("env", "robot_flush")
export declare function robot_flush(): i32;
@external("env", "robot_set_servo_speed")
export declare function robot_set_servo_speed(id: i32, speed: i32): i32;
// AT32 frame, 0-1023 — runs OPPOSITE to robot_set_servo_angle()'s frame.
@external("env", "robot_read_position")
export declare function robot_read_position(id: i32): i32;
// Same frame robot_set_servo_angle() takes: signed centidegrees from centre.
// This is the one to close a control loop around. INT32_MIN on a bad id.
@external("env", "robot_read_angle_cdeg")
export declare function robot_read_angle_cdeg(id: i32): i32;

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
export declare function robot_set_offset(id: i32, centideg: i32): i32;
@external("env", "robot_get_offset")
export declare function robot_get_offset(id: i32): i32;
@external("env", "robot_ping_servo")
export declare function robot_ping_servo(id: i32): i32;

// ── Utility ─────────────────────────────────────────────────────
@external("env", "robot_delay_ms")
export declare function robot_delay_ms(ms: i32): i32;

// ── Inverse Kinematics (per-leg) ─────────────────────────────────
@external("env", "robot_ik_fr")
export declare function robot_ik_fr(x: f32, th0: f32, z: f32): i32;
@external("env", "robot_ik_fl")
export declare function robot_ik_fl(x: f32, th0: f32, z: f32): i32;
@external("env", "robot_ik_rr")
export declare function robot_ik_rr(x: f32, th0: f32, z: f32): i32;
@external("env", "robot_ik_rl")
export declare function robot_ik_rl(x: f32, th0: f32, z: f32): i32;

// ── IMU ──────────────────────────────────────────────────────────
@external("env", "robot_imu_read")
export declare function robot_imu_read(buffer_ptr: usize): i32;
@external("env", "robot_imu_print")
export declare function robot_imu_print(): i32;


// ═══════════════════════════════════════════════════════════════════
//  Part 2 — High-Level Abstractions
// ═══════════════════════════════════════════════════════════════════

// ──── 1. Gait enum ──────────────────────────────────────────────

export const enum Gait {
    NONE         = 0,
    INIT         = 1,
    STEP         = 2,
    ROLL         = 3,
    PITCH        = 4,
    STRETCH      = 5,
    ADVANCE      = 6,
    BACK         = 7,
    LEFT         = 8,
    RIGHT        = 9,
    TURN_L       = 10,
    TURN_R       = 11,
    TWERK        = 12,
    JUMP         = 13,
    JUMP_FWD     = 14,
    TEST_SPD     = 15,
    LOOK_UP      = 16,
    LOOK_DOWN    = 17,
    LOOK_LEFT    = 18,
    LOOK_RIGHT   = 19,
    LOOK_UL      = 20,
    LOOK_UR      = 21,
    LOOK_LL      = 22,
    LOOK_LR      = 23,
    FORELEG_LIFT_L = 24,
    FORELEG_LIFT_R = 25,
    BACKLEG_LIFT_L = 26,
    BACKLEG_LIFT_R = 27,
    HEIGHT_UP    = 28,
    HEIGHT_DOWN  = 29,
    BALANCE      = 30,
    BOW_BACK     = 31,
    BODY_CYCLE   = 32,
    HEAD_ELLIPSE = 33,
    MOVE_LF      = 34,
    MOVE_RF      = 35,
    MOVE_LB      = 36,
    MOVE_RB      = 37,
    // These eight existed in the firmware and in mpx_host.h all along; the
    // AssemblyScript enum stopped at 37 and robotGait() hard-rejected
    // anything above it, so they were unreachable from TypeScript.
    STANFORD     = 38,
    FRONTKICK    = 39,
    WIGGLE       = 40,
    BUTTSHRUG    = 41,
    WIGGLE_L     = 42,
    WIGGLE_R     = 43,
    BUTTSHRUG_L  = 44,
    BUTTSHRUG_R  = 45,
}

/* Gait names, in Gait-enum order.
 *
 * These used to be a StaticArray<u8[]> of raw hex bytes passed to the host
 * with changetype<usize>(). That was broken twice over: changetype on an
 * Array<u8> yields the array OBJECT's address, not its data, and the bytes
 * were not NUL-terminated — while the firmware compares them with strcmp().
 * Every robotGait() call therefore missed every name and did nothing, and
 * because robot_gait is registered with a void signature the "unknown gait"
 * error could not even be returned. Plain strings encoded on demand are both
 * correct and legible.
 */
const GAIT_NAMES: string[] = [
    "none",          // 0
    "init",          // 1
    "step",          // 2
    "roll",          // 3
    "pitch",         // 4
    "stretch",       // 5
    "advance",       // 6
    "back",          // 7
    "left",          // 8
    "right",         // 9
    "turnL",         // 10
    "turnR",         // 11
    "twerk",         // 12
    "jump",          // 13
    "jumpfwd",       // 14
    "testspeed",     // 15
    "lookup",        // 16
    "lookdown",      // 17
    "lookleft",      // 18
    "lookright",     // 19
    "lookul",        // 20
    "lookur",        // 21
    "lookll",        // 22
    "looklr",        // 23
    "flegL",         // 24
    "flegR",         // 25
    "blegL",         // 26
    "blegR",         // 27
    "heightup",      // 28
    "heightdown",    // 29
    "balance",       // 30
    "bowback",       // 31
    "bodycycle",     // 32
    "headellipse",   // 33
    "moveLF",        // 34
    "moveRF",        // 35
    "moveLB",        // 36
    "moveRB",        // 37
    "stanford",      // 38
    "frontkick",     // 39
    "wiggle",        // 40
    "buttshrug",     // 41
    "wiggleL",       // 42
    "wiggleR",       // 43
    "buttshrugL",    // 44
    "buttshrugR",    // 45
];

/** Start a gait using the type-safe enum. */
export function robotGait(g: Gait): void {
    const idx = g as i32;
    if (idx < 0 || idx >= GAIT_NAMES.length) return;
    // `true` = NUL-terminate, which strcmp() on the host side requires.
    // changetype<usize> on an ArrayBuffer IS the data pointer; on a TypedArray
    // it is the view header, 32 bytes earlier. That distinction is the whole
    // bug this file used to have — see readImu()/servoRead() below.
    robot_gait(changetype<usize>(String.UTF8.encode(GAIT_NAMES[idx], true)));
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

// ──── 6. New gait choreography helpers ─────────────────────────

export function lookUp(ms: i32): void {
    robotGait(Gait.LOOK_UP);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function lookDown(ms: i32): void {
    robotGait(Gait.LOOK_DOWN);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function lookLeft(ms: i32): void {
    robotGait(Gait.LOOK_LEFT);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function lookRight(ms: i32): void {
    robotGait(Gait.LOOK_RIGHT);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function lookUpperLeft(ms: i32): void {
    robotGait(Gait.LOOK_UL);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function lookUpperRight(ms: i32): void {
    robotGait(Gait.LOOK_UR);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function lookLowerLeft(ms: i32): void {
    robotGait(Gait.LOOK_LL);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function lookLowerRight(ms: i32): void {
    robotGait(Gait.LOOK_LR);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function forelegLiftL(ms: i32): void {
    robotGait(Gait.FORELEG_LIFT_L);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function forelegLiftR(ms: i32): void {
    robotGait(Gait.FORELEG_LIFT_R);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function backlegLiftL(ms: i32): void {
    robotGait(Gait.BACKLEG_LIFT_L);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function backlegLiftR(ms: i32): void {
    robotGait(Gait.BACKLEG_LIFT_R);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function heightUp(ms: i32): void {
    robotGait(Gait.HEIGHT_UP);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function heightDown(ms: i32): void {
    robotGait(Gait.HEIGHT_DOWN);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function balance(ms: i32): void {
    robotGait(Gait.BALANCE);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function bowBack(ms: i32): void {
    robotGait(Gait.BOW_BACK);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function bodyCycle(ms: i32): void {
    robotGait(Gait.BODY_CYCLE);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function headEllipse(ms: i32): void {
    robotGait(Gait.HEAD_ELLIPSE);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function moveLF(ms: i32): void {
    robotGait(Gait.MOVE_LF);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function moveRF(ms: i32): void {
    robotGait(Gait.MOVE_RF);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function moveLB(ms: i32): void {
    robotGait(Gait.MOVE_LB);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
}

export function moveRB(ms: i32): void {
    robotGait(Gait.MOVE_RB);
    robot_delay_ms(ms);
    robotGait(Gait.NONE);
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
    robot_imu_read(buf.dataStart);
    return new ImuData(buf[0], buf[1], buf[2], buf[3], buf[4], buf[5]);
}

/* ═══════════════════════════════════════════════════════════════════
 *  LOW-LEVEL SERVO CONTROL  (AT32 driver boards)
 *
 *  Same shape as unitree_legged_sdk — a command per joint, a state per joint.
 *  The difference is hardware-imposed: only position and the current limit
 *  ride the fast frame. Gains go over the slow config path (~1 ms per write,
 *  gait must be parked), so set them once at the top of a skill.
 *
 *  Angles are the RAW AT32 angle, 0..270°, 135° = mechanical centre. Not the
 *  gait's calibrated frame: no offsets applied, no IK limits enforced.
 * ═══════════════════════════════════════════════════════════════════ */

/** Servo config parameter IDs — the addresses shown in Servo Studio. */
export const enum ServoParam {
    ReversePositionSensor = 0,
    MinPositionAdc        = 1,
    MaxPositionAdc        = 2,
    RangePositionDeg      = 3,
    ReverseMotor          = 4,
    KpPosition            = 5,
    KdPosition            = 6,
    KpCurrent             = 7,
    KffCurrent            = 8,
    MaxPwmDuty            = 9,
}

/** Control mode for servoDirect(). */
export const enum ServoMode {
    Idle     = 0,   /** motor off — the joint goes limp   */
    Position = 1,   /** hold a position, current-limited  */
    Torque   = 2,   /** current (torque) control          */
}

// ── Raw imports ─────────────────────────────────────────────────────

@external("env", "servo_lock")
export declare function servo_lock(): i32;
@external("env", "servo_unlock")
export declare function servo_unlock(): i32;
@external("env", "servo_is_locked")
export declare function servo_is_locked(): i32;

@external("env", "servo_set_gain")
export declare function servo_set_gain(id: i32, param: i32, value: f32): i32;
@external("env", "servo_get_gain")
export declare function servo_get_gain(id: i32, param: i32, out_ptr: usize): i32;
@external("env", "servo_save_config")
export declare function servo_save_config(id: i32): i32;
@external("env", "servo_restore_config")
export declare function servo_restore_config(id: i32): i32;

@external("env", "servo_stage")
export declare function servo_stage(id: i32, q_deg: f32, tau_ma: f32, kp: f32, kd: f32): i32;
@external("env", "servo_commit")
export declare function servo_commit(): i32;
@external("env", "servo_write_all")
export declare function servo_write_all(cmd_ptr: usize, count: i32): i32;
@external("env", "servo_direct")
export declare function servo_direct(id: i32, mode: i32, q_deg: f32, tau_ma: f32): i32;

@external("env", "servo_read")
export declare function servo_read(id: i32, out_ptr: usize): i32;
@external("env", "servo_read_all")
export declare function servo_read_all(out_ptr: usize): i32;
@external("env", "servo_poll")
export declare function servo_poll(): i32;
@external("env", "servo_scan")
export declare function servo_scan(): i32;

// ── Typed helpers ───────────────────────────────────────────────────

/**
 * One joint's command.
 *
 * kp/kd are sent in the wire frame but the stock AT32 firmware ignores them
 * and uses its stored config gains. Leave them 0 unless your board firmware
 * is known to honour per-frame gains.
 */
export class ServoCmd {
    constructor(
        public qDeg: f32 = 135,  /** target angle, raw 0..270°            */
        public tauMa: f32 = 200, /** current limit, mA — a ceiling        */
        public kp: f32 = 0,      /** per-frame gain, 0 = use stored gain  */
        public kd: f32 = 0,      /** per-frame gain, 0 = use stored gain  */
    ) {}
}

/**
 * One joint's measured state.
 *
 * There is no velocity field on purpose: the boards do not measure one, and a
 * hardcoded zero named `dq` would be a lie. Differentiate qDeg if you need it.
 */
export class ServoState {
    constructor(
        public qDeg: f32 = 0,   /** present angle, raw 0..270°            */
        public tauMa: f32 = 0,  /** present motor current, mA (signed)    */
        public tempC: f32 = 0,  /** NTC temperature °C — NaN if unknown   */
        public qRaw: f32 = 0,   /** same position on the SCS 0..1023 scale*/
    ) {}
}

/** Read one joint's state. */
export function readServo(id: i32): ServoState {
    const buf = new Float32Array(4);
    servo_read(id, buf.dataStart);
    return new ServoState(buf[0], buf[1], buf[2], buf[3]);
}

/** Read all twelve joints, index 0 = servo 1. */
export function readAllServos(): ServoState[] {
    const buf = new Float32Array(48);
    servo_read_all(buf.dataStart);
    const out = new Array<ServoState>(12);
    for (let i = 0; i < 12; i++) {
        const b = i * 4;
        out[i] = new ServoState(buf[b], buf[b + 1], buf[b + 2], buf[b + 3]);
    }
    return out;
}

/** Stage and commit up to twelve joint commands in one bus pass. */
export function writeAllServos(cmds: ServoCmd[]): i32 {
    const n = cmds.length <= 12 ? cmds.length : 12;
    const buf = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
        const c = cmds[i], b = i * 4;
        buf[b] = c.qDeg; buf[b + 1] = c.tauMa; buf[b + 2] = c.kp; buf[b + 3] = c.kd;
    }
    return servo_write_all(buf.dataStart, n);
}

/** Read one control gain back from the board. Returns NaN on failure. */
export function readServoGain(id: i32, param: ServoParam): f32 {
    const buf = new Float32Array(1);
    if (servo_get_gain(id, param, buf.dataStart) != 0) return NaN;
    return buf[0];
}

/** Set the position loop gains on every joint. Returns the number that failed. */
export function setAllServoGains(kp: f32, kd: f32): i32 {
    let failed = 0;
    for (let id = 1; id <= 12; id++) {
        if (servo_set_gain(id, ServoParam.KpPosition, kp) != 0) { failed++; continue; }
        if (servo_set_gain(id, ServoParam.KdPosition, kd) != 0) { failed++; }
    }
    return failed;
}

/** Cut power to every motor — the joints go limp. */
export function allServosOff(): i32 {
    let failed = 0;
    for (let id = 1; id <= 12; id++) {
        if (servo_direct(id, ServoMode.Idle, 135, 0) != 0) failed++;
    }
    return failed;
}
