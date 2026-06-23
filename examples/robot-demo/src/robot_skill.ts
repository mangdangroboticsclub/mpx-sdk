// robot_skill.ts — MPX-Dog WASM Skill: Full Robot Demo (AssemblyScript)
//
// Demonstrates the Part 2 high-level abstractions:
//   - Gait enum (Gait.ADVANCE, Gait.TURN_L, etc.)
//   - robotGait() — type-safe gait control
//   - setRobotConfig() — config via RobotConfig object
//   - walkForward(), turnLeft(), jump(), stand() — one-liner actions
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
    print, robot_ping_servo, robot_delay_ms,
    Gait, robotGait, setRobotConfig, RobotConfig,
    walkForward, turnLeft, jump, stand, stepInPlace,
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
    setRobotConfig(new RobotConfig(100, 70, 10, 10, 10));

    // ── Step 3: Init pose (stand up) ────────────────────────
    log_msg("robot_skill: init pose\n");
    stand();

    // ── Step 4: Step in place ───────────────────────────────
    log_msg("robot_skill: stepping\n");
    stepInPlace(3000);

    // ── Step 5: Walk forward ────────────────────────────────
    log_msg("robot_skill: advancing\n");
    walkForward(3000);

    // ── Step 6: Turn left ───────────────────────────────────
    log_msg("robot_skill: turn left\n");
    turnLeft(2000);

    // ── Step 7: Jump ────────────────────────────────────────
    log_msg("robot_skill: jump\n");
    jump();

    // ── Step 8: Return to neutral ───────────────────────────
    log_msg("robot_skill: stopping\n");
    robotGait(Gait.NONE);
    robot_delay_ms(1000);

    log_msg("robot_skill: demo complete\n");
}
