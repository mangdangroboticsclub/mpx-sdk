/* ═══ LAYER 4 — MOTORS ════════════════════════════════════════════════════
 *
 * You own the motor's control loop: the target angle AND the gains that
 * decide how hard it fights to get there.
 *
 * This is the bottom. Drop here when stiffness is part of the motion —
 * landing softly, going compliant so a leg can be pushed, holding a pose
 * against a load. Nothing above this layer can express any of that.
 *
 * THREE THINGS TO KNOW BEFORE YOU RUN IT:
 *
 *   1. Taking the bus PARKS THE GAIT. You cannot walk while you hold it.
 *   2. Gains PERSIST after you let go — the built-in gaits will use whatever
 *      you left behind. Put them back.
 *   3. Some parameters are calibration, not gains, and are refused.
 *
 *     mpx-cli deploy examples/04-motors
 */
#include "mpx.h"

MPX_EXPORT void on_start(void)
{
    MPX_REQUIRE_ABI();
    MPX_LOG("layer 4 — you own the motor");

    /* Servo Studio may hold the bus; a refusal is normal, not a failure. */
    if (mpx_bus_take() != MPX_OK) {
        MPX_LOG("could not take the bus — is Servo Studio open?");
        return;
    }

    /* ── A. Stiffness ────────────────────────────────────────────────────
     * Kp is how hard the motor pulls towards its target; Kd damps the
     * approach. Stock is Kp 65, Kd 800.
     *
     * There are FOUR tuned gains, in two loops, set by two paired calls:
     *
     *   mpx_gains_all  (kp, kd)            the POSITION loop — this one
     *   mpx_current_all(kp_cur, kff_cur)   the CURRENT loop  — section A2
     *
     * They are separate on purpose: one call taking all four would put 65 and
     * 0.0006 side by side as unlabelled arguments, and swapping them wrecks a
     * joint without any visible sign. mpx_gains_stock() puts all four back. */
    mpx_gains_all(65.0f, 800.0f);
    mpx_gain_set(MPX_FR_KNEE, MPX_PARAM_KP_POSITION, 95.0f);   /* one stiffer */

    float kp = 0.0f;
    if (mpx_gain_get(MPX_FR_KNEE, MPX_PARAM_KP_POSITION, &kp) == MPX_OK)
        mpx_log_f("FR knee Kp", kp);

    /* ── A2. The rest of the control loop ────────────────────────────────
     * Kp/Kd shape the POSITION loop — where the joint goes. Underneath it the
     * board runs a CURRENT loop, deciding how the motor makes the torque the
     * position loop asked for. Reach for these when a joint arrives in the
     * right place but arrives badly.
     *
     * READ THE SCALE BEFORE YOU TYPE A NUMBER HERE. The current loop is in
     * amps per count, not degrees. Stock is Kp 0.0006 and Kff 0.00022, and a
     * useful change is one step of 0.0001. The number 65 is correct for the
     * POSITION loop above and about 100,000x too large here — the joint sings,
     * gets hot, and you conclude the robot is broken. Scale from the stock
     * constants rather than typing an absolute value. */
    mpx_current_kp (MPX_FR_KNEE, MPX_KP_CURRENT_STOCK  * 1.5f);  /* 0.00090 */
    mpx_current_kff(MPX_FR_KNEE, MPX_KFF_CURRENT_STOCK * 1.2f);  /* 0.00026 */

    /* ...and the same two on all twelve, when you want the whole robot: */
    mpx_current_all(MPX_KP_CURRENT_STOCK, MPX_KFF_CURRENT_STOCK);

    /* Not a gain — a torque CEILING, which is why it is neither in
     * mpx_gains_all nor in mpx_current_all. Bundling it would mean every
     * stiffness change quietly reset a safety limit you set on purpose. */
    mpx_max_effort (MPX_FR_KNEE, 0.6f);    /* 0..1 */

    /* Calibration, not gains. These decide what every angle MEANS, and
     * mpx_gain_save() would burn a mistake into the driver board's flash
     * where a reboot will not clear it. Refused from a skill on purpose —
     * change them from Servo Studio, watching the joint move. */
    if (mpx_gain_set(MPX_FR_KNEE, MPX_PARAM_RANGE_POSITION_DEG, 300.0f)
            == MPX_ERR_READONLY)
        MPX_LOG("calibration params are read-only from a skill, as intended");

    /* The two REVERSE_* slots flip a direction. A skill that writes one leaves
     * a single joint driving opposite to the other eleven — a robot tearing at
     * its own legs, surviving the skill that caused it. The firmware refuses
     * them for that reason. */
    if (mpx_gain_set(MPX_FR_KNEE, MPX_PARAM_REVERSE_MOTOR, 1.0f) == MPX_ERR_READONLY)
        MPX_LOG("reverse_motor is refused too — it is a direction, not a gain");

    /* You never have to find out the hard way. Ask first: */
    for (int i = 0; i < MPX_PARAM_COUNT; ++i)
        if (MPX_PARAMS[i].read_only)
            mpx_log_s(MPX_PARAMS[i].name);      /* the five a skill cannot write */

    /* ── B. Driving joints directly ──────────────────────────────────────
     * Same discipline as one layer up: stage what you want, send once.
     * mpx_bus_stage() takes the same relative degrees as the rest of the
     * SDK. (mpx_bus_stage_abs() takes the driver board's own 0..270 frame —
     * it exists, but keeping one angle convention in your code is worth
     * more than matching the wire.) */
    for (int i = 0; i <= 60; ++i) {
        float deg = 12.0f * mpx_sind((float)i * 6.0f);

        mpx_bus_stage(MPX_FR_SHOULDER, deg,  400.0f, 0.0f, 0.0f);
        mpx_bus_stage(MPX_FR_KNEE,     0.0f, 400.0f, 0.0f, 0.0f);
        mpx_bus_send();                     /* one transaction for the frame */
        mpx_sleep(16);
    }

    /* ── C. Stiffness as part of the motion ──────────────────────────────
     * The thing only this layer can do: change how hard the joint fights,
     * mid-move. Per-frame kp/kd override the persistent gains — here the
     * knee goes soft as it arrives, so it settles instead of slamming. */
    for (int i = 0; i <= 40; ++i) {
        float t    = (float)i / 40.0f;
        float soft = 90.0f - 60.0f * t;     /* stiff -> compliant */

        mpx_bus_stage(MPX_FR_KNEE, -18.0f * t, 400.0f, soft, 900.0f);
        mpx_bus_send();
        mpx_trace_f("kp", soft);
        mpx_sleep(20);
    }

    /* ── D. Put it back ──────────────────────────────────────────────────
     * Gains outlive your skill. Leaving one joint at Kp 95 means every
     * built-in gait afterwards walks slightly wrong, and nothing on screen
     * explains why. */
    mpx_gains_stock();
    mpx_max_effort_all(1.0f);          /* give the joints their authority back */
    mpx_bus_release();

    mpx_stand();
    MPX_LOG("done");
}

MPX_EXPORT void on_stop(int reason)
{
    (void)reason;
    /* The firmware force-releases the bus when a skill ends, so a crash
     * cannot leave the gait parked. The GAINS are ours to restore. */
    mpx_gains_stock();
    mpx_bus_release();
    mpx_stand();
}
