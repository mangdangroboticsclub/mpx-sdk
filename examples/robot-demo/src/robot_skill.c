/* robot_skill.c — MPX-Dog WASM Skill: Full Robot Demo (C)
 *
 * Demonstrates all major host function categories:
 *   - Logging (MPX_print / MPX_LOG)
 *   - Servo bus check (robot_ping_servo)
 *   - Configuration (robot_set_config)
 *   - Gait sequence (init → step → advance → turnL → jump → none)
 *   - Delay (robot_delay_ms)
 *
 * Compile:
 *   mpx-cli build src/robot_skill.c -o build/robot_skill.wasm --validate
 *
 * Upload & run:
 *   mpx-cli upload build/robot_skill.wasm
 *   mpx-cli run robot_skill.wasm
 */

#include "mpx_host.h"

/* ── Helpers ───────────────────────────────────────────────── */
static void log_msg(const char *msg)
{
    MPX_print(msg, __builtin_strlen(msg));
}

/* ── Entry point ───────────────────────────────────────────── */
void on_start(void)
{
    log_msg("robot_skill: starting demo\n");

    /* ── Step 1: Verify servo bus ──────────────────────────── */
    int model = robot_ping_servo(1);
    if (model > 0) {
        log_msg("robot_skill: servo 1 OK\n");
    } else {
        log_msg("robot_skill: servo 1 NOT RESPONDING\n");
    }

    /* ── Step 2: Set conservative gait parameters ──────────── */
    robot_set_config(100,   /* period:  100 ms per phase */
                     70,    /* height:  70 mm body height */
                     10,    /* lift:    10 mm foot lift */
                     10,    /* stride:  10 mm step length */
                     10);   /* tilt:    10° max tilt */

    /* ── Step 3: Init pose (stand up) ──────────────────────── */
    log_msg("robot_skill: init pose\n");
    robot_gait((int)"init");
    robot_delay_ms(3000);

    /* ── Step 4: Step in place ─────────────────────────────── */
    log_msg("robot_skill: stepping\n");
    robot_gait((int)"step");
    robot_delay_ms(3000);

    /* ── Step 5: Walk forward ──────────────────────────────── */
    log_msg("robot_skill: advancing\n");
    robot_gait((int)"advance");
    robot_delay_ms(3000);

    /* ── Step 6: Turn left ─────────────────────────────────── */
    log_msg("robot_skill: turn left\n");
    robot_gait((int)"turnL");
    robot_delay_ms(2000);

    /* ── Step 7: Jump ──────────────────────────────────────── */
    log_msg("robot_skill: jump\n");
    robot_gait((int)"jump");
    robot_delay_ms(3000);

    /* ── Step 8: Return to neutral ─────────────────────────── */
    log_msg("robot_skill: stopping\n");
    robot_gait((int)"none");
    robot_delay_ms(1000);

    log_msg("robot_skill: demo complete\n");
}
