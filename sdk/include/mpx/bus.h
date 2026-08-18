/* mpx/bus.h — owning the motor, not just the joint.
 *
 * The deepest layer. Here you set not only where a joint should be but how
 * hard it tries to get there: the proportional and derivative gains of the
 * servo's own control loop, and the current it is allowed to draw. This is
 * what people mean by "Unitree-style" joint control, and it is how you get a
 * leg that is compliant on landing, or stiff enough to hold a load.
 *
 * ── TAKING THE BUS PARKS THE GAIT ──────────────────────────────────────────
 * While you hold the bus, the gait generator does not run. You cannot walk and
 * tune at the same time. The usual shape is:
 *
 *     mpx_bus_take();
 *     ... set gains ...
 *     mpx_bus_release();
 *     mpx_gait(MPX_GAIT_FORWARD);        // now the gait uses your gains
 *
 * Gains persist on the driver board after you release, which is the point:
 * the built-in gaits pick them up too.
 *
 * ── THIS FILE SPEAKS A DIFFERENT ANGLE FRAME ───────────────────────────────
 * The driver boards use ABSOLUTE degrees, 0..270, with 135 at centre. The rest
 * of the SDK uses relative degrees, +/-135 with 0 at centre. Every function
 * here says _abs_ in its name so the two cannot be confused, and the macros
 * below convert.
 *
 *     absolute = 135 + relative
 *
 * ── THE ROBOT WILL LET YOU BREAK IT ────────────────────────────────────────
 * A high Kp with no current cap can stall a servo against its own limit and
 * cook it. Start from the stock values (Kp 65, Kd 800), change one joint at a
 * time, and keep a current cap on. The robot's Servo Studio page has a live
 * scope for exactly this and is a better place to find your numbers than a
 * skill is.
 */
#ifndef MPX_BUS_H
#define MPX_BUS_H

#include "mpx/abi.h"
#include "mpx/params.h"
#include "mpx/sys.h"
#include "mpx/leg.h"
#include "mpx/math.h"

#ifdef __cplusplus
extern "C" {
#endif

/** Centre of the absolute frame, in absolute degrees. */
#define MPX_ABS_CENTRE_DEG 135.0f

/** Relative (+/-135, 0 = centre)  ->  absolute (0..270, 135 = centre). */
#define MPX_ABS_FROM_REL(d) ((float)(d) + MPX_ABS_CENTRE_DEG)
/** Absolute -> relative. */
#define MPX_REL_FROM_ABS(d) ((float)(d) - MPX_ABS_CENTRE_DEG)

/* ═══════════════════════════════════════════════════════════════════════════
 *  Ownership
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Take the bus. MPX_ERR_STATE if something else holds it — usually the
 *  robot's Servo Studio page being open in a browser somewhere. */
static inline int mpx_bus_take(void)    { return servo_lock(); }

/** Give the bus back. The gait generator resumes. The sandbox does this for
 *  you if your skill ends while still holding it, so a crash cannot leave the
 *  robot parked until someone reboots it. */
static inline int mpx_bus_release(void) { return servo_unlock(); }

/** Non-zero if the bus is currently held by anyone. */
static inline int mpx_bus_held(void)    { return servo_is_locked(); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Gains
 *
 *  Written through the driver board's config path, which is slow — tens of
 *  milliseconds each. Set them once, outside your motion loop.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* The parameter slots themselves are in mpx/params.h, generated from the
 * driver board's own table. They were hand-written here once and were wrong:
 * slot 4 is reverse_motor, not KP_POSITION, so setting "stiffness" reversed
 * a joint instead. Never retype a wire protocol. */

/* The four tuned gains this robot ships with. The two loops are in different
 * units and four orders of magnitude apart, which is exactly the trap: 65 is a
 * sane position gain and a catastrophic current gain. Restore from these
 * constants rather than from a number you remember. */
#define MPX_KP_STOCK           65.0f      /* position P                       */
#define MPX_KD_STOCK          800.0f      /* position D                       */
#define MPX_KP_CURRENT_STOCK    0.0006f   /* current P — note the scale       */
#define MPX_KFF_CURRENT_STOCK   0.00022f  /* current feed-forward             */

static inline int mpx_gain_set(mpx_joint_t j, mpx_param_t p, float v)
{
    return servo_set_gain((int)j, (int)p, v);
}

static inline int mpx_gain_get(mpx_joint_t j, mpx_param_t p, float *out)
{
    return servo_get_gain((int)j, (int)p, out);
}

/** The same POSITION-loop gains on every joint. First error, or MPX_OK.
 *
 *  Sets Kp and Kd only. Its partner is mpx_current_all() one section down;
 *  together they cover all four tuned gains, and mpx_gains_stock() puts all
 *  four back.
 *
 *  WHY THE TWO LOOPS ARE NOT ONE CALL. It is tempting to make this take all
 *  five numbers and be done. Then a call site reads
 *
 *      mpx_gains_all(65.0f, 800.0f, 0.0006f, 0.00022f, 1.0f);
 *
 *  — five unlabelled floats spanning five orders of magnitude, where swapping
 *  two of them is both catastrophic and invisible. That is not hypothetical:
 *  this SDK shipped mpx_current_kp(..., 40.0f), a position-loop number in a
 *  current-loop slot, roughly 66,000x too high. Splitting by loop keeps every
 *  argument list to numbers of the same magnitude, so a mistake is a mistake
 *  between neighbours rather than between 65 and 0.0006.
 *
 *  Max PWM duty is deliberately in neither: it is a torque CEILING, not a
 *  tuned gain. Bundling it here would mean every stiffness change silently
 *  reset a safety limit someone set on purpose. It has mpx_max_effort_all(). */
static inline int mpx_gains_all(float kp, float kd)
{
    for (int id = 1; id <= 12; ++id) {
        int rc = servo_set_gain(id, (int)MPX_PARAM_KP_POSITION, kp);
        if (rc != MPX_OK) return rc;
        rc = servo_set_gain(id, (int)MPX_PARAM_KD_POSITION, kd);
        if (rc != MPX_OK) return rc;
    }
    return MPX_OK;
}

/** Put every joint back to the factory control gains — all FOUR of them, both
 *  loops. It restored only Kp/Kd once, which meant a skill that touched the
 *  current loop and then "put things back" left the robot mistuned in a way
 *  no amount of reading its own source explained. Defined below the current-
 *  loop helpers it depends on. */
static inline int mpx_gains_stock(void);

/* ── The rest of the servo's control loop ─────────────────────────────────
 *
 * Kp and Kd shape the POSITION loop: where the joint goes. Underneath it the
 * board runs a CURRENT loop, deciding how the motor produces the torque the
 * position loop asked for. These are the knobs for when a joint arrives in
 * the right place but arrives badly.
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Gain of the inner current loop. **Stock is 0.0006.**
 *
 *  How sharply the motor delivers the torque the position loop asked for.
 *  Raise it and the joint feels crisper; too far and it buzzes or sings,
 *  because the loop is now fast enough to chase its own noise.
 *
 *  MIND THE SCALE. This is not Kp position. The current loop works in amps
 *  per count, so its useful range is thousandths — 0.0004 to 0.002, moved in
 *  steps of 0.0001. A value that looks reasonable next to Kp 65 is four
 *  orders of magnitude too large and will make the joint scream. Use
 *  MPX_KP_CURRENT_STOCK as your reference point, not the position gains. */
static inline int mpx_current_kp(mpx_joint_t j, float v)
{
    return mpx_gain_set(j, MPX_PARAM_KP_CURRENT, v);
}

/** Feed-forward current. **Stock is 0.00022.** Torque applied straight from
 *  the position error, without waiting for the loop to wind up.
 *
 *  This is the one for a joint that SAGS under a constant load, which on a
 *  quadruped means the robot's own weight. A pure Kp loop has to be off
 *  target to produce force, so it settles slightly low; feed-forward supplies
 *  that standing torque up front and the droop goes away.
 *
 *  Same scale as mpx_current_kp: ten-thousandths, stepped by 0.00001. */
static inline int mpx_current_kff(mpx_joint_t j, float v)
{
    return mpx_gain_set(j, MPX_PARAM_KFF_CURRENT, v);
}

/** The same CURRENT-loop gains on every joint — the partner to
 *  mpx_gains_all(). First error, or MPX_OK.
 *
 *  Between the two you can set all four tuned gains on all twelve joints, and
 *  neither call ever contains a number from the other loop. Stock is
 *
 *      mpx_current_all(MPX_KP_CURRENT_STOCK, MPX_KFF_CURRENT_STOCK);
 *
 *  and scaling from those constants is safer than typing absolute values,
 *  because nothing about 0.0009 looks wrong next to 65. */
static inline int mpx_current_all(float kp_current, float kff_current)
{
    for (int id = 1; id <= 12; ++id) {
        int rc = servo_set_gain(id, (int)MPX_PARAM_KP_CURRENT, kp_current);
        if (rc != MPX_OK) return rc;
        rc = servo_set_gain(id, (int)MPX_PARAM_KFF_CURRENT, kff_current);
        if (rc != MPX_OK) return rc;
    }
    return MPX_OK;
}

/** Ceiling on drive effort, 0..1 — your torque limit.
 *
 *  Lower it and the joint becomes physically unable to push hard, which is
 *  what you want while testing a new movement near furniture, or on a leg you
 *  do not yet trust. 1.0 is full authority. */
static inline int mpx_max_effort(mpx_joint_t j, float duty_0_to_1)
{
    return mpx_gain_set(j, MPX_PARAM_MAX_PWM_DUTY_CYCLE,
                        mpx_clamp(duty_0_to_1, 0.0f, 1.0f));
}

/** The same ceiling on all twelve joints. */
static inline int mpx_max_effort_all(float duty_0_to_1)
{
    int worst = MPX_OK;
    for (int id = 1; id <= 12; ++id) {
        int rc = mpx_max_effort((mpx_joint_t)id, duty_0_to_1);
        if (rc != MPX_OK) worst = rc;
    }
    return worst;
}

/* Declared above, next to mpx_gains_all(), where you go looking for it.
 * Deliberately both loops: restoring only half is worse than restoring none,
 * because it looks like you cleaned up. */
static inline int mpx_gains_stock(void)
{
    int worst = mpx_gains_all(MPX_KP_STOCK, MPX_KD_STOCK);
    int rc = mpx_current_all(MPX_KP_CURRENT_STOCK, MPX_KFF_CURRENT_STOCK);
    if (rc != MPX_OK) worst = rc;
    return worst;
}

/** Persist this joint's current gains to the driver board's flash. Survives a
 *  reboot — which is exactly why you should be sure first. */
static inline int mpx_gain_save(mpx_joint_t j)    { return servo_save_config((int)j); }
/** Reload the joint's gains from its flash, discarding run-time changes. */
static inline int mpx_gain_restore(mpx_joint_t j) { return servo_restore_config((int)j); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Commands — the fast path
 *
 *  Stage the joints you want to move, then send once. Same discipline as
 *  mpx_frame_send() one layer up, and for the same reason: one bus
 *  transaction per frame rather than one per joint.
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Queue one joint.
 *
 *  @param abs_deg  ABSOLUTE degrees, 0..270, 135 = centre.
 *  @param tau_ma   Current cap for this move, mA. 0 uses the board's own.
 *  @param kp,kd    Per-frame gain override. 0,0 uses the gains already set,
 *                  which is what you want unless you are modulating stiffness
 *                  within a motion — landing softly, for instance.
 */
static inline int mpx_bus_stage_abs(mpx_joint_t j, float abs_deg, float tau_ma,
                                    float kp, float kd)
{
    return servo_stage((int)j, abs_deg, tau_ma, kp, kd);
}

/** As mpx_bus_stage_abs(), taking the relative degrees the rest of the SDK
 *  uses. Prefer this one; it keeps a single angle convention in your code. */
static inline int mpx_bus_stage(mpx_joint_t j, float deg, float tau_ma,
                                float kp, float kd)
{
    return servo_stage((int)j, MPX_ABS_FROM_REL(deg), tau_ma, kp, kd);
}

/** Send every staged joint in one bus transaction. */
static inline int mpx_bus_send(void) { return servo_commit(); }

/** Bypass the stage/send buffer for one joint. mode: 0 idle, 1 position,
 *  2 torque. Idle makes a joint go limp, which is how you check a leg by hand
 *  without fighting it. */
static inline int mpx_bus_direct_abs(mpx_joint_t j, int mode, float abs_deg, float tau_ma)
{
    return servo_direct((int)j, mode, abs_deg, tau_ma);
}

/** Let every joint go limp. Note that the robot will sit down. */
static inline int mpx_bus_relax_all(void)
{
    for (int id = 1; id <= 12; ++id) {
        int rc = servo_direct(id, 0, 0.0f, 0.0f);
        if (rc != MPX_OK) return rc;
    }
    return MPX_OK;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  State
 * ═══════════════════════════════════════════════════════════════════════════ */

/** One joint's measured state. Angles are ABSOLUTE degrees. */
typedef struct {
    float q_deg;     /**< Measured position, absolute degrees. */
    float dq_dps;    /**< Measured speed, degrees per second.  */
    float tau_ma;    /**< Measured current, mA.                */
    float temp_c;    /**< Winding temperature, Celsius.        */
} mpx_bus_state_t;

/** Refresh the firmware's cached state for all joints. One bus sweep. */
static inline int mpx_bus_poll(void) { return servo_poll(); }

static inline int mpx_bus_read(mpx_joint_t j, mpx_bus_state_t *out)
{
    if (!out) return MPX_ERR_ARG;
    return servo_read((int)j, out);
}

/** Read all twelve into an array of twelve, index 0 = joint 1. */
static inline int mpx_bus_read_all(mpx_bus_state_t out[12])
{
    if (!out) return MPX_ERR_ARG;
    return servo_read_all(out);
}

/** Bitmask of joints that answered: bit 0 is joint 1. 0xFFF means all twelve.
 *  The quickest way to find a servo that is not talking. */
static inline int mpx_bus_scan(void) { return servo_scan(); }

#ifdef __cplusplus
}
#endif
#endif /* MPX_BUS_H */
