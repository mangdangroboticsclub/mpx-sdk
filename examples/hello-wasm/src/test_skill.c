/* test_skill.c — Minimal MPX-Dog WASM Skill (C)
 *
 * Compile:
 *   mpx-cli build src/test_skill.c -o build/test_skill.wasm
 *
 * Upload & run:
 *   mpx-cli upload build/test_skill.wasm
 *   mpx-cli run test_skill.wasm
 */

#include "mpx_host.h"
#include <string.h>

/* Exported entry point — called by the sandbox as "on_start". */
void on_start(void)
{
    const char *msg = "Hello from C/WASI on ESP32-S3!";
    MPX_print(msg, strlen(msg));
}
