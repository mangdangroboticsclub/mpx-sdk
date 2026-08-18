/* ═══ LAYER 1 — GAITS AND DRIVING ═════════════════════════════════════════
 *
 * You say what you want. The robot works out every joint angle, every frame,
 * for as long as it takes.
 *
 * This is the highest layer and the only one where a mistake in your maths
 * cannot put the robot on its side — because there is no maths. Start here,
 * and only drop a layer when you actually need something this cannot do.
 *
 *     mpx-cli deploy examples/01-gaits
 */
#include "mpx.h"

MPX_EXPORT void on_start(void)
{
    MPX_REQUIRE_ABI();          /* firmware ABI mismatch? say so, don't move */
    MPX_LOG("layer 1 — the robot moves itself");

    /* ── A. Naming a movement ────────────────────────────────────────────
     * 46 are built in. `mpx-cli gaits` lists them with descriptions.
     *
     * The KIND matters more than the name:
     *   CYCLES  repeats until stopped        — advance, twerk
     *   RETURNS performs once, stands again  — jump, frontkick
     *   HOLDS   stays in its final pose      — lookup, init
     */
    mpx_gait_for(MPX_GAIT_FORWARD, 2000);   /* a CYCLES gait, so give it a duration */
    mpx_gait_once(MPX_GAIT_JUMP);           /* a RETURNS gait knows its own length  */

    mpx_gait(MPX_GAIT_LOOK_UP);             /* a HOLDS gait keeps holding... */
    mpx_sleep(1000);
    mpx_stand();                            /* ...until you say otherwise    */

    /* ── B. Steering instead of naming ───────────────────────────────────
     * Named gaits are discrete. For "forward at 40 mm/s while turning
     * gently" the robot takes a velocity — the same path the phone's
     * joystick uses.
     */
    mpx_walk_speed_set(40);                 /* mm/s that 1.0 means. Max 200. */
    mpx_drive_for(1.0f, 0.0f, 0.25f, 2500); /* fwd, strafe, turn — all -1..1 */

    /* Or in real units, if that is what you know: */
    mpx_drive_mm_s(60.0f, 0.0f, 15.0f);     /* mm/s, mm/s, deg/s */
    mpx_sleep(1500);
    mpx_stop();

    /* ── C. Leaning, without stepping ────────────────────────────────────
     * The feet stay planted and the body moves over them. Firmware-clamped
     * to roll +/-25, pitch +/-20, yaw +/-30 — you cannot ask it to tip over.
     */
    mpx_body_speed(60);                     /* deg/s, so it glides not snaps */
    mpx_body(0.0f, 12.0f, 0.0f);            /* roll, pitch, yaw */
    mpx_sleep(900);
    mpx_body(0.0f, 0.0f, 0.0f);
    mpx_sleep(900);

    mpx_stand();
    MPX_LOG("done");
}

/* Optional. Runs however the skill ends — returned, trapped, or stopped.
 * A HOLDS gait is still holding when you exit, so leave the robot somewhere
 * you would be happy to find it. */
MPX_EXPORT void on_stop(int reason)
{
    (void)reason;
    mpx_gait_stop();
}
