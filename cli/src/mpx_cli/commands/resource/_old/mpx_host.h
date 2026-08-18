/* ═══════════════════════════════════════════════════════════════════
 * mpx_host.h — MPX-Dog WASM Skill Host Function Reference
 *
 * Include this header in your C/C++ WASM skills to import all
 * available host functions from the "env" module.
 *
 * The ESP32 firmware registers these functions via WAMR's native
 * symbol table. Each function is callable from within the WASM
 * sandbox with no special setup required.
 *
 * Usage:
 *   #include "mpx_host.h"
 *
 *   void on_start(void) {
 *       MPX_print("Hello from my skill!");
 *       robot_gait((int)"advance");
 *       robot_delay_ms(2000);
 *       robot_gait((int)"none");
 *   }
 *
 * Compile with WASI SDK:
 *   /opt/wasi-sdk/bin/clang \
 *       --target=wasm32-wasip1 \
 *       -nostartfiles \
 *       -Wl,--no-entry \
 *       -Wl,--export=on_start \
 *       -Wl,--import-undefined \
 *       -I/path/to/mpx_host/dir \
 *       -o skill.wasm skill.c
 * ═══════════════════════════════════════════════════════════════════ */

#ifndef MPX_HOST_H
#define MPX_HOST_H

#ifdef __cplusplus
extern "C" {
#endif

/* ── ABI version and error codes ─────────────────────────────── */

/** The host ABI this header targets. */
#define MPX_ABI_VERSION 2

/**
 * @brief Ask the robot which host ABI it implements.
 *
 * Wasm import:  extern int mpx_abi_version(void);
 * WAMR sig:     "()i"
 *
 * A skill built against a different major version fails to link its imports
 * and traps on the first call to a changed function, which is a confusing way
 * to find out. Checking this at the top of on_start() is cheaper:
 *
 * @code
 *     if (mpx_abi_version() != MPX_ABI_VERSION) {
 *         MPX_LOG("rebuild me against this robot's SDK");
 *         return;
 *     }
 * @endcode
 */
extern int mpx_abi_version(void);

/**
 * Every host function returns one of these, or a value >= 0 where it is
 * documented to return data.
 *
 * Before ABI v2 there were four incompatible conventions in one table, and
 * seventeen functions computed an error they could not physically return —
 * a misspelled gait name and a watchdog cancellation both looked exactly like
 * nothing happening. This is the only convention now.
 */
typedef enum {
    MPX_OK             =  0,  /**< Success.                             */
    MPX_ERR_ARG        = -1,  /**< Bad argument: id, index or pointer.  */
    MPX_ERR_NOT_LOCKED = -2,  /**< YOU do not hold the servo bus.       */
    MPX_ERR_NO_REPLY   = -3,  /**< The driver board did not answer.     */
    MPX_ERR_READONLY   = -4,  /**< Calibration parameter; read-only.    */
    MPX_ERR_CANCELLED  = -5,  /**< The skill was stopped mid-call.      */
    MPX_ERR_STATE      = -6,  /**< Right call, wrong time.              */
} mpx_err_t;

/** Human-readable form of a host return code, for logging. */
static inline const char *mpx_strerror(int code) {
    switch (code) {
        case MPX_OK:             return "ok";
        case MPX_ERR_ARG:        return "bad argument";
        case MPX_ERR_NOT_LOCKED: return "servo bus not locked by this skill";
        case MPX_ERR_NO_REPLY:   return "driver board did not answer";
        case MPX_ERR_READONLY:   return "read-only calibration parameter";
        case MPX_ERR_CANCELLED:  return "skill cancelled";
        case MPX_ERR_STATE:      return "wrong state for this call";
        default:                 return "unknown error";
    }
}

/* ── SDK / Logging ───────────────────────────────────────────── */

/**
 * @brief Print a message to the robot's log (ESP_LOGI).
 *
 * The firmware registers this function as ``"print"`` under module ``"env"``.
 * WAMR sig: "($i)" — the string pointer is auto-converted to a native pointer.
 *
 * @param ptr  Native pointer to the string (cast with (int))
 * @param len  String length in bytes
 */
extern int print(int ptr, int len);

/** Convenience wrapper — accepts ``const char *`` directly. */
static inline void MPX_print(const char *str, int len) {
    print((int)str, len);
}

/** Convenience macro — prints a string literal. */
#define MPX_LOG(msg)  MPX_print((msg), (int)(sizeof(msg) - 1))

/* ── High-Level Gait Control ─────────────────────────────────── */

/**
 * @brief Start a gait by name.
 *
 * Wasm import:  extern int robot_gait(int name_ptr);
 * WAMR sig:     "($)i"  — name string (auto-converted)
 *
 * Valid names:
 *   "none"       Stop all gait
 *   "init"       Return to init/stand pose
 *   "step"       Step in place
 *   "roll"       Roll body
 *   "pitch"      Pitch body
 *   "stretch"    Stretch legs
 *   "advance"    Walk forward
 *   "back"       Walk backward
 *   "left"       Sidestep left
 *   "right"      Sidestep right
 *   "turnL"      Turn left
 *   "turnR"      Turn right
 *   "twerk"      Twerk!
 *   "jump"       Jump
 *   "jumpfwd"    Jump forward
 *   "testspeed"  Speed test
 *   "lookup"     Look up (gait-based)
 *   "lookdown"   Look down (gait-based)
 *   "lookleft"   Look left (gait-based)
 *   "lookright"  Look right (gait-based)
 *   "lookul"     Look upper-left
 *   "lookur"     Look upper-right
 *   "lookll"     Look lower-left
 *   "looklr"     Look lower-right
 *   "flegL"      Foreleg lift left
 *   "flegR"      Foreleg lift right
 *   "blegL"      Backleg lift left
 *   "blegR"      Backleg lift right
 *   "heightup"   Height up
 *   "heightdown" Height down
 *   "balance"    Balance body
 *   "bowback"    Bow backward
 *   "bodycycle"  Cycle body motion
 *   "headellipse" Head ellipse motion
 *   "moveLF"     Move left front leg
 *   "moveRF"     Move right front leg
 *   "moveLB"     Move left back leg
 *   "moveRB"     Move right back leg
 *   "stanford"   Stanford trot
 *   "frontkick"  Front kick (auto-return)
 *   "wiggle"     Rear-up tail wiggle
 *   "buttshrug"  Front-up butt shrug
 *   "wiggleL" / "wiggleR"       One-sided wiggle
 *   "buttshrugL" / "buttshrugR" One-sided butt shrug
 */
extern int robot_gait(int name_ptr);

/**
 * @brief Get current gait mode as integer.
 *
 * Wasm import:  extern int robot_get_mode(void);
 * WAMR sig:     "()i"
 *
 * @return Gait mode: 0=None, 1=Init, 2=Step, ...
 */
extern int robot_get_mode(void);

/**
 * @brief Hold a body attitude using Stanford IK.
 *
 * Angles are in degrees and firmware-clamped to safe limits:
 * roll +/-25, pitch +/-20, yaw +/-30.
 * WAMR sig: "(fff)i"
 */
extern int robot_set_body_pose(float roll_deg, float pitch_deg, float yaw_deg);

/**
 * @brief Set the roll/pitch/yaw slew speed in degrees per second.
 *
 * Wasm import:  extern int robot_set_attitude_speed(int dps);
 * WAMR sig:     "(i)i"
 *
 * 0 (default) = instant: poses snap straight to the target.
 * >0 makes robot_roll/pitch/yaw/attitude GLIDE to the target at this speed,
 * so repeated pose updates ease smoothly instead of jumping. Persists until
 * changed, so set it once near the start of your skill.
 */
extern int robot_set_attitude_speed(int dps);
/**
 * @brief Per-axis roll/pitch/yaw slew speed in degrees per second.
 *
 * Wasm import:  extern int robot_set_attitude_speed_xyz(int roll_dps,
 *                   int pitch_dps, int yaw_dps);
 * WAMR sig:     "(iii)i"
 *
 * Like robot_set_attitude_speed() but each axis has its own speed, so e.g.
 * yaw can glide slowly while roll/pitch stay instant. 0 on an axis = snap.
 */
extern int robot_set_attitude_speed_xyz(int roll_dps, int pitch_dps, int yaw_dps);

/* ── Configuration ───────────────────────────────────────────── */

/**
 * @brief Set all gait parameters at once.
 *
 * Wasm import:  extern int robot_set_config(int period, int height,
 *                   int up_height, int stride, int tilt);
 * WAMR sig:     "(iiiii)i"
 *
 * @param period     Gait period in milliseconds (e.g. 100)
 * @param height     Body height in millimeters (e.g. 70)
 * @param up_height  Foot lift height in millimeters (e.g. 10)
 * @param stride     Stride length in millimeters (e.g. 10)
 * @param tilt       Max tilt angle in degrees (e.g. 10)
 */
extern int robot_set_config(int period, int height,
                             int up_height, int stride, int tilt);

/** @brief Get gait period in ms.  WAMR sig: "()i" */
extern int robot_get_period(void);

/** @brief Get body height in mm.  WAMR sig: "()i" */
extern int robot_get_height(void);

/** @brief Get foot lift height in mm.  WAMR sig: "()i" */
extern int robot_get_up_height(void);

/** @brief Get stride length in mm.  WAMR sig: "()i" */
extern int robot_get_stride(void);

/** @brief Get max tilt angle in degrees.  WAMR sig: "()i" */
extern int robot_get_tilt(void);

/* ── Low-Level Servo Control ─────────────────────────────────── */

/**
 * @brief Set a servo's target angle.
 *
 * Wasm import:  extern int robot_set_servo_angle(int id, int centideg);
 * WAMR sig:     "(ii)i"
 *
 * @param id        Servo ID (1-12)
 * @param centideg  Target angle in centidegrees (e.g. 4500 = 45.00°)
 */
extern int robot_set_servo_angle(int id, int centideg);

/**
 * @brief Send all buffered servo commands to the bus.
 * WAMR sig:     "()i"
 */
extern int robot_flush(void);

/**
 * @brief Set servo movement speed.
 *
 * Wasm import:  extern int robot_set_servo_speed(int id, int speed);
 * WAMR sig:     "(ii)i"
 *
 * @param id     Servo ID (1-12)
 * @param speed  0 = max speed, higher values = slower
 */
extern int robot_set_servo_speed(int id, int speed);

/**
 * @brief Read a servo's current position, raw 0-1023 in the AT32 FRAME.
 *
 * Wasm import:  extern int robot_read_position(int id);
 * WAMR sig:     "(i)i"
 *
 * @warning This is the frame the driver boards, servo_read()/servo_read_all()
 *          and Servo Studio use. It runs in the OPPOSITE direction to the
 *          frame robot_set_servo_angle() accepts, so a read -> compare ->
 *          correct loop built on this reader diverges. Use
 *          robot_read_angle_cdeg() to close a loop.
 *
 * @param  id  Servo ID (1-12)
 * @return Raw position (0-1023), or -1 on error
 */
extern int robot_read_position(int id);

/**
 * @brief Read a servo's measured angle in the SAME frame
 *        robot_set_servo_angle() takes: signed centidegrees from centre.
 *
 * Wasm import:  extern int robot_read_angle_cdeg(int id);
 * WAMR sig:     "(i)i"
 *
 * This is the reader to build a control loop around:
 * @code
 *     int err = target_cdeg - robot_read_angle_cdeg(SERVO_FR_KNEE);
 *     robot_set_servo_angle(SERVO_FR_KNEE, target_cdeg + err / 4);
 *     robot_flush();
 * @endcode
 *
 * @param  id  Servo ID (1-12)
 * @return Centidegrees from centre, or INT32_MIN on a bad id. Every value in
 *         +/-13500 is a legitimate reading, so -1 could not be the sentinel.
 */
extern int robot_read_angle_cdeg(int id);

/**
 * @brief Read a servo's current speed.
 *
 * Wasm import:  extern int robot_read_speed(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Signed speed value, or -1 on error
 */
extern int robot_read_speed(int id);

/**
 * @brief Read a servo's current load.
 *
 * Wasm import:  extern int robot_read_load(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Signed load value, or -1 on error
 */
extern int robot_read_load(int id);

/**
 * @brief Read a servo's voltage.
 *
 * Wasm import:  extern int robot_read_voltage(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Voltage in 0.1V units, or -1 on error
 */
extern int robot_read_voltage(int id);

/**
 * @brief Read a servo's temperature.
 *
 * Wasm import:  extern int robot_read_temperature(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Temperature in °C, or -1 on error
 */
extern int robot_read_temperature(int id);

/**
 * @brief Read a servo's moving status.
 *
 * Wasm import:  extern int robot_read_moving(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return 0=stopped, 1=moving, or -1 on error
 */
extern int robot_read_moving(int id);

/**
 * @brief Read a servo's current draw.
 *
 * Wasm import:  extern int robot_read_current(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Signed current in mA, or -1 on error
 */
extern int robot_read_current(int id);

/* ── Calibration ─────────────────────────────────────────────── */

/**
 * @brief Set angular offset for a servo.
 *
 * Wasm import:  extern int robot_set_offset(int id, int centideg);
 * WAMR sig:     "(ii)i"
 *
 * @param id        Servo ID (1-12)
 * @param centideg  Offset in centidegrees (e.g. 150 = 1.50°)
 */
extern int robot_set_offset(int id, int centideg);

/**
 * @brief Get angular offset for a servo.
 *
 * Wasm import:  extern int robot_get_offset(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Offset in centidegrees
 */
extern int robot_get_offset(int id);

/**
 * @brief Ping a servo to check connectivity.
 *
 * Wasm import:  extern int robot_ping_servo(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Servo model number (>0) on success, ≤0 on failure
 */
extern int robot_ping_servo(int id);

/* ── Utility ─────────────────────────────────────────────────── */

/**
 * @brief Block the WASM thread for a real-time delay.
 *
 * Wasm import:  extern int robot_delay_ms(int ms);
 * WAMR sig:     "(i)i"
 *
 * IMPORTANT: This is the ONLY reliable way to pause between gait
 * commands from a WASM skill. Pure-WASM busy-loops run at near-zero
 * wall time inside the interpreter and won't produce real delays.
 *
 * @param ms  Milliseconds to block (uses vTaskDelay internally)
 */
extern int robot_delay_ms(int ms);

/* ── Inverse Kinematics (per-leg) ──────────────────────────────── */

/**
 * @brief Front-right leg IK target.
 *
 * Wasm import:  extern int robot_ik_fr(float x, float th0, float z);
 * WAMR sig:     "(fff)i"
 *
 * @param x    Forward/backward position in mm
 * @param th0  Hip rotation angle in degrees
 * @param z    Height in mm
 */
extern int robot_ik_fr(float x, float th0, float z);

/**
 * @brief Front-left leg IK target.
 *
 * Wasm import:  extern int robot_ik_fl(float x, float th0, float z);
 * WAMR sig:     "(fff)i"
 */
extern int robot_ik_fl(float x, float th0, float z);

/**
 * @brief Rear-right leg IK target.
 *
 * Wasm import:  extern int robot_ik_rr(float x, float th0, float z);
 * WAMR sig:     "(fff)i"
 */
extern int robot_ik_rr(float x, float th0, float z);

/**
 * @brief Rear-left leg IK target.
 *
 * Wasm import:  extern int robot_ik_rl(float x, float th0, float z);
 * WAMR sig:     "(fff)i"
 */
extern int robot_ik_rl(float x, float th0, float z);

/* ── IMU ───────────────────────────────────────────────────────── */

/**
 * @brief Read IMU 6-DOF data into a WASM buffer.
 *
 * Wasm import:  extern int robot_imu_read(int buffer_ptr);
 * WAMR sig:     "(i)i"
 *
 * Buffer must be at least 6 × 4 = 24 bytes. Layout:
 *   float[0] = ax (accel X, g)
 *   float[1] = ay (accel Y, g)
 *   float[2] = az (accel Z, g)
 *   float[3] = gx (gyro X, dps)
 *   float[4] = gy (gyro Y, dps)
 *   float[5] = gz (gyro Z, dps)
 */
extern int robot_imu_read(int buffer_ptr);

/**
 * @brief Print the latest IMU data to the robot's log.
 *
 * Wasm import:  extern int robot_imu_print(void);
 * WAMR sig:     "()i"
 */
extern int robot_imu_print(void);

/* ═══════════════════════════════════════════════════════════════════
 *  PART 2 — High-Level Abstractions
 *
 *  Enums, structs, and inline helpers that make skill development
 *  easier.  They compile down to the Part 1 host functions — no
 *  firmware changes needed.
 *
 *  Usage:
 *      robot_stand();
 *      robot_walk_forward(3000);
 *      robot_turn_left(1500);
 *      robot_jump();
 *      robot_apply_pose((robot_pose_t){ .fr_shoulder = -30, ... });
 *      MPX_print_int(42);
 * ═══════════════════════════════════════════════════════════════════ */

// ──── 1. Gait enum (no more string typos) ─────────────────────

typedef enum {
    GAIT_NONE         = 0,
    GAIT_INIT         = 1,
    GAIT_STEP         = 2,
    GAIT_ROLL         = 3,
    GAIT_PITCH        = 4,
    GAIT_STRETCH      = 5,
    GAIT_ADVANCE      = 6,
    GAIT_BACK         = 7,
    GAIT_LEFT         = 8,
    GAIT_RIGHT        = 9,
    GAIT_TURN_L       = 10,
    GAIT_TURN_R       = 11,
    GAIT_TWERK        = 12,
    GAIT_JUMP         = 13,
    GAIT_JUMP_FWD     = 14,
    GAIT_TEST_SPD     = 15,
    GAIT_LOOK_UP      = 16,
    GAIT_LOOK_DOWN    = 17,
    GAIT_LOOK_LEFT    = 18,
    GAIT_LOOK_RIGHT   = 19,
    GAIT_LOOK_UL      = 20,
    GAIT_LOOK_UR      = 21,
    GAIT_LOOK_LL      = 22,
    GAIT_LOOK_LR      = 23,
    GAIT_FORELEG_LIFT_L = 24,
    GAIT_FORELEG_LIFT_R = 25,
    GAIT_BACKLEG_LIFT_L = 26,
    GAIT_BACKLEG_LIFT_R = 27,
    GAIT_HEIGHT_UP    = 28,
    GAIT_HEIGHT_DOWN  = 29,
    GAIT_BALANCE      = 30,
    GAIT_BOW_BACK     = 31,
    GAIT_BODY_CYCLE   = 32,
    GAIT_HEAD_ELLIPSE = 33,
    GAIT_MOVE_LF      = 34,
    GAIT_MOVE_RF      = 35,
    GAIT_MOVE_LB      = 36,
    GAIT_MOVE_RB      = 37,
    GAIT_STANFORD     = 38,
    GAIT_FRONT_KICK   = 39,
    GAIT_WIGGLE       = 40,
    GAIT_BUTT_SHRUG   = 41,
    GAIT_WIGGLE_L     = 42,
    GAIT_WIGGLE_R     = 43,
    GAIT_BUTT_SHRUG_L = 44,
    GAIT_BUTT_SHRUG_R = 45,
} robot_gait_t;

/**
 * @brief Start a gait using the type-safe enum.
 *
 * Internally maps enum → string → robot_gait().  No more typos like
 * "advnce" silently failing — and since ABI v2 the failure is actually
 * returned rather than only logged on a serial console you are not watching.
 *
 * @return MPX_OK, MPX_ERR_ARG for an out-of-range gait, or whatever
 *         robot_gait() reports.
 */
static inline int robot_gait_enum(robot_gait_t g) {
    /* String lookup table in WASM linear memory.
     * Must match the order of robot::GaitCmd on the firmware side. */
    static const char *names[] = {
        "none",      /* 0  GAIT_NONE         */
        "init",      /* 1  GAIT_INIT         */
        "step",      /* 2  GAIT_STEP         */
        "roll",      /* 3  GAIT_ROLL         */
        "pitch",     /* 4  GAIT_PITCH        */
        "stretch",   /* 5  GAIT_STRETCH      */
        "advance",   /* 6  GAIT_ADVANCE      */
        "back",      /* 7  GAIT_BACK         */
        "left",      /* 8  GAIT_LEFT         */
        "right",     /* 9  GAIT_RIGHT        */
        "turnL",     /* 10 GAIT_TURN_L       */
        "turnR",     /* 11 GAIT_TURN_R       */
        "twerk",     /* 12 GAIT_TWERK        */
        "jump",      /* 13 GAIT_JUMP         */
        "jumpfwd",   /* 14 GAIT_JUMP_FWD     */
        "testspeed", /* 15 GAIT_TEST_SPD     */
        "lookup",    /* 16 GAIT_LOOK_UP      */
        "lookdown",  /* 17 GAIT_LOOK_DOWN    */
        "lookleft",  /* 18 GAIT_LOOK_LEFT    */
        "lookright", /* 19 GAIT_LOOK_RIGHT   */
        "lookul",    /* 20 GAIT_LOOK_UL      */
        "lookur",    /* 21 GAIT_LOOK_UR      */
        "lookll",    /* 22 GAIT_LOOK_LL      */
        "looklr",    /* 23 GAIT_LOOK_LR      */
        "flegL",     /* 24 GAIT_FORELEG_LIFT_L */
        "flegR",     /* 25 GAIT_FORELEG_LIFT_R */
        "blegL",     /* 26 GAIT_BACKLEG_LIFT_L */
        "blegR",     /* 27 GAIT_BACKLEG_LIFT_R */
        "heightup",  /* 28 GAIT_HEIGHT_UP    */
        "heightdown",/* 29 GAIT_HEIGHT_DOWN  */
        "balance",   /* 30 GAIT_BALANCE      */
        "bowback",   /* 31 GAIT_BOW_BACK     */
        "bodycycle", /* 32 GAIT_BODY_CYCLE   */
        "headellipse",/* 33 GAIT_HEAD_ELLIPSE */
        "moveLF",    /* 34 GAIT_MOVE_LF      */
        "moveRF",    /* 35 GAIT_MOVE_RF      */
        "moveLB",    /* 36 GAIT_MOVE_LB      */
        "moveRB",    /* 37 GAIT_MOVE_RB      */
        "stanford",  /* 38 GAIT_STANFORD     */
        "frontkick", /* 39 GAIT_FRONT_KICK   */
        "wiggle",    /* 40 GAIT_WIGGLE       */
        "buttshrug", /* 41 GAIT_BUTT_SHRUG   */
        "wiggleL",   /* 42 GAIT_WIGGLE_L     */
        "wiggleR",   /* 43 GAIT_WIGGLE_R     */
        "buttshrugL",/* 44 GAIT_BUTT_SHRUG_L */
        "buttshrugR",/* 45 GAIT_BUTT_SHRUG_R */
    };
    if (g < GAIT_NONE || g > GAIT_BUTT_SHRUG_R) return MPX_ERR_ARG;
    return robot_gait((int)names[(int)g]);
}

// ──── 2. Named servo IDs (no more magic numbers) ──────────────

typedef enum {
    /* Front Right leg */
    SERVO_FR_HIP      = 1,
    SERVO_FR_SHOULDER = 2,
    SERVO_FR_KNEE     = 3,
    /* Front Left leg */
    SERVO_FL_HIP      = 4,
    SERVO_FL_SHOULDER = 5,
    SERVO_FL_KNEE     = 6,
    /* Rear Right leg */
    SERVO_RR_HIP      = 7,
    SERVO_RR_SHOULDER = 8,
    SERVO_RR_KNEE     = 9,
    /* Rear Left leg */
    SERVO_RL_HIP      = 10,
    SERVO_RL_SHOULDER = 11,
    SERVO_RL_KNEE     = 12,
} robot_servo_t;

// ──── 3. Degree-based servo control (no more centidegree math) ─

/** Set servo angle in degrees (auto-converts to centidegrees). */
static inline int robot_set_servo_deg(robot_servo_t id, float deg) {
    return robot_set_servo_angle((int)id, (int)(deg * 100.0f));
}

/* robot_set_servo_raw() USED TO LIVE HERE. It has been removed, not fixed,
 * because every part of its contract was wrong:
 *
 *   - it scaled by 300°, but the hardware range is 270° (SERVO_RANGE_DEG);
 *   - it was documented as absolute ("0°→0"), but robot_set_servo_angle()
 *     is RELATIVE TO CENTRE, so robot_set_servo_raw(0) parked the joint at
 *     centre rather than at 0;
 *   - and as a result every input from about 461 upward saturated — over
 *     half its documented range drove the joint into its mechanical stop.
 *
 * For raw work use the low-level servo API further down this header:
 * servo_direct() / servo_stage() take the true AT32 angle in degrees
 * (0..270, 135 = centre) and go straight to the driver boards.
 */

/** Set servo angle + speed in one call. */
static inline void robot_set_servo(robot_servo_t id, float deg, int speed) {
    robot_set_servo_speed((int)id, speed);
    robot_set_servo_deg(id, deg);
}

// ──── 4. Config struct (no more flat 5-arg calls) ────────────

typedef struct {
    int period;      /**< Gait period in ms per phase */
    int height;      /**< Body height in mm */
    int up_height;   /**< Foot lift height in mm */
    int stride;      /**< Stride length in mm */
    int tilt;        /**< Max body tilt in degrees */
} robot_config_t;

/** Set config from a struct. */
static inline void robot_set_config_ex(robot_config_t cfg) {
    robot_set_config(cfg.period, cfg.height,
                     cfg.up_height, cfg.stride, cfg.tilt);
}

/** Get current config as a struct. */
static inline robot_config_t robot_get_config_ex(void) {
    robot_config_t c;
    c.period    = robot_get_period();
    c.height    = robot_get_height();
    c.up_height = robot_get_up_height();
    c.stride    = robot_get_stride();
    c.tilt      = robot_get_tilt();
    return c;
}

// ──── 5. Choreography helpers (one-liner actions) ────────────

/** Walk forward for N ms, then stop. */
static inline int robot_walk_forward(int ms) {
    int rc = robot_gait_enum(GAIT_ADVANCE);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Walk backward for N ms, then stop. */
static inline int robot_walk_backward(int ms) {
    int rc = robot_gait_enum(GAIT_BACK);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Turn left (spin) for N ms, then stop. */
static inline int robot_turn_left(int ms) {
    int rc = robot_gait_enum(GAIT_TURN_L);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Turn right (spin) for N ms, then stop. */
static inline int robot_turn_right(int ms) {
    int rc = robot_gait_enum(GAIT_TURN_R);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Strafe left for N ms, then stop. */
static inline int robot_strafe_left(int ms) {
    int rc = robot_gait_enum(GAIT_LEFT);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Strafe right for N ms, then stop. */
static inline int robot_strafe_right(int ms) {
    int rc = robot_gait_enum(GAIT_RIGHT);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Perform a single jump. */
static inline void robot_jump(void) {
    robot_gait_enum(GAIT_JUMP);
    robot_delay_ms(2000);
    robot_gait_enum(GAIT_NONE);
}

/** Stand to init pose (blocks ~2 s). */
static inline void robot_stand(void) {
    robot_gait_enum(GAIT_INIT);
    robot_delay_ms(2000);
}

/** Do a fun dance for N ms. */
static inline void robot_dance(int ms) {
    robot_set_config(60, 60, 15, 8, 15);
    robot_gait_enum(GAIT_TWERK);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Step in place for N ms, then stop. */
static inline int robot_step_in_place(int ms) {
    int rc = robot_gait_enum(GAIT_STEP);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look up for N ms, using gait-based head control. */
static inline int robot_look_up(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_UP);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look down for N ms, using gait-based head control. */
static inline int robot_look_down(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_DOWN);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look left for N ms, using gait-based head control. */
static inline int robot_look_left(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_LEFT);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look right for N ms, using gait-based head control. */
static inline int robot_look_right(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_RIGHT);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look upper-left for N ms, using gait-based head control. */
static inline int robot_look_upper_left(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_UL);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look upper-right for N ms, using gait-based head control. */
static inline int robot_look_upper_right(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_UR);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look lower-left for N ms, using gait-based head control. */
static inline int robot_look_lower_left(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_LL);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Look lower-right for N ms, using gait-based head control. */
static inline int robot_look_lower_right(int ms) {
    int rc = robot_gait_enum(GAIT_LOOK_LR);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Lift left foreleg for N ms. */
static inline int robot_foreleg_lift_left(int ms) {
    int rc = robot_gait_enum(GAIT_FORELEG_LIFT_L);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Lift right foreleg for N ms. */
static inline int robot_foreleg_lift_right(int ms) {
    int rc = robot_gait_enum(GAIT_FORELEG_LIFT_R);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Lift left back leg for N ms. */
static inline int robot_backleg_lift_left(int ms) {
    int rc = robot_gait_enum(GAIT_BACKLEG_LIFT_L);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Lift right back leg for N ms. */
static inline int robot_backleg_lift_right(int ms) {
    int rc = robot_gait_enum(GAIT_BACKLEG_LIFT_R);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Raise body height for N ms. */
static inline int robot_height_up(int ms) {
    int rc = robot_gait_enum(GAIT_HEIGHT_UP);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Lower body height for N ms. */
static inline int robot_height_down(int ms) {
    int rc = robot_gait_enum(GAIT_HEIGHT_DOWN);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Balance on the spot for N ms. */
static inline int robot_balance(int ms) {
    int rc = robot_gait_enum(GAIT_BALANCE);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Bow backward for N ms. */
static inline int robot_bow_back(int ms) {
    int rc = robot_gait_enum(GAIT_BOW_BACK);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Cycle body for N ms. */
static inline int robot_body_cycle(int ms) {
    int rc = robot_gait_enum(GAIT_BODY_CYCLE);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Head ellipse motion for N ms. */
static inline int robot_head_ellipse(int ms) {
    int rc = robot_gait_enum(GAIT_HEAD_ELLIPSE);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Move left front leg for N ms. */
static inline int robot_move_lf(int ms) {
    int rc = robot_gait_enum(GAIT_MOVE_LF);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Move right front leg for N ms. */
static inline int robot_move_rf(int ms) {
    int rc = robot_gait_enum(GAIT_MOVE_RF);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Move left back leg for N ms. */
static inline int robot_move_lb(int ms) {
    int rc = robot_gait_enum(GAIT_MOVE_LB);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Move right back leg for N ms. */
static inline int robot_move_rb(int ms) {
    int rc = robot_gait_enum(GAIT_MOVE_RB);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Walk using the Stanford trot for N ms. */
static inline int robot_stanford_walk(int ms) {
    int rc = robot_gait_enum(GAIT_STANFORD);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Perform one front kick. */
static inline void robot_front_kick(void) {
    robot_gait_enum(GAIT_FRONT_KICK);
    robot_delay_ms(2000);
}

/** Wiggle the raised rear for N ms. */
static inline int robot_wiggle(int ms) {
    int rc = robot_gait_enum(GAIT_WIGGLE);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Perform the distinct front-up butt shrug for N ms. */
static inline int robot_butt_shrug(int ms) {
    int rc = robot_gait_enum(GAIT_BUTT_SHRUG);
    if (rc != MPX_OK) return rc;
    robot_delay_ms(ms);
    return robot_gait_enum(GAIT_NONE);
}

/** Hold any roll/pitch/yaw combination; the next movement interrupts it. */
static inline void robot_attitude(float roll_deg, float pitch_deg, float yaw_deg) {
    robot_set_body_pose(roll_deg, pitch_deg, yaw_deg);
}

/** Angle-only body controls, matching the reference movement API. */
static inline void robot_roll(float angle_deg)  { robot_set_body_pose(angle_deg, 0.0f, 0.0f); }
static inline void robot_pitch(float angle_deg) { robot_set_body_pose(0.0f, angle_deg, 0.0f); }
static inline void robot_yaw(float angle_deg)   { robot_set_body_pose(0.0f, 0.0f, angle_deg); }
static inline void robot_reset_attitude(void)   { robot_gait((int)"none"); }

/** Set the roll/pitch/yaw glide speed in degrees/second (0 = instant snap).
 *  Float-friendly wrapper around robot_set_attitude_speed(). */
static inline void robot_attitude_speed(float dps) { robot_set_attitude_speed((int)dps); }

/** Per-axis glide speed in degrees/second (0 on an axis = instant snap). */
static inline void robot_attitude_speed_xyz(float roll_dps, float pitch_dps, float yaw_dps) {
    robot_set_attitude_speed_xyz((int)roll_dps, (int)pitch_dps, (int)yaw_dps);
}

/** Set the glide speed AND move to a pose in one call. */
static inline void robot_attitude_at(float roll_deg, float pitch_deg,
                                     float yaw_deg, float dps) {
    robot_set_attitude_speed((int)dps);
    robot_set_body_pose(roll_deg, pitch_deg, yaw_deg);
}

// ──── 6. Full pose helper (all 12 servos at once) ────────────

typedef struct {
    float fr_hip, fr_shoulder, fr_knee;
    float fl_hip, fl_shoulder, fl_knee;
    float rr_hip, rr_shoulder, rr_knee;
    float rl_hip, rl_shoulder, rl_knee;
} robot_pose_t;

/** Apply a complete pose — sets all 12 servos and flushes. */
static inline void robot_apply_pose(robot_pose_t p) {
    robot_set_servo_angle(SERVO_FR_HIP,      (int)(p.fr_hip      * 100.0f));
    robot_set_servo_angle(SERVO_FR_SHOULDER,  (int)(p.fr_shoulder * 100.0f));
    robot_set_servo_angle(SERVO_FR_KNEE,      (int)(p.fr_knee     * 100.0f));
    robot_set_servo_angle(SERVO_FL_HIP,      (int)(p.fl_hip      * 100.0f));
    robot_set_servo_angle(SERVO_FL_SHOULDER,  (int)(p.fl_shoulder * 100.0f));
    robot_set_servo_angle(SERVO_FL_KNEE,      (int)(p.fl_knee     * 100.0f));
    robot_set_servo_angle(SERVO_RR_HIP,      (int)(p.rr_hip      * 100.0f));
    robot_set_servo_angle(SERVO_RR_SHOULDER,  (int)(p.rr_shoulder * 100.0f));
    robot_set_servo_angle(SERVO_RR_KNEE,      (int)(p.rr_knee     * 100.0f));
    robot_set_servo_angle(SERVO_RL_HIP,      (int)(p.rl_hip      * 100.0f));
    robot_set_servo_angle(SERVO_RL_SHOULDER,  (int)(p.rl_shoulder * 100.0f));
    robot_set_servo_angle(SERVO_RL_KNEE,      (int)(p.rl_knee     * 100.0f));
    robot_flush();
}

// ──── 7. Integer printing (for debugging) ─────────────────────

/** Print an integer to the robot's log (handles negatives). */
static inline void MPX_print_int(int value) {
    char buf[16];
    int  pos      = 15;
    int  negative = 0;

    buf[14] = '\n';
    buf[15] = '\0';

    if (value < 0) {
        negative = 1;
        value = -value;
    }

    if (value == 0) {
        buf[--pos] = '0';
    } else {
        while (value > 0 && pos > 0) {
            buf[--pos] = '0' + (value % 10);
            value /= 10;
        }
    }

    if (negative && pos > 0) {
        buf[--pos] = '-';
    }

    print((int)(buf + pos), 15 - pos);
}


/* ═══════════════════════════════════════════════════════════════════
 *  LOW-LEVEL SERVO CONTROL  (AT32 driver boards)
 *
 *  Direct joint control, in the shape unitree_legged_sdk uses: you write a
 *  command per joint and read a state per joint. What differs is dictated by
 *  the hardware, and it matters:
 *
 *    Unitree streams {q, dq, tau, Kp, Kd} per joint every tick. On the AT32
 *    boards only position and the current limit ride on the fast frame. The
 *    gains (Kp position, Kd position, Kp current, Kff current, max PWM duty)
 *    are CONFIG parameters: each write is a request/reply pair over SPI,
 *    ~1 ms, and it cannot interleave with gait traffic. Set them once at the
 *    top of your skill, then stream commands.
 *
 *  Angles here are the RAW AT32 angle, 0..270°, with 135° at mechanical
 *  centre. This is NOT the gait's calibrated frame and NOT the ±90° relative
 *  frame robot_set_servo_angle() uses — nothing subtracts your calibration
 *  offsets, and nothing clamps to the IK's reachable range.
 *
 *  Every call below requires the bus lock EXCEPT servo_read() and
 *  servo_read_all(), which are served from the feedback cache.
 *  servo_scan() and servo_poll() DO require it despite reading — they
 *  put traffic on the bus. (This header used to claim otherwise.)
 *
 *  "The bus lock" means YOU hold it. If Servo Studio has the bus, these
 *  calls return -2 even though the bus is busy: a skill that never
 *  called servo_lock() must never drive joints, and it used to be able
 *  to whenever someone had Studio open.
 *
 *  Return codes: 0 ok, -1 bad argument or bad pointer, -2 bus not
 *  locked by you, -3 the board did not answer, -4 read-only parameter.
 * ═══════════════════════════════════════════════════════════════════ */

/** Servo config parameter IDs — the addresses shown in Servo Studio. */
typedef enum {
    MPX_PARAM_REVERSE_POSITION_SENSOR = 0,
    MPX_PARAM_MIN_POSITION_ADC        = 1,
    MPX_PARAM_MAX_POSITION_ADC        = 2,
    MPX_PARAM_RANGE_POSITION_DEG      = 3,
    MPX_PARAM_REVERSE_MOTOR           = 4,
    MPX_PARAM_KP_POSITION             = 5,
    MPX_PARAM_KD_POSITION             = 6,
    MPX_PARAM_KP_CURRENT              = 7,
    MPX_PARAM_KFF_CURRENT             = 8,
    MPX_PARAM_MAX_PWM_DUTY            = 9,
    MPX_PARAM_COUNT                   = 10
} mpx_servo_param_t;

/** Control mode for mpx_servo_direct(). */
typedef enum {
    MPX_SERVO_IDLE     = 0,   /* motor off — the joint goes limp     */
    MPX_SERVO_POSITION = 1,   /* hold a position, current-limited    */
    MPX_SERVO_TORQUE   = 2    /* current (torque) control            */
} mpx_servo_mode_t;

/**
 * @brief One joint's command. Matches the float layout servo_write_all reads.
 *
 * @note kp/kd are sent in the per-servo wire frame, but the stock AT32
 *       firmware IGNORES them and uses its stored config gains instead.
 *       Leave them 0 unless your board firmware is known to honour per-frame
 *       gains — see HOST_FUNCTIONS.md. This is the one field here whose
 *       behaviour depends on which AT32 build you flashed.
 */
typedef struct {
    float q_deg;    /* target angle, raw 0..270° (135 = centre)      */
    float tau_ma;   /* current limit in mA — a ceiling, not a demand */
    float kp;       /* per-frame position gain, 0 = use stored gain  */
    float kd;       /* per-frame damping gain,  0 = use stored gain  */
} mpx_servo_cmd_t;

/**
 * @brief One joint's measured state.
 *
 * @note There is deliberately no velocity field: the driver boards do not
 *       measure one, and a hardcoded zero named "dq" would be a lie.
 *       Differentiate q_deg yourself if you need it.
 */
typedef struct {
    float q_deg;    /* present angle, raw 0..270°                    */
    float tau_ma;   /* present motor current, mA (signed)            */
    float temp_c;   /* NTC temperature °C — NaN if never reported    */
    float q_raw;    /* the same position on the SCS 0..1023 scale    */
} mpx_servo_state_t;

/* ── Bus ownership ───────────────────────────────────────────────── */

/**
 * @brief Take the servo bus. Parks the gait; the robot holds its last pose.
 *
 * Wasm import:  extern int servo_lock(void);
 * WAMR sig:     "()i"
 *
 * @return 0 on success, -1 if Servo Studio currently holds the bus.
 * @note The sandbox releases this automatically when your skill returns or is
 *       killed, so a crash cannot leave the robot parked. Still call
 *       servo_unlock() when you are done — the gait resumes sooner.
 */
extern int servo_lock(void);

/** @brief Release the bus and resume the gait. WAMR sig: "()i" */
extern int servo_unlock(void);

/** @brief 1 if anything currently holds the bus, else 0. WAMR sig: "()i" */
extern int servo_is_locked(void);

/* ── Gains (config path — slow, set once) ────────────────────────── */

/**
 * @brief Write one control gain to a servo's RAM.
 *
 * Wasm import:  extern int servo_set_gain(int id, int param, float value);
 * WAMR sig:     "(iif)i"
 *
 * @param id     Servo ID (1-12)
 * @param param  An mpx_servo_param_t
 * @return 0 ok, -1 bad argument, -2 bus not locked, -3 no reply from board
 * @note RAM only — call servo_save_config() to survive a power cycle.
 */
extern int servo_set_gain(int id, int param, float value);

/**
 * @brief Read one control gain back from the board.
 * WAMR sig: "(iii)i"   (out points at a single float)
 * @return 0 ok, -1 bad argument, -2 bus not locked, -3 no reply
 */
extern int servo_get_gain(int id, int param, float *out);

/**
 * @brief Commit a board's gains to its flash. id 0 = all four boards.
 * WAMR sig: "(i)i"
 */
extern int servo_save_config(int id);

/**
 * @brief Load factory defaults into RAM. id 0 = all four boards.
 * WAMR sig: "(i)i"
 * @note RAM only — follow with servo_save_config() to keep them.
 */
extern int servo_restore_config(int id);

/* ── Commands (fast path) ────────────────────────────────────────── */

/**
 * @brief Stage one joint's command without touching the bus.
 * WAMR sig: "(iffff)i"
 * @note Nothing moves until servo_commit().
 */
extern int servo_stage(int id, float q_deg, float tau_ma, float kp, float kd);

/**
 * @brief Push every staged command — four SPI frames for all twelve joints.
 * WAMR sig: "()i"
 */
extern int servo_commit(void);

/**
 * @brief Stage and commit an array of commands in one call.
 *
 * Wasm import:  extern int servo_write_all(const void *cmd, int count);
 * WAMR sig:     "(ii)i"
 *
 * @param cmd    Array of mpx_servo_cmd_t, index 0 = servo 1
 * @param count  1..12
 * @return 0 ok, -1 bad argument, -2 bus not locked, -3 a board did not answer
 */
extern int servo_write_all(const void *cmd, int count);

/**
 * @brief Drive one joint immediately, including motor-off and torque mode.
 * WAMR sig: "(iiff)i"
 * @param mode  An mpx_servo_mode_t
 */
extern int servo_direct(int id, int mode, float q_deg, float tau_ma);

/* ── State ───────────────────────────────────────────────────────── */

/** @brief Read one joint into an mpx_servo_state_t. WAMR sig: "(ii)i" */
extern int servo_read(int id, void *out);

/** @brief Read all twelve into an mpx_servo_state_t[12]. WAMR sig: "(i)i" */
extern int servo_read_all(void *out);

/**
 * @brief Refresh the feedback cache while the gait is parked.
 * WAMR sig: "()i"
 * @note Only needed while you hold the bus. With the gait running the cache is
 *       refreshed every tick for free, so servo_read*() is already live.
 */
extern int servo_poll(void);

/**
 * @brief Probe all twelve channels.
 * WAMR sig: "()i"
 * @return Bitmask of servos that answered — bit 0 is servo 1. Negative on
 *         error. A whole silent board of three points at that board's CS line
 *         or its power, not at the servos.
 */
extern int servo_scan(void);

/* ── Convenience wrappers ────────────────────────────────────────── */

/**
 * @brief Set the position loop gains on every joint at once.
 * @return 0 if all twelve took the write, else the count that failed (>0).
 */
static inline int mpx_servo_set_all_gains(float kp, float kd)
{
    int failed = 0;
    for (int id = 1; id <= 12; ++id) {
        if (servo_set_gain(id, MPX_PARAM_KP_POSITION, kp) != 0) { failed++; continue; }
        if (servo_set_gain(id, MPX_PARAM_KD_POSITION, kd) != 0) { failed++; }
    }
    return failed;
}

/** @brief Hold every joint at mechanical centre with a gentle current cap. */
static inline int mpx_servo_all_centre(float tau_ma)
{
    mpx_servo_cmd_t cmd[12];
    for (int i = 0; i < 12; ++i) {
        cmd[i].q_deg = 135.0f;
        cmd[i].tau_ma = tau_ma;
        cmd[i].kp = 0.0f;
        cmd[i].kd = 0.0f;
    }
    return servo_write_all(cmd, 12);
}

/** @brief Cut power to every motor — the joints go limp. */
static inline int mpx_servo_all_off(void)
{
    int failed = 0;
    for (int id = 1; id <= 12; ++id) {
        if (servo_direct(id, MPX_SERVO_IDLE, 135.0f, 0.0f) != 0) failed++;
    }
    return failed;
}

/* ═══════════════════════════════════════════════════════════════════
 *  Quick reference: see the declarations above for the full function list
 *  (raw imports in Part 1, high-level helpers in Part 2).
 * ═══════════════════════════════════════════════════════════════════ */

#ifdef __cplusplus
}
#endif

#endif /* MPX_HOST_H */
