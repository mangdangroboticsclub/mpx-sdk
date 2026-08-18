# Where things live in the firmware

The firmware repo is a sibling of this one: `../mangdang`.

```
main/
├── main.cc                      boot: NVS, Wi-Fi, robot, sandbox, HTTP
├── sdk/
│   ├── wasm_host_functions.h    ★ the ABI. NATIVE_SYMBOLS[] is the source of truth.
│   └── wasm_host_functions.cc     the implementations
├── wasm/
│   ├── wasm_sandbox.cc          load, instantiate, run, watchdog, on_stop,
│   │                            the per-run clock and parameter table
│   └── wasm_decrypt.cc          .mpxe encrypted skills
├── robot/
│   ├── robot.h / robot.cc       ★ the robot. Gait task, goal buffer, IK,
│   │                            joy_input, config, calibration, bus lock.
│   ├── stanford_gait.cc         the trot generator
│   ├── stanford_kinematics.cc   the leg solver behind mpx_foot()
│   ├── driver_board.c           SPI to the four AT32F413 boards
│   └── imu.cc
├── network/
│   ├── http_server.cc           the REST API, including /v1/skills/run
│   ├── chat_ws.cc               the voice/chat websocket
│   └── marketplace_proxy.cc
├── fs/littlefs_manager.cc       where uploaded skills are stored
└── lua/                         the Lua VM (a separate scripting path)
```

## The paths that matter to this SDK

**A skill runs** when `POST /v1/skills/run` lands in `http_server.cc`, which
installs any parameters and spawns a task calling
`wasm::load_and_run(path, "on_start", 60000)`.

**A host call** goes from the module, through WAMR's native symbol table, into
`sdk/wasm_host_functions.cc`, and usually straight into a `robot::` function.

**A joint moves** when something writes the goal buffer in `robot.cc` and the
gait task's 15 ms tick puts it on the SPI bus via `driver_board.c`.

## Things worth knowing before you change any of it

- **`robot.h` has the long comments.** The two raw position frames, why they
  are mirrored, why all-servos-centred is the standing pose, and what the NVS
  calibration means are all documented at the top of that file. Read them
  before touching anything angular.
- **The gait task does not flush while a skill is running.** It checks
  `wasm::is_running()`. Otherwise the idle gait would overwrite a skill's joint
  writes 66 times a second.
- **`servo_lock()` parks the gait**, and the sandbox force-releases it after a
  skill ends however it ended.
- **`Config` is persisted to NVS.** Gait shape and walk speed survive reboots,
  so a skill that changes them changes the robot.

## Building it

See [flashing.md](flashing.md).
