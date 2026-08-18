/* ═══ ALL FOUR LAYERS, IN ONE ROUTINE ═════════════════════════════════════
 *
 * The first four examples each show one layer on its own. Real movements mix
 * them — and the interesting part is not the mixing, it is knowing when to
 * come back UP a layer.
 *
 * This performs a short greeting:
 *
 *   L1  walks in                     the firmware does the walking
 *   L2  bows                         we place the feet, it solves the legs
 *   L3  waves a paw                  we solve one leg ourselves
 *   L4  goes soft to be patted       only this layer can express that
 *   L1  walks off
 *
 * Then it stays behind as a BEHAVIOUR, keeping itself level, until stopped.
 *
 * Look at manifest.json too — four fields there change what this skill IS,
 * with no code at all:
 *
 *   provides_gait  it joins the movement list; the phone triggers "greet"
 *   behaviour      no 60-second watchdog; it runs until stopped
 *   on             the firmware starts it when the robot is picked up
 *   params         tunable at run time, no rebuild
 *
 *     mpx-cli deploy examples/06-together
 *     mpx-cli movements            # "greet" is now in the list
 *     mpx-cli trace                # watch it level itself
 *     mpx-cli stop                 # the only way a behaviour ends
 */
#include "mpx.h"

static float s_gain;

/* ── L2: a bow, as two keyframes ─────────────────────────────────────────
 * A timeline is the right shape for "a pose, over time". Writing this as a
 * for-loop of magic constants is the mistake mpx/motion.h exists to stop. */
static void bow(void)
{
    mpx_stance_key_t keys[] = {
        {    0, mpx_stance_stand(),              MPX_EASE_LINEAR },
        {  650, mpx_stance_front(22.0f, -52.0f), MPX_EASE_INOUT  },
        { 1500, mpx_stance_stand(),              MPX_EASE_OUT    },
    };
    mpx_stance_play(keys, 3, mpx_play(50, 1));
}

/* ── L3: wave the front-right paw ────────────────────────────────────────
 * The built-in IK cannot do this: it places FEET, and a waving paw is not a
 * foot on the floor. So we solve this one leg and leave the other three to
 * the firmware's standing pose. */
static void wave(void)
{
    mpx_take(MPX_OWN_JOINTS);
    for (int i = 0; i <= 70; ++i) {
        mpx_joint_to(MPX_FR_SHOULDER, 45.0f);
        mpx_joint_to(MPX_FR_KNEE,    -30.0f + 18.0f * mpx_sind((float)i * 18.0f));
        mpx_frame_send();
        mpx_sleep(20);
    }
    mpx_release();
}

/* ── L4: go compliant, so a hand can move the leg ────────────────────────
 * Nothing above this layer can say "be soft". Low Kp means the motor stops
 * insisting on its target, which is what makes a robot feel alive rather
 * than like a machine holding a pose. */
static void be_pattable(int ms)
{
    if (mpx_bus_take() != MPX_OK) return;
    mpx_gains_all(18.0f, 600.0f);          /* soft */
    mpx_sleep(ms);
    mpx_gains_stock();                     /* ALWAYS put them back */
    mpx_bus_release();
}

MPX_EXPORT void on_start(void)
{
    MPX_REQUIRE_ABI();

    s_gain = mpx_paramf("gain", 0.45f);
    const int walk_mm_s = mpx_parami("speed", 50);

    /* L1 — walk in. No maths, no risk. */
    mpx_walk_speed_set(walk_mm_s);
    mpx_drive_for(1.0f, 0.0f, 0.0f, 1800);

    bow();                                  /* L2 */
    wave();                                 /* L3 */
    be_pattable(2000);                      /* L4 */

    /* L1 again — come back UP as soon as the low layer has done its job.
     * Staying at layer 4 to walk would mean writing a gait. */
    mpx_drive_for(-1.0f, 0.0f, 0.0f, 1200);
    mpx_stand();

    /* Now stop being a script and start being a behaviour: 25 Hz, watching
     * its own attitude, until someone stops it. */
    mpx_tick_hz(25.0f);
}

/* Runs repeatedly AFTER on_start returns — never alongside it, so there is no
 * shared state to guard and no locking to write. */
MPX_EXPORT void on_tick(int dt_ms)
{
    (void)dt_ms;

    float roll, pitch;
    if (mpx_imu_tilt(&roll, &pitch) != MPX_OK) { mpx_tick_end(); return; }

    /* An OVERLAY adds to whatever is already driving the robot rather than
     * replacing it. Clamped to +/-20 by the firmware, so a trim cannot
     * become a fall. */
    mpx_overlay_lean(mpx_clamp(-roll  * s_gain, -8.0f, 8.0f));
    mpx_overlay_pitch(mpx_clamp(-pitch * s_gain, -8.0f, 8.0f));

    mpx_trace_f("roll", roll);
    mpx_trace_f("trim", -roll * s_gain);
}

/* A behaviour has no watchdog, so parking the robot is YOUR job. This runs
 * however it ends: stopped from the app, cancelled, or a trap. */
MPX_EXPORT void on_stop(int reason)
{
    (void)reason;
    mpx_overlay_clear();
    mpx_release();
    mpx_gains_stock();
    mpx_bus_release();
    mpx_stand();
}
