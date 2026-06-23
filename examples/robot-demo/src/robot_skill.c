/* robot_skill.c — MPX-Dog WASM Skill: Full Robot Demo (C)
 *
 * Demonstrates the Part 2 high-level abstractions:
 *   - robot_gait_enum() — type-safe gait control (no more string typos)
 *   - robot_gait_t enum (GAIT_ADVANCE, GAIT_TURN_L, etc.)
 *   - robot_set_config_ex() — config via struct
 *   - robot_walk_forward(), robot_turn_left(), robot_jump(),
 *     robot_stand() — one-liner actions
 *   - MPX_print_int() — integer debug printing
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
    robot_set_config_ex((robot_config_t){
        .period    = 100,
        .height    = 70,
        .up_height = 10,
        .stride    = 10,
        .tilt      = 10,
    });

    /* ── Step 3: Init pose (stand up) ──────────────────────── */
    log_msg("robot_skill: init pose\n");
    robot_stand();

    /* ── Step 4: Step in place ─────────────────────────────── */
    log_msg("robot_skill: stepping\n");
    robot_step_in_place(3000);

    /* ── Step 5: Walk forward ──────────────────────────────── */
    log_msg("robot_skill: advancing\n");
    robot_walk_forward(3000);

    /* ── Step 6: Turn left ─────────────────────────────────── */
    log_msg("robot_skill: turn left\n");
    robot_turn_left(2000);

    /* ── Step 7: Jump ──────────────────────────────────────── */
    log_msg("robot_skill: jump\n");
    robot_jump();

    /* ── Step 8: Return to neutral ─────────────────────────── */
    log_msg("robot_skill: stopping\n");
    robot_gait_enum(GAIT_NONE);
    robot_delay_ms(1000);

    log_msg("robot_skill: demo complete\n");
}
