/* mpx/live.h — running inside the control loop, and composing with it.
 *
 * The rest of the SDK treats a skill as a script: on_start() runs, plays a
 * movement, and returns. That covers choreography and nothing else. Three
 * things here change what a skill can be.
 *
 *   TICKING     export on_tick() and your code runs repeatedly, at a rate you
 *               choose, after on_start() returns. Reactive behaviour --
 *               balancing, reacting to load, following something -- becomes a
 *               skill instead of a firmware patch.
 *
 *   OVERLAY     a small per-joint offset added to whatever is already driving
 *               the robot. The built-in walk keeps walking; you add a limp, a
 *               lean, a tail wiggle, a correction.
 *
 *   TRACE       named numbers out of a running skill, plotted by
 *               `mpx-cli trace`. Because a control loop you cannot see is a
 *               control loop you will end up debugging in firmware.
 *
 * Together they are the difference between a robot that performs tricks and
 * one that behaves.
 */
#ifndef MPX_LIVE_H
#define MPX_LIVE_H

#include "mpx/abi.h"
#include "mpx/leg.h"
#include "mpx/math.h"
#include "mpx/sys.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ═══════════════════════════════════════════════════════════════════════════
 *  Ticking — your code, in the loop
 *
 *      MPX_EXPORT void on_start(void) {
 *          mpx_tick_every(20);           // ask for 50 Hz
 *      }
 *
 *      MPX_EXPORT void on_tick(int dt_ms) {
 *          float roll, pitch;
 *          mpx_imu_tilt(&roll, &pitch);
 *          mpx_overlay_lean(-roll * 0.4f);
 *      }
 *
 *  on_start() returns immediately; on_tick() then runs every 20 ms until you
 *  call mpx_tick_stop(), it traps, or the run's time budget expires.
 *
 *  THINGS WORTH KNOWING:
 *
 *  - Ticking happens AFTER on_start returns. It is not concurrent with it, so
 *    there is no shared-state problem to solve and no locking to write.
 *
 *  - A tick is not phase-locked to a gait frame. It is paced on its own thread
 *    so that slow maker code can never stall the real-time loop that keeps the
 *    robot standing. Overlays are applied whenever the robot next sends a
 *    frame, so this does not matter for trimming and stabilising -- which is
 *    what this is for.
 *
 *  - Overrun three ticks in a row and the loop stops, with the reason in
 *    `mpx-cli logs`. Asking for 10 ms and taking 15 is not a rate; being told
 *    is better than silently running late forever.
 *
 *  - Ticks share the run's 60-second budget. A tick loop is not yet a way to
 *    run forever.
 * ═══════════════════════════════════════════════════════════════════════════ */

/* mpx_tick_every(int period_ms) and mpx_tick_stop(void) come straight from
 * mpx/abi.h -- their raw signatures are already the ones you want, so there is
 * nothing to wrap. */

/** Convenience: ask for a rate in Hz instead of a period. */
static inline int mpx_tick_hz(float hz)
{
    if (hz <= 0.0f) return mpx_tick_stop();
    return mpx_tick_every((int)(1000.0f / hz + 0.5f));
}

/** Stop ticking. The skill then ends normally, through on_stop(). */
static inline int mpx_tick_end(void) { return mpx_tick_stop(); }

/* ═══════════════════════════════════════════════════════════════════════════
 *  Overlay — add to what is already happening
 *
 *  An overlay is a per-joint offset in degrees, added to the frame on its way
 *  to the servos. It does not take ownership of anything: the gait generator,
 *  the IK, or your own joint writes carry on exactly as before, and the
 *  overlay rides on top.
 *
 *      mpx_gait(MPX_GAIT_FORWARD);        // the firmware keeps walking
 *      mpx_overlay_lean(6.0f);            // ...leaning into the turn
 *
 *  Clamped to +/-MPX_OVERLAY_MAX_DEG per joint by the firmware. That bound is
 *  what makes it safe to apply on top of a running gait: an overlay is a
 *  garnish, and a skill that wants real authority over a joint should take it
 *  properly with mpx_take(MPX_JOINTS).
 *
 *  Cleared automatically when your skill ends, however it ends.
 * ═══════════════════════════════════════════════════════════════════════════ */

/** The firmware's clamp. Asking for more is silently limited, not an error. */
#define MPX_OVERLAY_MAX_DEG  20.0f

/** Offset one joint, in degrees. */
static inline int mpx_overlay_at(mpx_joint_t j, float deg)
{
    return mpx_overlay((int)j, deg);
}

/** Read one joint's overlay back. */
static inline float mpx_overlay_of(mpx_joint_t j)
{
    return mpx_overlay_get((int)j);
}

/** Offset all three joints of one leg. */
static inline int mpx_overlay_leg(mpx_leg_t leg, float hip, float shoulder, float knee)
{
    int worst = MPX_OK, rc;
    rc = mpx_overlay((int)mpx_joint(leg, MPX_HIP),      hip);      if (rc) worst = rc;
    rc = mpx_overlay((int)mpx_joint(leg, MPX_SHOULDER), shoulder); if (rc) worst = rc;
    rc = mpx_overlay((int)mpx_joint(leg, MPX_KNEE),     knee);     if (rc) worst = rc;
    return worst;
}

/** Lean left (+) or right (-) by trimming the hips, without touching the gait.
 *  The two sides are trimmed in opposite directions, which is what makes it a
 *  lean rather than a sideways shuffle. */
static inline int mpx_overlay_lean(float deg)
{
    int worst = MPX_OK, rc;
    rc = mpx_overlay(MPX_FL_HIP,  deg); if (rc) worst = rc;
    rc = mpx_overlay(MPX_RL_HIP,  deg); if (rc) worst = rc;
    rc = mpx_overlay(MPX_FR_HIP, -deg); if (rc) worst = rc;
    rc = mpx_overlay(MPX_RR_HIP, -deg); if (rc) worst = rc;
    return worst;
}

/** Pitch nose-up (+) or nose-down (-) by trimming front and rear shoulders. */
static inline int mpx_overlay_pitch(float deg)
{
    int worst = MPX_OK, rc;
    rc = mpx_overlay(MPX_FL_SHOULDER,  deg); if (rc) worst = rc;
    rc = mpx_overlay(MPX_FR_SHOULDER,  deg); if (rc) worst = rc;
    rc = mpx_overlay(MPX_RL_SHOULDER, -deg); if (rc) worst = rc;
    rc = mpx_overlay(MPX_RR_SHOULDER, -deg); if (rc) worst = rc;
    return worst;
}

/* ═══════════════════════════════════════════════════════════════════════════
 *  Trace — see what your loop is doing
 *
 *      mpx_trace_f("roll", roll_deg);
 *      mpx_trace_f("cmd",  correction);
 *
 *      $ mpx-cli trace              # live, in the terminal
 *
 *  Names are limited to 15 characters and to letters, digits, `_`, `.` and
 *  `-`; anything else is replaced. Samples are timestamped with mpx_now().
 *
 *  The robot holds the last 256 samples. That is deliberately a "what just
 *  happened" window and not a recording facility -- at 50 Hz tracing two
 *  signals it is about two and a half seconds. Trace the one or two numbers
 *  that answer your question, not everything.
 * ═══════════════════════════════════════════════════════════════════════════ */

/** Record a named number from inside a running skill. */
static inline int mpx_trace_f(const char *name, float value)
{
    return mpx_trace(name, value);
}

/** Record a named integer. */
static inline int mpx_trace_i(const char *name, int value)
{
    return mpx_trace(name, (float)value);
}

#ifdef __cplusplus
}
#endif

#endif /* MPX_LIVE_H */
