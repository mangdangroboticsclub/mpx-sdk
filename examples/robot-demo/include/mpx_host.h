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
 *   "none"      Stop all gait
 *   "init"      Return to init/stand pose
 *   "step"      Step in place
 *   "roll"      Roll body
 *   "pitch"     Pitch body
 *   "stretch"   Stretch legs
 *   "advance"   Walk forward
 *   "back"      Walk backward
 *   "left"      Sidestep left
 *   "right"     Sidestep right
 *   "turnL"     Turn left
 *   "turnR"     Turn right
 *   "twerk"     Twerk!
 *   "jump"      Jump
 *   "jumpfwd"   Jump forward
 *   "testspeed" Speed test
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

/* ═══════════════════════════════════════════════════════════════════
 *  Quick reference — all available functions:
 *
 *   void   MPX_print(const char *str, int len);
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
 *   void   robot_set_offset(int id, int centideg);
 *   int    robot_get_offset(int id);
 *   int    robot_ping_servo(int id);
 *   void   robot_delay_ms(int ms);
 * ═══════════════════════════════════════════════════════════════════ */

#ifdef __cplusplus
}
#endif

#endif /* MPX_HOST_H */
