/* mpx/leg.h — feet and joints: the layer where you shape the motion yourself.
 *
 * Two ways to move a leg, and the difference matters:
 *
 *   mpx_foot_to(leg, x, splay, z)   You say where the FOOT goes; the firmware
 *                                   works out the three joint angles. Uses the
 *                                   same kinematics and the same calibration
 *                                   as the built-in gaits, so your poses sit
 *                                   in the same frame as theirs.
 *
 *   mpx_joint_to(joint, degrees)    You say what the JOINT does. Total
 *                                   freedom, and total responsibility for the
 *                                   trigonometry.
 *
 * Prefer feet. Reach for joints when you are writing your own kinematics or
 * doing something the leg model does not describe.
 *
 * ── ANGLES ─────────────────────────────────────────────────────────────────
 * Everything in this file is DEGREES, RELATIVE TO CENTRE, range +/-135.
 * Zero means centred, and the robot is calibrated so that all twelve joints
 * centred is exactly the standing pose. Positive and negative are symmetric
 * about that.
 *
 * mpx/bus.h speaks a different frame — absolute 0..270 with 135 at centre —
 * because that is what the driver boards use. Everything there is named
 * _abs_ so you cannot mix the two by accident. If you need to convert,
 * MPX_ABS_FROM_REL / MPX_REL_FROM_ABS in that file do it.
 *
 * ── FRAMES ─────────────────────────────────────────────────────────────────
 * Writes are buffered. Nothing moves until the frame is sent:
 *
 *     mpx_foot_to(MPX_FL, 0, 0, -78);
 *     mpx_foot_to(MPX_FR, 0, 0, -78);
 *     mpx_frame_send();                 <- one send, after all the writes
 *
 * One send per frame, not one per joint. Sending per joint puts each servo on
 * the bus in its own transaction and the legs arrive at different times, which
 * is exactly what a judder is.
 *
 * mpx_ticker_wait() (mpx/sys.h) sends for you, so in a timed loop
 * mpx_frame_send() does not appear at all.
 */
#ifndef MPX_LEG_H
#define MPX_LEG_H

#include "mpx/abi.h"
#include "mpx/geometry.h"
#include "mpx/sys.h"
#include "mpx/math.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ═══════════════════════════════════════════════════════════════════════════
 *  Naming
 * ═══════════════════════════════════════════════════════════════════════════ */

typedef enum {
    MPX_FR = 0,   /**< Front right. */
    MPX_FL = 1,   /**< Front left.  */
    MPX_RR = 2,   /**< Rear right.  */
    MPX_RL = 3,   /**< Rear left.   */
} mpx_leg_t;

/** The three joints in a leg, hip outwards. */
typedef enum {
    MPX_HIP      = 0,   /**< Rotates the leg sideways (abduction).   */
    MPX_SHOULDER = 1,   /**< Swings the leg fore and aft.            */
    MPX_KNEE     = 2,   /**< Bends the leg.                          */
} mpx_part_t;

/** The twelve joints. Values are the firmware's servo ids, 1-12. */
typedef enum {
    MPX_FR_HIP = 1,  MPX_FR_SHOULDER = 2,  MPX_FR_KNEE = 3,
    MPX_FL_HIP = 4,  MPX_FL_SHOULDER = 5,  MPX_FL_KNEE = 6,
    MPX_RR_HIP = 7,  MPX_RR_SHOULDER = 8,  MPX_RR_KNEE = 9,
    MPX_RL_HIP = 10, MPX_RL_SHOULDER = 11, MPX_RL_KNEE = 12,
} mpx_joint_t;

/** The joint at `part` on `leg` — so a leg can be a loop variable. */
static inline mpx_joint_t mpx_joint(mpx_leg_t leg, mpx_part_t part)
{
    return (mpx_joint_t)((int)leg * 3 + (int)part + 1);
}

/* Link lengths, joint limits and hip positions live in mpx/geometry.h, which
 * is generated from the firmware's own kinematics headers. Do not redefine
 * them here: this file used to carry MPX_CALF_MM 56.0f while the firmware
 * said 60.0f, and a 4 mm error in a link length is invisible until the foot
 * lands somewhere you did not ask for. */

/* ═══════════════════════════════════════════════════════════════════════════
 *  Feet — you place, the firmware solves
 *
 *      x      mm, forward positive, back negative
 *      splay  degrees, sideways swing at the hip
 *      z      mm, measured DOWN from the hip, so it is negative.
 *             About -78 is standing; less negative is a crouch.
 * ═══════════════════════════════════════════════════════════════════════════ */

static inline int mpx_foot_to(mpx_leg_t leg, float x_mm, float splay_deg, float z_mm)
{
    return mpx_foot((int)leg, x_mm, splay_deg, z_mm);
}

/** Put all four feet in the same place relative to their own hips. */
static inline int mpx_feet_to(float x_mm, float splay_deg, float z_mm)
{
    int rc, worst = MPX_OK;
    for (int l = 0; l < 4; ++l) {
        rc = mpx_foot((int)l, x_mm, splay_deg, z_mm);
        if (rc != MPX_OK) worst = rc;
    }
    return worst;
}

/** The neutral four-feet-planted stance. */
static inline int mpx_feet_stand(void)
{
    return mpx_feet_to(0.0f, 0.0f, MPX_STAND_Z_MM);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Joints — you solve, the firmware passes it on
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Set one joint, in degrees relative to centre. Clamped to the joint limit
 *  rather than refused: a pose that overshoots by a degree because of an
 *  easing curve should sit at the limit, not abandon the frame. */
static inline int mpx_joint_to(mpx_joint_t j, float deg)
{
    deg = mpx_clamp(deg, -MPX_JOINT_LIMIT_DEG, MPX_JOINT_LIMIT_DEG);
    return robot_set_servo_angle((int)j, (int)(deg * 100.0f));
}

/** Read one joint back, in degrees relative to centre.
 *
 *  This is the reading that matches mpx_joint_to(). To close a loop, use this
 *  one — and only this one. mpx_joint_raw() below is in the opposite frame,
 *  and an error term computed across the two has the wrong sign, so the loop
 *  drives away from the target instead of towards it. */
static inline float mpx_joint_at(mpx_joint_t j)
{
    return (float)robot_read_angle_cdeg((int)j) * 0.01f;
}

/** Raw driver-board position, 0..1023, in the ABSOLUTE frame. For diagnostics
 *  and for talking to Servo Studio. Not for closing a loop — see above. */
static inline int mpx_joint_raw(mpx_joint_t j) { return robot_read_position((int)j); }

/** How fast a joint travels to its target. 0 = as fast as it can. */
static inline int mpx_joint_speed(mpx_joint_t j, int speed)
{
    return robot_set_servo_speed((int)j, speed);
}

/** Travel speed for every joint at once. */
static inline int mpx_joints_speed(int speed) { return mpx_set_all_servo_speed(speed); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Sending a frame
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Send every buffered write. One per frame. */
static inline int mpx_frame_send(void) { return robot_flush(); }

/** Send this frame and hold the rate. Returns MPX_ERR_CANCELLED if the skill
 *  was stopped, which is your cue to leave the loop. */
static inline int mpx_ticker_wait(mpx_ticker_t *t)
{
    int rc = mpx_frame_send();
    if (rc != MPX_OK) return rc;
    t->frame++;
    return mpx_sleep_to(t->start_ms + t->frame * t->period_ms);
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Telemetry
 *
 *  Every read is a round trip to a driver board — roughly a millisecond. Do
 *  not put twelve of them inside a 60 Hz loop; sample one joint per frame, or
 *  read between moves.
 * ═══════════════════════════════════════════════════════════════════════════ */

static inline int   mpx_joint_load    (mpx_joint_t j) { return robot_read_load((int)j); }
static inline int   mpx_joint_current (mpx_joint_t j) { return robot_read_current((int)j); }
static inline int   mpx_joint_moving  (mpx_joint_t j) { return robot_read_moving((int)j); }
static inline float mpx_joint_temp_c  (mpx_joint_t j) { return mpx_read_temperature_c((int)j); }
static inline float mpx_battery_v     (void)          { return (float)robot_read_voltage(1) * 0.1f; }

/** Model number if the joint answers, <= 0 if it does not. A quick way to
 *  find a servo that has come unplugged. */
static inline int mpx_joint_ping(mpx_joint_t j) { return robot_ping_servo((int)j); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Calibration
 *
 *  An offset shifts what "centred" means for one joint. It is persistent and
 *  it changes what every later angle command means — including the built-in
 *  gaits'. Change these deliberately, with the robot in front of you, and
 *  prefer the robot's Servo Studio page where you can watch the joint move.
 * ═══════════════════════════════════════════════════════════════════════════ */

static inline float mpx_offset(mpx_joint_t j)
{
    return (float)robot_get_offset((int)j) * 0.01f;
}

static inline int mpx_offset_set(mpx_joint_t j, float deg)
{
    return robot_set_offset((int)j, (int)(deg * 100.0f));
}

/** Clear every calibration offset. Recalibration follows. */
static inline int mpx_offsets_reset(void) { return mpx_reset_offsets(); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Two-link inverse kinematics, in your module
 *
 *  The firmware's IK is better in almost every case — it inherits the
 *  calibration and matches the built-in gaits. This is here for when you are
 *  learning what IK does, or building on top of it.
 *
 *  Returns MPX_OK, or MPX_ERR_ARG if the target was out of reach, in which
 *  case the angles returned are for the closest reachable point rather than
 *  garbage.
 * ═══════════════════════════════════════════════════════════════════════════ */

static inline int mpx_ik2(float x_mm, float z_mm,
                          float *shoulder_deg, float *knee_deg)
{
    float d2, d, knee, sh, s;
    int   reachable = 1;

    d2 = x_mm * x_mm + z_mm * z_mm;
    d  = mpx_sqrt(d2);

    if (d > MPX_REACH_MM - 1.0f) {          /* pull the target into reach */
        reachable = 0;
        s = (MPX_REACH_MM - 1.0f) / (d > 0.0f ? d : 1.0f);
        x_mm *= s; z_mm *= s;
        d2 = x_mm * x_mm + z_mm * z_mm;
        d  = mpx_sqrt(d2);
    }

    knee = mpx_acos((d2 - MPX_THIGH_MM * MPX_THIGH_MM - MPX_CALF_MM * MPX_CALF_MM)
                    / (2.0f * MPX_THIGH_MM * MPX_CALF_MM));
    sh   = mpx_atan2(x_mm, -z_mm)
         + mpx_acos((d2 + MPX_THIGH_MM * MPX_THIGH_MM - MPX_CALF_MM * MPX_CALF_MM)
                    / (2.0f * MPX_THIGH_MM * (d > 0.0f ? d : 1.0f)));

    if (shoulder_deg) *shoulder_deg = mpx_deg(sh)   - 45.0f;
    if (knee_deg)     *knee_deg     = mpx_deg(knee) - 90.0f;
    return reachable ? MPX_OK : MPX_ERR_ARG;
}

#ifdef __cplusplus
}
#endif
#endif /* MPX_LEG_H */
