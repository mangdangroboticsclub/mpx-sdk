/* mpx/robot.h — whole-robot movement: gaits, driving, body attitude.
 *
 * This is the layer to reach for first. Everything here moves all four legs
 * in a coordinated way that the firmware already knows is stable, so it is
 * very hard to hurt the robot from this file.
 *
 * Go down to mpx/leg.h when you need to place a specific foot, and to
 * mpx/bus.h when you need to own a motor's control loop. See
 * docs/MOVEMENT.md for which layer owns what.
 */
#ifndef MPX_ROBOT_H
#define MPX_ROBOT_H

#include "mpx/abi.h"
#include "mpx/sys.h"
#include "mpx/gaits.h"
#include "mpx/math.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ═══════════════════════════════════════════════════════════════════════════
 *  Control domains
 *
 *  Four things in this firmware can move a joint: the gait generator, the
 *  built-in foot IK, your own joint writes, and the servo bus. They share one
 *  goal buffer, so if two of them write in the same 15 ms window the last one
 *  wins and the result looks like a glitch rather than a conflict.
 *
 *  Claiming a domain makes that conflict loud instead of silent: while you
 *  hold one, a call belonging to a different domain returns MPX_ERR_BUSY
 *  rather than quietly interleaving.
 *
 *      mpx_take(MPX_OWN_FEET);          // I am placing feet; nothing else may
 *      ...
 *      mpx_release();
 *
 *  This is opt-in. A skill that never calls mpx_take() sees exactly the
 *  behaviour it saw before this existed, so nothing you have already written
 *  changes meaning. Claim a domain when you are debugging a fight between
 *  layers, or when a routine must not be interfered with.
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef enum {
    MPX_OWN_NONE   = 0,  /**< Unclaimed: anything may write (the default).    */
    MPX_OWN_GAIT   = 1,  /**< Gaits, driving and body attitude.               */
    MPX_OWN_FEET   = 2,  /**< Foot placement through the built-in IK.         */
    MPX_OWN_JOINTS = 3,  /**< Direct joint angles.                            */
    MPX_OWN_BUS    = 4,  /**< The servo bus (see mpx/bus.h).                  */
} mpx_domain_t;

/** Claim a domain. MPX_OK, or MPX_ERR_BUSY if another domain holds it. */
static inline int mpx_take(mpx_domain_t d) { return mpx_control_take((int)d); }

/** Give the claim back. Always succeeds. */
static inline int mpx_release(void) { return mpx_control_release(); }

/** Which domain currently holds the joints, or MPX_OWN_NONE. */
static inline mpx_domain_t mpx_owner(void)
{
    return (mpx_domain_t)mpx_control_owner();
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Gaits — the robot's own movements
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Start a gait and return immediately. It keeps running until you change it. */
static inline int mpx_gait(mpx_gait_t g) { return robot_gait((int)mpx_gait_name(g)); }

/** Stop whatever gait is running. The robot holds its current pose. */
static inline int mpx_gait_stop(void) { return robot_gait((int)"none"); }

/** Return to the neutral standing pose and wait for it to settle. */
static inline int mpx_stand(void)
{
    int rc = mpx_gait(MPX_GAIT_STAND);
    if (rc != MPX_OK) return rc;
    return mpx_sleep(800);
}

/** Start a gait, hold it for `ms`, then stop. Blocks for the duration. */
static inline int mpx_gait_for(mpx_gait_t g, int ms)
{
    int rc = mpx_gait(g);
    if (rc != MPX_OK) return rc;
    rc = mpx_sleep(ms);
    if (rc != MPX_OK) return rc;      /* cancelled — do not issue another call */
    return mpx_gait_stop();
}

/** As mpx_gait_for(), using the duration the catalogue suggests. */
static inline int mpx_gait_once(mpx_gait_t g)
{
    int ms = mpx_gait_typical_ms(g);
    return mpx_gait_for(g, ms > 0 ? ms : 1500);
}

/** Which gait is running, as the firmware's numbering. */
static inline int mpx_gait_current(void) { return robot_get_mode(); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Driving — continuous, analog movement
 *
 *  A gait is a switch: forward, or not forward. Driving is a stick. Each axis
 *  runs -1 to +1 and they combine, so "forward at a third of speed while
 *  turning gently left" is one call:
 *
 *      mpx_drive_at(0.33f, 0.0f, -0.2f);
 *
 *  This is the same path the robot's own phone UI uses for its thumbsticks.
 *  Values persist until you change them, so a skill that drives must stop
 *  driving before it ends — mpx_drive_for() does that for you.
 *
 *  How fast "1.0" actually is depends on mpx_walk_speed_set().
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Set the drive vector. fwd/strafe/turn each -1..+1; values persist. */
static inline int mpx_drive_at(float fwd, float strafe, float turn)
{
    return mpx_drive(fwd, strafe, turn);
}

/** Stop driving. Always call this before your skill ends. */
static inline int mpx_stop(void) { return mpx_drive_stop(); }

/** Drive for `ms`, then stop. */
static inline int mpx_drive_for(float fwd, float strafe, float turn, int ms)
{
    int rc = mpx_drive(fwd, strafe, turn);
    if (rc != MPX_OK) return rc;
    rc = mpx_sleep(ms);
    mpx_drive_stop();                  /* stop even if we were cancelled */
    return rc;
}

/** Top walking speed in mm/s that a drive value of 1.0 means. Clamped 10..200
 *  by the firmware. 200 is genuinely fast; 40-80 looks controlled. */
static inline int mpx_walk_speed_set(int mm_s) { return mpx_set_walk_speed(mm_s); }
static inline int mpx_walk_speed(void)         { return mpx_get_walk_speed(); }

/** Drive in real units: mm/s forward and sideways, degrees/s of turn.
 *
 *  mpx_drive_at() takes -1..1, which is what a thumbstick produces and what
 *  the firmware's own joystick path expects. That is the right shape for
 *  teleoperation and the wrong shape for a movement you are choreographing,
 *  where "cross the mat at 60 mm/s" is the thing you actually know.
 *
 *  This sets the walk speed to the magnitude you asked for and drives at full
 *  deflection, so the number you pass is the number you get. It changes the
 *  walk speed as a side effect -- that setting is global and persists, which
 *  is why it is a separate call rather than the default.
 *
 *  Speeds above MPX_WALK_MAX_MM_S are clamped by the firmware.
 */
static inline int mpx_drive_mm_s(float fwd_mm_s, float strafe_mm_s, float turn_dps)
{
    float mag = mpx_abs(fwd_mm_s);
    if (mpx_abs(strafe_mm_s) > mag) mag = mpx_abs(strafe_mm_s);
    if (mag < 1.0f)
        return mpx_drive(0.0f, 0.0f, turn_dps / 90.0f);

    int rc = mpx_walk_speed_set((int)(mag + 0.5f));
    if (rc != MPX_OK) return rc;
    return mpx_drive(fwd_mm_s / mag, strafe_mm_s / mag, turn_dps / 90.0f);
}


/* ═══════════════════════════════════════════════════════════════════════════
 *  Body attitude — lean without stepping
 *
 *  The feet stay planted and the body moves over them. Firmware-clamped to
 *  roll +/-25, pitch +/-20, yaw +/-30 degrees, so you cannot ask for a lean
 *  that would tip it.
 *
 *  Set a glide speed first or poses snap instantly, which reads as a twitch.
 * ═══════════════════════════════════════════════════════════════════════════ */

static inline int mpx_body(float roll_deg, float pitch_deg, float yaw_deg)
{
    return robot_set_body_pose(roll_deg, pitch_deg, yaw_deg);
}

static inline int mpx_body_level(void) { return robot_set_body_pose(0, 0, 0); }
static inline int mpx_roll (float deg) { return robot_set_body_pose(deg, 0, 0); }
static inline int mpx_pitch(float deg) { return robot_set_body_pose(0, deg, 0); }
static inline int mpx_yaw  (float deg) { return robot_set_body_pose(0, 0, deg); }

/** Degrees per second for attitude changes. 0 = snap instantly. Persists. */
static inline int mpx_body_speed(int dps) { return robot_set_attitude_speed(dps); }

/** Per-axis glide speed, for when yaw should drift while roll stays crisp. */
static inline int mpx_body_speed_xyz(int roll_dps, int pitch_dps, int yaw_dps)
{
    return robot_set_attitude_speed_xyz(roll_dps, pitch_dps, yaw_dps);
}

/** Glide to an attitude at a given speed, and wait for it to arrive. */
static inline int mpx_body_to(float roll_deg, float pitch_deg, float yaw_deg,
                              int dps, int settle_ms)
{
    int rc = robot_set_attitude_speed(dps);
    if (rc != MPX_OK) return rc;
    rc = mpx_body(roll_deg, pitch_deg, yaw_deg);
    if (rc != MPX_OK) return rc;
    return mpx_sleep(settle_ms);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Gait shape
 *
 *  These change how the built-in gaits look. They persist across skills and
 *  are saved to the robot's flash, so a skill that changes them and does not
 *  put them back has changed the robot for whoever picks it up next.
 *  mpx_gait_config() then mpx_gait_config_set() on the way out is polite.
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct {
    int period_ms;   /**< Milliseconds per gait phase. Lower = quicker steps. */
    int height_mm;   /**< Body height while walking.                          */
    int lift_mm;     /**< How far each foot lifts on a step.                  */
    int stride_mm;   /**< How far each step reaches.                          */
    int tilt_deg;    /**< How much the body is allowed to tilt while walking. */
} mpx_gait_config_t;

static inline mpx_gait_config_t mpx_gait_config(void)
{
    mpx_gait_config_t c;
    c.period_ms = robot_get_period();
    c.height_mm = robot_get_height();
    c.lift_mm   = robot_get_up_height();
    c.stride_mm = robot_get_stride();
    c.tilt_deg  = robot_get_tilt();
    return c;
}

static inline int mpx_gait_config_set(mpx_gait_config_t c)
{
    return robot_set_config(c.period_ms, c.height_mm, c.lift_mm,
                            c.stride_mm, c.tilt_deg);
}

/** The firmware defaults, for putting things back the way you found them. */
static inline mpx_gait_config_t mpx_gait_config_default(void)
{
    mpx_gait_config_t c;
    c.period_ms = 80; c.height_mm = 70; c.lift_mm = 10;
    c.stride_mm = 10; c.tilt_deg  = 10;
    return c;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  IMU — which way is up
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef struct {
    float ax, ay, az;   /**< Acceleration, g.        */
    float gx, gy, gz;   /**< Angular rate, deg/s.    */
} mpx_imu_t;

/** Read all six axes. The struct is exactly the 24-byte layout the firmware
 *  writes, so this is one call with no copying. */
static inline int mpx_imu(mpx_imu_t *out)
{
    if (!out) return MPX_ERR_ARG;
    return robot_imu_read((int)out);
}

/** Body tilt from gravity, in degrees, derived from the accelerometer.
 *
 *  Only meaningful while the robot is roughly still. During a jump or a hard
 *  trot the accelerometer is measuring that motion, not the ground, and this
 *  will confidently report a lean that is not there. Gate it on the robot
 *  being settled, or fuse it with the gyro yourself. */
static inline int mpx_imu_tilt(float *roll_deg, float *pitch_deg)
{
    mpx_imu_t d;
    int rc = mpx_imu(&d);
    if (rc != MPX_OK) return rc;
    if (roll_deg)  *roll_deg  = mpx_deg(mpx_atan2(d.ay, d.az));
    if (pitch_deg) *pitch_deg = mpx_deg(mpx_atan2(-d.ax,
                                    mpx_sqrt(d.ay * d.ay + d.az * d.az)));
    return MPX_OK;
}

/** Print the current IMU reading to the robot's log. */
static inline int mpx_imu_log(void) { return robot_imu_print(); }

#ifdef __cplusplus
}
#endif
#endif /* MPX_ROBOT_H */
