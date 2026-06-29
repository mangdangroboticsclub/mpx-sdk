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
extern void print(int ptr, int len);

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
 * Wasm import:  extern void robot_gait(int name_ptr);
 * WAMR sig:     "($)"  — name string (auto-converted)
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
 */
extern void robot_gait(int name_ptr);

/**
 * @brief Get current gait mode as integer.
 *
 * Wasm import:  extern int robot_get_mode(void);
 * WAMR sig:     "()i"
 *
 * @return Gait mode: 0=None, 1=Init, 2=Step, ...
 */
extern int robot_get_mode(void);

/* ── Configuration ───────────────────────────────────────────── */

/**
 * @brief Set all gait parameters at once.
 *
 * Wasm import:  extern void robot_set_config(int period, int height,
 *                   int up_height, int stride, int tilt);
 * WAMR sig:     "(iiiii)"
 *
 * @param period     Gait period in milliseconds (e.g. 100)
 * @param height     Body height in millimeters (e.g. 70)
 * @param up_height  Foot lift height in millimeters (e.g. 10)
 * @param stride     Stride length in millimeters (e.g. 10)
 * @param tilt       Max tilt angle in degrees (e.g. 10)
 */
extern void robot_set_config(int period, int height,
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
 * Wasm import:  extern void robot_set_servo_angle(int id, int centideg);
 * WAMR sig:     "(ii)"
 *
 * @param id        Servo ID (1-12)
 * @param centideg  Target angle in centidegrees (e.g. 4500 = 45.00°)
 */
extern void robot_set_servo_angle(int id, int centideg);

/**
 * @brief Send all buffered servo commands to the bus.
 * WAMR sig:     "()"
 */
extern void robot_flush(void);

/**
 * @brief Set servo movement speed.
 *
 * Wasm import:  extern void robot_set_servo_speed(int id, int speed);
 * WAMR sig:     "(ii)"
 *
 * @param id     Servo ID (1-12)
 * @param speed  0 = max speed, higher values = slower
 */
extern void robot_set_servo_speed(int id, int speed);

/**
 * @brief Read a servo's current position.
 *
 * Wasm import:  extern int robot_read_position(int id);
 * WAMR sig:     "(i)i"
 *
 * @param  id  Servo ID (1-12)
 * @return Raw position (0-1023), or -1 on error
 */
extern int robot_read_position(int id);

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
 * Wasm import:  extern void robot_set_offset(int id, int centideg);
 * WAMR sig:     "(ii)"
 *
 * @param id        Servo ID (1-12)
 * @param centideg  Offset in centidegrees (e.g. 150 = 1.50°)
 */
extern void robot_set_offset(int id, int centideg);

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
 * Wasm import:  extern void robot_delay_ms(int ms);
 * WAMR sig:     "(i)"
 *
 * IMPORTANT: This is the ONLY reliable way to pause between gait
 * commands from a WASM skill. Pure-WASM busy-loops run at near-zero
 * wall time inside the interpreter and won't produce real delays.
 *
 * @param ms  Milliseconds to block (uses vTaskDelay internally)
 */
extern void robot_delay_ms(int ms);

/* ── Inverse Kinematics (per-leg) ──────────────────────────────── */

/**
 * @brief Front-right leg IK target.
 *
 * Wasm import:  extern void robot_ik_fr(float x, float th0, float z);
 * WAMR sig:     "(fff)"
 *
 * @param x    Forward/backward position in mm
 * @param th0  Hip rotation angle in degrees
 * @param z    Height in mm
 */
extern void robot_ik_fr(float x, float th0, float z);

/**
 * @brief Front-left leg IK target.
 *
 * Wasm import:  extern void robot_ik_fl(float x, float th0, float z);
 * WAMR sig:     "(fff)"
 */
extern void robot_ik_fl(float x, float th0, float z);

/**
 * @brief Rear-right leg IK target.
 *
 * Wasm import:  extern void robot_ik_rr(float x, float th0, float z);
 * WAMR sig:     "(fff)"
 */
extern void robot_ik_rr(float x, float th0, float z);

/**
 * @brief Rear-left leg IK target.
 *
 * Wasm import:  extern void robot_ik_rl(float x, float th0, float z);
 * WAMR sig:     "(fff)"
 */
extern void robot_ik_rl(float x, float th0, float z);

/* ── IMU ───────────────────────────────────────────────────────── */

/**
 * @brief Read IMU 6-DOF data into a WASM buffer.
 *
 * Wasm import:  extern void robot_imu_read(int buffer_ptr);
 * WAMR sig:     "(i)"
 *
 * Buffer must be at least 6 × 4 = 24 bytes. Layout:
 *   float[0] = ax (accel X, g)
 *   float[1] = ay (accel Y, g)
 *   float[2] = az (accel Z, g)
 *   float[3] = gx (gyro X, dps)
 *   float[4] = gy (gyro Y, dps)
 *   float[5] = gz (gyro Z, dps)
 */
extern void robot_imu_read(int buffer_ptr);

/**
 * @brief Print the latest IMU data to the robot's log.
 *
 * Wasm import:  extern void robot_imu_print(void);
 * WAMR sig:     "()"
 */
extern void robot_imu_print(void);

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
} robot_gait_t;

/**
 * @brief Start a gait using the type-safe enum.
 *
 * Internally maps enum → string → robot_gait().  No more
 * typos like "advnce" silently failing.
 */
static inline void robot_gait_enum(robot_gait_t g) {
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
    };
    if (g >= GAIT_NONE && g <= GAIT_MOVE_RB) {
        robot_gait((int)names[(int)g]);
    }
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
static inline void robot_set_servo_deg(robot_servo_t id, float deg) {
    robot_set_servo_angle((int)id, (int)(deg * 100.0f));
}

/** Set servo angle in raw 0-1023 units (maps 0°→0, 300°→1023). */
static inline void robot_set_servo_raw(robot_servo_t id, int raw) {
    robot_set_servo_angle((int)id, (raw * 30000) / 1023);
}

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
static inline void robot_walk_forward(int ms) {
    robot_gait_enum(GAIT_ADVANCE);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Walk backward for N ms, then stop. */
static inline void robot_walk_backward(int ms) {
    robot_gait_enum(GAIT_BACK);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Turn left (spin) for N ms, then stop. */
static inline void robot_turn_left(int ms) {
    robot_gait_enum(GAIT_TURN_L);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Turn right (spin) for N ms, then stop. */
static inline void robot_turn_right(int ms) {
    robot_gait_enum(GAIT_TURN_R);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Strafe left for N ms, then stop. */
static inline void robot_strafe_left(int ms) {
    robot_gait_enum(GAIT_LEFT);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Strafe right for N ms, then stop. */
static inline void robot_strafe_right(int ms) {
    robot_gait_enum(GAIT_RIGHT);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
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
static inline void robot_step_in_place(int ms) {
    robot_gait_enum(GAIT_STEP);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look up for N ms, using gait-based head control. */
static inline void robot_look_up(int ms) {
    robot_gait_enum(GAIT_LOOK_UP);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look down for N ms, using gait-based head control. */
static inline void robot_look_down(int ms) {
    robot_gait_enum(GAIT_LOOK_DOWN);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look left for N ms, using gait-based head control. */
static inline void robot_look_left(int ms) {
    robot_gait_enum(GAIT_LOOK_LEFT);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look right for N ms, using gait-based head control. */
static inline void robot_look_right(int ms) {
    robot_gait_enum(GAIT_LOOK_RIGHT);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look upper-left for N ms, using gait-based head control. */
static inline void robot_look_upper_left(int ms) {
    robot_gait_enum(GAIT_LOOK_UL);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look upper-right for N ms, using gait-based head control. */
static inline void robot_look_upper_right(int ms) {
    robot_gait_enum(GAIT_LOOK_UR);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look lower-left for N ms, using gait-based head control. */
static inline void robot_look_lower_left(int ms) {
    robot_gait_enum(GAIT_LOOK_LL);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Look lower-right for N ms, using gait-based head control. */
static inline void robot_look_lower_right(int ms) {
    robot_gait_enum(GAIT_LOOK_LR);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Lift left foreleg for N ms. */
static inline void robot_foreleg_lift_left(int ms) {
    robot_gait_enum(GAIT_FORELEG_LIFT_L);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Lift right foreleg for N ms. */
static inline void robot_foreleg_lift_right(int ms) {
    robot_gait_enum(GAIT_FORELEG_LIFT_R);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Lift left back leg for N ms. */
static inline void robot_backleg_lift_left(int ms) {
    robot_gait_enum(GAIT_BACKLEG_LIFT_L);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Lift right back leg for N ms. */
static inline void robot_backleg_lift_right(int ms) {
    robot_gait_enum(GAIT_BACKLEG_LIFT_R);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Raise body height for N ms. */
static inline void robot_height_up(int ms) {
    robot_gait_enum(GAIT_HEIGHT_UP);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Lower body height for N ms. */
static inline void robot_height_down(int ms) {
    robot_gait_enum(GAIT_HEIGHT_DOWN);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Balance on the spot for N ms. */
static inline void robot_balance(int ms) {
    robot_gait_enum(GAIT_BALANCE);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Bow backward for N ms. */
static inline void robot_bow_back(int ms) {
    robot_gait_enum(GAIT_BOW_BACK);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Cycle body for N ms. */
static inline void robot_body_cycle(int ms) {
    robot_gait_enum(GAIT_BODY_CYCLE);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Head ellipse motion for N ms. */
static inline void robot_head_ellipse(int ms) {
    robot_gait_enum(GAIT_HEAD_ELLIPSE);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Move left front leg for N ms. */
static inline void robot_move_lf(int ms) {
    robot_gait_enum(GAIT_MOVE_LF);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Move right front leg for N ms. */
static inline void robot_move_rf(int ms) {
    robot_gait_enum(GAIT_MOVE_RF);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Move left back leg for N ms. */
static inline void robot_move_lb(int ms) {
    robot_gait_enum(GAIT_MOVE_LB);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
}

/** Move right back leg for N ms. */
static inline void robot_move_rb(int ms) {
    robot_gait_enum(GAIT_MOVE_RB);
    robot_delay_ms(ms);
    robot_gait_enum(GAIT_NONE);
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
 *  Quick reference — all functions:
 *
 *  ── Raw imports (Part 1) ──────────────────────────────────
 *   void   print(int ptr, int len);
 *   void   robot_gait(int name_ptr);
 *   int    robot_get_mode(void);
 *   void   robot_set_config(int period, int height,
 *                           int up_height, int stride, int tilt);
 *   int    robot_get_period(void);
 *   int    robot_get_height(void);
 *   int    robot_get_up_height(void);
 *   int    robot_get_stride(void);
 *   int    robot_get_tilt(void);
 *   void   robot_set_servo_angle(int id, int centideg);
 *   void   robot_flush(void);
 *   void   robot_set_servo_speed(int id, int speed);
 *   int    robot_read_position(int id);
 *   int    robot_read_speed(int id);
 *   int    robot_read_load(int id);
 *   int    robot_read_voltage(int id);
 *   int    robot_read_temperature(int id);
 *   int    robot_read_moving(int id);
 *   int    robot_read_current(int id);
 *   void   robot_set_offset(int id, int centideg);
 *   int    robot_get_offset(int id);
 *   int    robot_ping_servo(int id);
 *   void   robot_delay_ms(int ms);
 *   void   robot_ik_fr(float x, float th0, float z);
 *   void   robot_ik_fl(float x, float th0, float z);
 *   void   robot_ik_rr(float x, float th0, float z);
 *   void   robot_ik_rl(float x, float th0, float z);
 *   void   robot_imu_read(int buffer_ptr);
 *   void   robot_imu_print(void);
 *
 *  ── High-level (Part 2) ───────────────────────────────────
 *   void   robot_gait_enum(robot_gait_t g);
 *   void   robot_set_servo_deg(robot_servo_t id, float deg);
 *   void   robot_set_servo_raw(robot_servo_t id, int raw);
 *   void   robot_set_servo(robot_servo_t id, float deg, int speed);
 *   void   robot_set_config_ex(robot_config_t cfg);
 *   robot_config_t robot_get_config_ex(void);
 *   void   robot_walk_forward(int ms);
 *   void   robot_walk_backward(int ms);
 *   void   robot_turn_left(int ms);
 *   void   robot_turn_right(int ms);
 *   void   robot_strafe_left(int ms);
 *   void   robot_strafe_right(int ms);
 *   void   robot_jump(void);
 *   void   robot_stand(void);
 *   void   robot_dance(int ms);
 *   void   robot_step_in_place(int ms);
 *   void   robot_look_up(int ms);
 *   void   robot_look_down(int ms);
 *   void   robot_look_left(int ms);
 *   void   robot_look_right(int ms);
 *   void   robot_look_upper_left(int ms);
 *   void   robot_look_upper_right(int ms);
 *   void   robot_look_lower_left(int ms);
 *   void   robot_look_lower_right(int ms);
 *   void   robot_foreleg_lift_left(int ms);
 *   void   robot_foreleg_lift_right(int ms);
 *   void   robot_backleg_lift_left(int ms);
 *   void   robot_backleg_lift_right(int ms);
 *   void   robot_height_up(int ms);
 *   void   robot_height_down(int ms);
 *   void   robot_balance(int ms);
 *   void   robot_bow_back(int ms);
 *   void   robot_body_cycle(int ms);
 *   void   robot_head_ellipse(int ms);
 *   void   robot_move_lf(int ms);
 *   void   robot_move_rf(int ms);
 *   void   robot_move_lb(int ms);
 *   void   robot_move_rb(int ms);
 *   void   robot_apply_pose(robot_pose_t p);
 *   void   MPX_print_int(int value);
 * ═══════════════════════════════════════════════════════════════════ */

#ifdef __cplusplus
}
#endif

#endif /* MPX_HOST_H */
