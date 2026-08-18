/* ═══ SENSING — READING THE ROBOT, AND MOVING BECAUSE OF IT ═══════════════
 *
 * The four layers are all about OUTPUT: gaits, feet, joints, motors. This is
 * the other axis. Sensing is what turns a routine that plays into a robot
 * that responds, and it works with every layer.
 *
 * Two sources:
 *
 *   THE IMU        how the body is oriented and how fast it is turning.
 *                  Six axes: three accelerometer, three gyro.
 *
 *   THE SERVOS     every joint reports its real angle, its load, its
 *                  current and its temperature. The robot can feel itself.
 *
 *     mpx-cli deploy examples/05-sensing
 *     mpx-cli trace                       # watch it in another terminal
 *
 * TILT THE ROBOT and it stays level. PUSH A FRONT LEG and it yields.
 */
#include "mpx.h"

MPX_EXPORT void on_start(void)
{
    MPX_REQUIRE_ABI();
    MPX_LOG("sensing — the robot can feel itself");

    mpx_stand();
    mpx_sleep(600);

    /* ── A. What is there ────────────────────────────────────────────────
     * A tour of everything readable, once, so you can see it in the log. */
    mpx_imu_t imu;
    if (mpx_imu(&imu) == MPX_OK) {
        mpx_log_f("accel z (g)", imu.az);   /* ~1.0 standing, ~0 in free fall */
        mpx_log_f("gyro z (dps)", imu.gz);
    }
    mpx_log_f("battery (V)",  mpx_battery_v());
    mpx_log_f("FR knee (deg)", mpx_joint_at(MPX_FR_KNEE));
    mpx_log_f("FR knee (C)",   mpx_joint_temp_c(MPX_FR_KNEE));
    mpx_log_i("FR knee load",  mpx_joint_load(MPX_FR_KNEE));

    /* ── B. Stay level  —  IMU in, movement out ──────────────────────────
     * mpx_imu_tilt() turns the raw accelerometer into the two numbers you
     * actually want: roll and pitch in degrees.
     *
     * Counter-rotating the BODY (layer 1) keeps the feet planted, so this is
     * safe on a slope. Tilt the robot by hand and watch it compensate. */
    MPX_LOG("B — tilt me; I will stay level");
    mpx_body_speed(120);                       /* deg/s, so it glides */

    for (int i = 0; i < 250; ++i) {            /* ~5 s at 20 ms */
        float roll, pitch;
        if (mpx_imu_tilt(&roll, &pitch) != MPX_OK) break;

        /* Command the OPPOSITE of the measured tilt, clamped well inside the
         * firmware's own limits. A gain of 1.0 would be exact levelling; less
         * is calmer, and calmer is almost always what you want. */
        mpx_body(mpx_clamp(-roll  * 0.8f, -20.0f, 20.0f),
                 mpx_clamp(-pitch * 0.8f, -15.0f, 15.0f),
                 0.0f);

        mpx_trace_f("roll", roll);
        mpx_trace_f("pitch", pitch);
        mpx_sleep(20);
    }
    mpx_body(0.0f, 0.0f, 0.0f);
    mpx_sleep(500);

    /* ── C. Feel a push  —  joint load in, movement out ──────────────────
     * Load is what the servo is fighting against. Push a leg and the load
     * on that joint rises. Yielding to it is the difference between a robot
     * that feels alive and one that feels like a machine.
     *
     * Load is noisy and unsigned; treat it as "something is happening", not
     * as a measurement. */
    MPX_LOG("C — push my front-right leg");
    mpx_take(MPX_OWN_JOINTS);

    float yield = 0.0f;
    for (int i = 0; i < 200; ++i) {
        int load = mpx_joint_load(MPX_FR_SHOULDER);

        /* Above the resting noise floor, give way; otherwise spring back. */
        if (load > 120) yield += 1.5f;
        else            yield *= 0.90f;
        yield = mpx_clamp(yield, 0.0f, 25.0f);

        mpx_joint_to(MPX_FR_SHOULDER, yield);
        mpx_frame_send();

        mpx_trace_i("load",  load);
        mpx_trace_f("yield", yield);
        mpx_sleep(25);
    }
    mpx_release();
    mpx_stand();

    /* ── D. Closing a loop, correctly ────────────────────────────────────
     * The gotcha worth remembering: mpx_joint_at() reads back in the SAME
     * frame mpx_joint_to() writes. The raw reading underneath runs the
     * OPPOSITE way, so a loop built on mpx_joint_raw() makes the error term
     * the wrong sign and diverges instead of converging — silently, fast. */
    MPX_LOG("D — closing a loop on measured angle");
    mpx_take(MPX_OWN_JOINTS);

    const float target = -20.0f;
    for (int i = 0; i < 30; ++i) {
        float error = target - mpx_joint_at(MPX_FR_KNEE);
        mpx_joint_to(MPX_FR_KNEE, target + error * 0.25f);
        mpx_frame_send();
        mpx_trace_f("error", error);
        mpx_sleep(40);
    }
    mpx_release();

    mpx_stand();
    MPX_LOG("done");
}

MPX_EXPORT void on_stop(int reason)
{
    (void)reason;
    mpx_release();
    mpx_body(0.0f, 0.0f, 0.0f);
    mpx_stand();
}
