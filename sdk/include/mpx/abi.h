/* mpx/abi.h — the raw host imports, exactly as the firmware registers them.
 *
 * YOU ALMOST CERTAINLY DO NOT WANT THIS FILE.
 *
 * Every symbol here is a WebAssembly import: a function that lives in the
 * robot's firmware, not in your module. The names, argument types and return
 * types must match `abi/host_functions.json` byte for byte, because WAMR
 * checks the signature at instantiation and refuses a module that disagrees.
 * That is why they are ugly — `print(int, int)` rather than a string, angles
 * as centidegrees rather than degrees. They are a wire format.
 *
 * The rest of the SDK is a zero-cost layer over this file: every helper in
 * mpx/sys.h, mpx/robot.h, mpx/leg.h, mpx/bus.h and mpx/motion.h is a
 * `static inline` that compiles down to one of these calls with nothing
 * added. Read this file to understand what a call really costs, or to reach
 * something the friendly layer has not wrapped yet. Otherwise use `mpx.h`.
 *
 * GENERATED — regenerate with `python tools/gen_abi.py --emit-c`.
 * Hand edits are overwritten and, worse, can silently disagree with the
 * firmware. Change `abi/host_functions.json` (or the firmware table it is
 * extracted from) instead.
 */
#ifndef MPX_ABI_H
#define MPX_ABI_H

#ifdef __cplusplus
extern "C" {
#endif

/* The ABI this header describes. Compare against mpx_abi_version() at run
 * time: a mismatch means the module was built against a different firmware,
 * which shows up otherwise as an unexplained trap on the first host call. */
#define MPX_ABI_VERSION 4

/* ── v1: logging ─────────────────────────────────────────────────────────── */
extern int print(int text_ptr, int len);

/* ── v2: ABI introspection ───────────────────────────────────────────────── */
extern int mpx_abi_version(void);

/* ── v1/v2: gaits and body attitude ──────────────────────────────────────── */
extern int robot_gait(int name_ptr);
extern int robot_get_mode(void);
extern int robot_set_body_pose(float roll_deg, float pitch_deg, float yaw_deg);
extern int robot_set_attitude_speed(int dps);
extern int robot_set_attitude_speed_xyz(int roll_dps, int pitch_dps, int yaw_dps);

/* ── v1/v2: gait configuration ───────────────────────────────────────────── */
extern int robot_set_config(int period, int height, int up_height,
                            int stride, int tilt);
extern int robot_get_period(void);
extern int robot_get_height(void);
extern int robot_get_up_height(void);
extern int robot_get_stride(void);
extern int robot_get_tilt(void);

/* ── v1/v2: joints, in centidegrees relative to centre ───────────────────── */
extern int robot_set_servo_angle(int id, int centideg);
extern int robot_flush(void);
extern int robot_set_servo_speed(int id, int speed);
extern int robot_read_position(int id);       /* raw 0..1023, ABSOLUTE frame  */
extern int robot_read_angle_cdeg(int id);     /* centideg, RELATIVE frame     */
extern int robot_read_speed(int id);
extern int robot_read_load(int id);
extern int robot_read_voltage(int id);        /* 0.1 V units                  */
extern int robot_read_temperature(int id);    /* whole degrees C              */
extern int robot_read_moving(int id);
extern int robot_read_current(int id);        /* mA, signed                   */

/* ── v1/v2: calibration ──────────────────────────────────────────────────── */
extern int robot_set_offset(int id, int centideg);
extern int robot_get_offset(int id);
extern int robot_ping_servo(int id);

/* ── v1/v2: timing ───────────────────────────────────────────────────────── */
extern int robot_delay_ms(int ms);

/* ── v1/v2: per-leg inverse kinematics ───────────────────────────────────── */
extern int robot_ik_fr(float x, float th0, float z);
extern int robot_ik_fl(float x, float th0, float z);
extern int robot_ik_rr(float x, float th0, float z);
extern int robot_ik_rl(float x, float th0, float z);

/* ── v1/v2: IMU ──────────────────────────────────────────────────────────── */
extern int robot_imu_read(int buffer_ptr);    /* 6 floats: ax ay az gx gy gz  */
extern int robot_imu_print(void);

/* ── v2: servo bus, ABSOLUTE degrees (0..270, 135 = centre) ──────────────── */
extern int servo_lock(void);
extern int servo_unlock(void);
extern int servo_is_locked(void);
extern int servo_set_gain(int id, int param, float value);
extern int servo_get_gain(int id, int param, float *out);
extern int servo_save_config(int id);
extern int servo_restore_config(int id);
extern int servo_stage(int id, float q_deg, float tau_ma, float kp, float kd);
extern int servo_commit(void);
extern int servo_write_all(const void *cmd, int count);
extern int servo_read(int id, void *out);
extern int servo_read_all(void *out);
extern int servo_poll(void);
extern int servo_direct(int id, int mode, float q_deg, float tau_ma);
extern int servo_scan(void);

/* ── v3: control arbitration ─────────────────────────────────────────────── */
extern int mpx_control_take(int domain);
extern int mpx_control_release(void);
extern int mpx_control_owner(void);

/* ── v3: clock ───────────────────────────────────────────────────────────── */
extern int mpx_millis(void);
extern int mpx_sleep_until(int t_ms);

/* ── v3: continuous drive ────────────────────────────────────────────────── */
extern int mpx_drive(float fwd, float strafe, float turn);
extern int mpx_drive_stop(void);
extern int mpx_set_walk_speed(int mm_s);
extern int mpx_get_walk_speed(void);

/* ── v3: foot placement ──────────────────────────────────────────────────── */
extern int mpx_foot(int leg, float x, float th0, float z);

/* ── v3: capabilities that existed in the firmware but not in the ABI ────── */
extern int   mpx_set_all_servo_speed(int speed);
extern int   mpx_reset_offsets(void);
extern float mpx_read_temperature_c(int id);

/* ── v3: per-run parameters ──────────────────────────────────────────────── */
extern float mpx_param_f(const char *name, float fallback);
extern int   mpx_param_i(const char *name, int fallback);

/* ── v4: composing with the gait, ticking, and being seen ────────────────── */
extern int   mpx_overlay(int joint, float deg);
extern float mpx_overlay_get(int joint);
extern int   mpx_overlay_clear(void);
extern int   mpx_tick_every(int period_ms);
extern int   mpx_tick_stop(void);
extern int   mpx_trace(const char *name, float value);

#ifdef __cplusplus
}
#endif
#endif /* MPX_ABI_H */
