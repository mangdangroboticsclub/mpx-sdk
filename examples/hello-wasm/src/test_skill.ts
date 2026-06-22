// test_skill.ts — Minimal MPX-Dog WASM Skill (AssemblyScript)
//
// Compile:
//   mpx-cli build src/test_skill.ts -o build/test_skill.wasm
//
// Upload & run:
//   mpx-cli upload build/test_skill.wasm
//   mpx-cli run test_skill.wasm

import { print } from "../include/mpx_env";

// ── Entry point ────────────────────────────────────────────────
export function on_start(): void {
    const msg = "Hello from AssemblyScript on ESP32-S3!";
    const encoded = String.UTF8.encode(msg);
    print(changetype<usize>(encoded), encoded.byteLength as i32);
}
