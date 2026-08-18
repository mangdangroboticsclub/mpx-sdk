/* ═══ LAYER 2 — FEET ══════════════════════════════════════════════════════
 *
 * You say where a foot should be. The firmware solves the leg.
 *
 * Drop to this layer when you want poses the built-in gaits do not have, but
 * you do not want to own the trigonometry. It is the same inverse kinematics
 * the gait generator uses, so your poses sit in the same frame as the
 * built-in movements and inherit the same calibration.
 *
 *     mpx-cli deploy examples/02-feet
 */
#include "mpx.h"

/* Coordinates, for one leg, relative to ITS OWN hip:
 *
 *        +x forward          x   mm, forward positive
 *          ↑                 splay  degrees, sideways swing at the hip
 *          │                 z   mm, UP positive — so a foot on the floor
 *     hip ─┼──→ +y left          is NEGATIVE. About -70 is standing.
 *          │
 *          ↓ foot at z ≈ -70
 */

MPX_EXPORT void on_start(void)
{
    MPX_REQUIRE_ABI();
    MPX_LOG("layer 2 — you place the feet");

    const float STAND = MPX_STAND_Z_MM;     /* -70, from the firmware's own model */

    /* ── A. One pose ─────────────────────────────────────────────────────
     * All four feet in the same place relative to their own hips. */
    mpx_feet_to(0.0f, 0.0f, STAND);
    mpx_sleep(600);

    /* ── B. Crouch and rise ──────────────────────────────────────────────
     * Less negative z is a crouch: the foot is closer to the hip. */
    for (int i = 0; i <= 40; ++i) {
        float z = STAND + 18.0f * mpx_sind((float)i * 4.5f);   /* 0..180 deg */
        mpx_feet_to(0.0f, 0.0f, z);
        mpx_sleep(25);
    }

    /* ── C. Body sway, feet planted ──────────────────────────────────────
     * Moving all four feet backwards together moves the BODY forwards.
     * The robot rides over its feet without stepping. */
    for (int i = 0; i < 90; ++i) {
        float sway = 18.0f * mpx_sind((float)i * 4.0f);
        mpx_feet_to(sway, 0.0f, STAND);
        mpx_sleep(20);
    }

    /* ── D. One leg at a time ────────────────────────────────────────────
     * Plant three, lift the fourth. Lift a leg the robot is standing on and
     * it will fall over — that is the responsibility this layer hands you. */
    mpx_feet_to(0.0f, 0.0f, STAND);
    mpx_sleep(400);

    for (int i = 0; i <= 60; ++i) {
        float t     = (float)i / 60.0f;
        float lift  = 25.0f * mpx_sind(t * 180.0f);     /* up and back down  */
        float reach = 20.0f * mpx_sind(t * 360.0f);     /* forward and back  */
        mpx_foot_to(MPX_FR, reach, 0.0f, STAND + lift);
        mpx_sleep(20);
    }

    mpx_feet_stand();
    MPX_LOG("done");
}

MPX_EXPORT void on_stop(int reason) { (void)reason; mpx_stand(); }
