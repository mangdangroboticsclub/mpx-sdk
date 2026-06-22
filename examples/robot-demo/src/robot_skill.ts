// robot_skill.ts — MPX-Dog WASM Skill: Full Robot Demo (AssemblyScript)
//
// Compile:
//   mpx-cli build src/robot_skill.ts -o build/robot_skill.wasm --validate
//
// Upload & run:
//   mpx-cli upload build/robot_skill.wasm
//   mpx-cli run robot_skill.wasm
//
// Sequence: init -> step -> advance -> turnL -> jump -> none

import {
    print, robot_gait, robot_delay_ms,
    robot_set_config, robot_ping_servo,
} from "../include/mpx_env";

// ── Helpers ─────────────────────────────────────────────────────
function log_msg(msg: string): void {
    const encoded = String.UTF8.encode(msg);
    print(changetype<usize>(encoded), encoded.byteLength as i32);
}

// ── Entry point ────────────────────────────────────────────────
export function on_start(): void {
    log_msg("robot_skill: starting demo\n");

    // ── Step 1: Verify servo bus ────────────────────────────
    const model = robot_ping_servo(1);
    if (model > 0) {
        log_msg("robot_skill: servo 1 OK\n");
    } else {
        log_msg("robot_skill: servo 1 NOT RESPONDING\n");
    }

    // ── Step 2: Set conservative gait parameters ────────────
    robot_set_config(100, 70, 10, 10, 10);

    // ── Step 3: Init pose ───────────────────────────────────
    log_msg("robot_skill: init pose\n");
    const init = String.UTF8.encode("init");
    robot_gait(changetype<usize>(init));
    robot_delay_ms(3000);

    // ── Step 4: Step in place ───────────────────────────────
    log_msg("robot_skill: stepping\n");
    const step = String.UTF8.encode("step");
    robot_gait(changetype<usize>(step));
    robot_delay_ms(3000);

    // ── Step 5: Walk forward ────────────────────────────────
    log_msg("robot_skill: advancing\n");
    const advance = String.UTF8.encode("advance");
    robot_gait(changetype<usize>(advance));
    robot_delay_ms(3000);

    // ── Step 6: Turn left ───────────────────────────────────
    log_msg("robot_skill: turn left\n");
    const turnL = String.UTF8.encode("turnL");
    robot_gait(changetype<usize>(turnL));
    robot_delay_ms(2000);

    // ── Step 7: Jump ────────────────────────────────────────
    log_msg("robot_skill: jump\n");
    const jump = String.UTF8.encode("jump");
    robot_gait(changetype<usize>(jump));
    robot_delay_ms(3000);

    // ── Step 8: Return to neutral ───────────────────────────
    log_msg("robot_skill: stopping\n");
    const none = String.UTF8.encode("none");
    robot_gait(changetype<usize>(none));
    robot_delay_ms(1000);

    log_msg("robot_skill: demo complete\n");
}
