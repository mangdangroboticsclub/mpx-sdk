# Reference

Everything you look up rather than read. **Generated** from the firmware's own
tables and from the CLI itself, so it cannot drift from what the robot does.

* [When something goes wrong](#when-something-goes-wrong)
* [Error codes](#error-codes)
* [The manifest](#the-manifest)
* [Commands](#commands)
* [Built-in movements](#built-in-movements)
* [Host functions](#host-functions)

---

## When something goes wrong

```bash
mpx-cli doctor      # is the setup right?
mpx-cli logs -f     # what is the robot actually saying?
```

| Symptom | Almost always means |
|---|---|
| `no on_start export` | your entry point is not named `on_start`, or was not exported — use `MPX_EXPORT` |
| `load failed — not a valid .wasm` | the file is corrupt, or is not a module |
| `trapped during execution` | out-of-bounds access, or a divide by zero |
| `timed out (60 s)` | your loop does not finish — or you meant `"behaviour": true` |
| traps on the first host call | built against a different ABI. `mpx-cli doctor`, then rebuild |
| runs, but nothing moves | you forgot `mpx_frame_send()` |
| joints move the wrong way | you closed a loop on `mpx_joint_raw()` — use `mpx_joint_at()` |
| `a skill is already running` | one at a time. `mpx-cli stop` |
| the robot froze in a pose | a `holds` movement, doing what it says. Send `init` |
| a control loop diverges | same frame mistake as above, or a gain that is too high |
| autorun stopped happening | safe mode tripped. `mpx-cli safe-mode` |
| `MPX_ERR_READONLY` | that parameter is board calibration, not a gain |
| `MPX_ERR_BUSY` | another domain holds the joints — see `mpx_take()` |

If the SDK behaves differently from the documentation, treat the documentation
as the thing that is wrong, and please report it.

---

## Error codes

Every host function returns one of these, or a value `>= 0` where it is
documented to return data. `mpx_strerror(code)` turns any of them into text.

| Name | Value | Meaning |
|---|---|---|
| `MPX_OK` | `0` | Success. |
| `MPX_ERR_ARG` | `-1` | Bad argument: id, index or pointer. |
| `MPX_ERR_NOT_LOCKED` | `-2` | You do not hold the servo bus. |
| `MPX_ERR_NO_REPLY` | `-3` | The driver board did not answer. |
| `MPX_ERR_READONLY` | `-4` | Calibration parameter; read-only. |
| `MPX_ERR_CANCELLED` | `-5` | Your skill was stopped mid-call. |
| `MPX_ERR_STATE` | `-6` | Right call, wrong time. |
| `MPX_ERR_BUSY` | `-7` | Another control domain holds the joints. |

---

## The manifest

`manifest.json` is the one file the CLI and the robot both read. `mpx-cli build`
embeds the declarative fields into the `.wasm` itself, so they travel with the
artifact.

| Field | Type | What it does |
|---|---|---|
| `slug` | string | the identifier; the source file and the robot filename derive from it |
| `title` | string | shown in the marketplace |
| `version` | string | semver |
| `abi` | int | the ABI this was built for. `mpx-cli` refuses a mismatch before upload |
| `readme` | string | one-line description |
| `params` | array | tunable at run time; the web UI renders a control per entry |
| `provides_gait` | string | registers a movement name the phone can trigger |
| `behaviour` | bool | no 60-second watchdog; must be stopped |
| `on` | array | events that start it: `boot`, `imu.lifted`, `imu.fallen`, `imu.shaken`, `chat:<word>` |
| `autorun` | bool | start at power-on, subject to safe mode |

A parameter entry is `{"name","type","default"}` plus optional `min`, `max`
and `label`. `type` is `float` or `int`.

---

## Commands

### The loop you will actually run

```bash
mpx-cli init my_move      # scaffold a skill
cd my_move
mpx-cli deploy            # build + upload + run, in one
mpx-cli logs -f           # what the robot is saying
```

Run from inside a skill directory and every path is derived from
`manifest.json`, so you never retype the name.

| Command | What it does |
|---|---|
| [`mpx-cli init`](#mpx-cli-init) | Scaffold a new skill |
| [`mpx-cli build`](#mpx-cli-build) | Compile a C/WAT/TS source file to .wasm |
| [`mpx-cli upload`](#mpx-cli-upload) | Upload a .wasm skill to the robot |
| [`mpx-cli run`](#mpx-cli-run) | Execute a skill on the robot |
| [`mpx-cli deploy`](#mpx-cli-deploy) | Build, upload and run in one step (the usual dev loop) |
| [`mpx-cli list` (or `ls`)](#mpx-cli-list) | List skills installed on the robot |
| [`mpx-cli delete`](#mpx-cli-delete) | Delete a skill from the robot |
| [`mpx-cli logs`](#mpx-cli-logs) | Show the robot's log (use -f to follow) |
| [`mpx-cli install`](#mpx-cli-install) | Download a marketplace skill and put it on the robot |
| [`mpx-cli gaits`](#mpx-cli-gaits) | List the robot's built-in movements |
| [`mpx-cli doctor`](#mpx-cli-doctor) | Check that everything needed to build and deploy is present |
| [`mpx-cli trace`](#mpx-cli-trace) | Plot the named numbers a running skill emits |
| [`mpx-cli movements`](#mpx-cli-movements) | Every movement this robot can perform, built-in and skill-provided |
| [`mpx-cli stop`](#mpx-cli-stop) | Ask the running skill to stop (the only way to end a behaviour) |
| [`mpx-cli safe-mode`](#mpx-cli-safe-mode) | Show or clear autorun safe mode |
| [`mpx-cli sync`](#mpx-cli-sync) | Refresh this project's generated bindings from the SDK |
| [`mpx-cli signup`](#mpx-cli-signup) | Register a new marketplace account |
| [`mpx-cli login`](#mpx-cli-login) | Authenticate and store a session token |
| [`mpx-cli logout`](#mpx-cli-logout) | Clear stored session token |
| [`mpx-cli publish`](#mpx-cli-publish) | Publish a skill to the marketplace |
| [`mpx-cli search`](#mpx-cli-search) | Browse or search marketplace skills |
| [`mpx-cli info`](#mpx-cli-info) | Show detailed marketplace skill information |
| [`mpx-cli versions`](#mpx-cli-versions) | List all published versions of a skill |
| [`mpx-cli robot`](#mpx-cli-robot) | Show robot information and assigned skills |

### `mpx-cli init`

| Option | Meaning |
|---|---|
| `name` | Skill name, e.g. my_wave |
| `--lang`, `-l` | c (default, and the only one with the friendly API), ts (AssemblyScript) or wat (raw WebAssembly text) |
| `--dir`, `-d` | Where to put it (default: ./<name>) |

### `mpx-cli build`

| Option | Meaning |
|---|---|
| `source` | Source file (default: src/<slug>.<ext> from manifest.json) |
| `-o`, `--output` | Output .wasm path (default: build/<name>.wasm) |
| `--validate` | Run wasm-validate on the output |
| `--inspect` | Show imports/exports via wasm-objdump |
| `--show-toolchains` | List detected toolchains and exit |

### `mpx-cli upload`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `wasm` | Path to the .wasm file (default: build/<slug>.wasm from manifest.json) |

### `mpx-cli run`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `skill` | Skill filename (default: <slug>.wasm from manifest.json) |
| `--no-wait` | Return as soon as the skill starts, without waiting for its result |
| `--timeout` | Seconds to wait for a result (default: 70; the robot stops any skill at 60) |
| `--param` | Set a skill parameter for this run. Repeatable. The skill reads it with mpx_paramf()/mpx_parami(); anything it does not supply falls back to the skill's own default, so this is always optional. Declare parameters in manifest.json and the robot's web UI renders a control for each one. |

### `mpx-cli deploy`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `source` | Source file (default: src/<slug>.<ext> from manifest.json) |
| `-o`, `--output` | Output .wasm path (default: build/<slug>.wasm) |
| `--no-run` | Upload but do not execute the skill |
| `--validate` | Run wasm-validate on the built module |
| `--no-wait` | Return as soon as the skill starts, without waiting for its result |
| `--timeout` | Seconds to wait for a result (default: 70; the robot stops any skill at 60) |
| `--param` | Set a skill parameter for this run. Repeatable. The skill reads it with mpx_paramf()/mpx_parami(); anything it does not supply falls back to the skill's own default, so this is always optional. Declare parameters in manifest.json and the robot's web UI renders a control for each one. |

### `mpx-cli list`

Alias: `mpx-cli ls`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `--all`, `-a` | Show all files (not just .wasm skills) |

### `mpx-cli delete`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `skill` | Skill filename to delete (e.g. my_skill.wasm) |
| `--yes`, `-y` | Skip confirmation prompt |

### `mpx-cli logs`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `-f`, `--follow` | Keep polling and print new lines as they appear (Ctrl-C to stop) |
| `-n`, `--lines` | How many past lines to show first (default: 200) |

### `mpx-cli install`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `skill_id` | Marketplace skill id (see 'mpx-cli search') |
| `--version` | Specific version (default: latest) |
| `--url` | Download from this URL instead of asking the gateway |
| `--name` | Filename on the robot (default: derived from the skill id) |
| `--run` | Run it once installed |

### `mpx-cli gaits`

| Option | Meaning |
|---|---|
| `filter` | Only show gaits matching this text |
| `--names` | Just the C enum names, one per line (for scripting) |

### `mpx-cli doctor`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `--no-robot` | Skip the robot connectivity check |

### `mpx-cli trace`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `--signal`, `-s` | Only this signal; repeatable. Default: all of them. |
| `--csv` | Write CSV to stdout instead of drawing (for a real plot) |
| `--once` | Print what is buffered and exit, instead of following |
| `--interval` | Seconds between polls (default: 0.25) |

### `mpx-cli movements`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `--skills-only` | Only the ones skills provide |

### `mpx-cli stop`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |

### `mpx-cli safe-mode`

| Option | Meaning |
|---|---|
| `--ip`, `-i` | Robot IP address (default: 192.168.2.1, env: MPX_HOST) |
| `--port`, `-p` | Robot HTTP port (default: 80, env: MPX_PORT) |
| `--clear` | Re-enable autorun after it was disabled |

### `mpx-cli sync`

| Option | Meaning |
|---|---|
| `--check` | Report staleness without writing anything (exit 1 if stale) |

### `mpx-cli signup`

| Option | Meaning |
|---|---|
| `username` | Desired username |
| `--password`, `-p` | Password (prompted securely if omitted) |

### `mpx-cli login`

| Option | Meaning |
|---|---|
| `username` | Account username |
| `--password`, `-p` | Password (prompted securely if omitted) |

### `mpx-cli logout`

| Option | Meaning |
|---|---|
| `--yes`, `-y` | Skip confirmation |

### `mpx-cli publish`

| Option | Meaning |
|---|---|
| `dir` | Path to the skill directory (with manifest.json and build/) |
| `--force` | Skip slug lock check |

### `mpx-cli search`

| Option | Meaning |
|---|---|
| `query` | Optional search term |
| `--json` | Output raw JSON instead of a table |

### `mpx-cli info`

| Option | Meaning |
|---|---|
| `skill_id` | Skill ID (e.g. username~slug) |
| `--json` | Output raw JSON instead of formatted text |

### `mpx-cli versions`

| Option | Meaning |
|---|---|
| `skill_id` | Skill ID (e.g. username~slug) |
| `--json` | Output raw JSON instead of a table |

### `mpx-cli robot`

| Option | Meaning |
|---|---|
| `uuid` | Robot UUID |
| `--json` | Output raw JSON instead of formatted text |

## Settings

| Variable | Default | Meaning |
|---|---|---|
| `MPX_HOST` | `192.168.2.1` | Robot address |
| `MPX_PORT` | `80` | Robot port |
| `MPX_SDK_INCLUDE` | auto | Where the SDK headers are, if not found automatically |

Put the first two in a `.env` beside your project and stop typing `--ip`.


---

## Built-in movements

The **46** movements the firmware already knows how to perform.

GENERATED by `tools/gen_docs.py` from `sdk/include/mpx/gaits.h`, which is
itself generated from the firmware's `robot::GaitCmd` enum. Do not edit.

```c
mpx_gait(MPX_GAIT_FORWARD);            // start it, return immediately
mpx_gait_for(MPX_GAIT_TWERK, 2000);    // start, hold 2 s, stop
mpx_gait_once(MPX_GAIT_STRETCH);       // start, hold for TYPICAL, stop
mpx_gait_stop();                       // stop; the pose is held
```

Same list on the terminal, searchable: `mpx-cli gaits [text]`

## What ENDING means

This is the column people trip over.

| Ending | What happens when you stop asking |
|---|---|
| `holds` | Stays in its final pose. **It will still be there when your skill exits.** |
| `returns` | Comes back to standing on its own. |
| `cycles` | Repeats until you stop it. |

`TYPICAL` is a duration that suits the movement; `-` means it runs until
stopped. `mpx_gait_once()` uses it so you do not have to guess.

## The catalogue

| Name | Wire name | Ending | Typical | What it does |
|---|---|---|---:|---|
| `MPX_GAIT_NONE` | `none` | holds | — | Stop the gait generator; hold the current pose. |
| `MPX_GAIT_STAND` | `init` | holds | 800 ms | Return to the neutral standing pose. |
| `MPX_GAIT_STEP` | `step` | cycles | 1500 ms | March on the spot. |
| `MPX_GAIT_ROLL` | `roll` | cycles | 1500 ms | Roll the body side to side. |
| `MPX_GAIT_PITCH` | `pitch` | cycles | 1500 ms | Pitch the body nose-up and nose-down. |
| `MPX_GAIT_STRETCH` | `stretch` | returns | 2000 ms | Stretch the legs out, like waking up. |
| `MPX_GAIT_FORWARD` | `advance` | cycles | — | Walk forward. |
| `MPX_GAIT_BACK` | `back` | cycles | — | Walk backward. |
| `MPX_GAIT_STRAFE_LEFT` | `left` | cycles | — | Sidestep left without turning. |
| `MPX_GAIT_STRAFE_RIGHT` | `right` | cycles | — | Sidestep right without turning. |
| `MPX_GAIT_TURN_LEFT` | `turnL` | cycles | — | Spin left on the spot. |
| `MPX_GAIT_TURN_RIGHT` | `turnR` | cycles | — | Spin right on the spot. |
| `MPX_GAIT_TWERK` | `twerk` | cycles | 2000 ms | Rear-end shimmy. Crowd-pleaser. |
| `MPX_GAIT_JUMP` | `jump` | returns | 2000 ms | Jump straight up. |
| `MPX_GAIT_JUMP_FORWARD` | `jumpfwd` | returns | 2000 ms | Jump forward. |
| `MPX_GAIT_TEST_SPEED` | `testspeed` | cycles | 3000 ms | Diagnostic speed sweep. Not a display move. |
| `MPX_GAIT_LOOK_UP` | `lookup` | holds | 800 ms | Tilt the body to look up. |
| `MPX_GAIT_LOOK_DOWN` | `lookdown` | holds | 800 ms | Tilt the body to look down. |
| `MPX_GAIT_LOOK_LEFT` | `lookleft` | holds | 800 ms | Turn the body to look left. |
| `MPX_GAIT_LOOK_RIGHT` | `lookright` | holds | 800 ms | Turn the body to look right. |
| `MPX_GAIT_LOOK_UP_LEFT` | `lookul` | holds | 800 ms | Look up and to the left. |
| `MPX_GAIT_LOOK_UP_RIGHT` | `lookur` | holds | 800 ms | Look up and to the right. |
| `MPX_GAIT_LOOK_DOWN_LEFT` | `lookll` | holds | 800 ms | Look down and to the left. |
| `MPX_GAIT_LOOK_DOWN_RIGHT` | `looklr` | holds | 800 ms | Look down and to the right. |
| `MPX_GAIT_LIFT_FRONT_LEFT` | `flegL` | holds | 1200 ms | Raise the front-left paw. |
| `MPX_GAIT_LIFT_FRONT_RIGHT` | `flegR` | holds | 1200 ms | Raise the front-right paw. |
| `MPX_GAIT_LIFT_REAR_LEFT` | `blegL` | holds | 1200 ms | Raise the rear-left leg. |
| `MPX_GAIT_LIFT_REAR_RIGHT` | `blegR` | holds | 1200 ms | Raise the rear-right leg. |
| `MPX_GAIT_HEIGHT_UP` | `heightup` | holds | 600 ms | Stand taller. |
| `MPX_GAIT_HEIGHT_DOWN` | `heightdown` | holds | 600 ms | Crouch lower. |
| `MPX_GAIT_BALANCE` | `balance` | cycles | — | Hold level using the IMU. |
| `MPX_GAIT_BOW` | `bowback` | holds | 1200 ms | Bow: front down, rear up. |
| `MPX_GAIT_BODY_CYCLE` | `bodycycle` | cycles | 2500 ms | Circle the body over planted feet. |
| `MPX_GAIT_HEAD_ELLIPSE` | `headellipse` | cycles | 2500 ms | Trace an ellipse with the front of the body. |
| `MPX_GAIT_MOVE_FL` | `moveLF` | returns | 1500 ms | Sweep the front-left leg through an arc. |
| `MPX_GAIT_MOVE_FR` | `moveRF` | returns | 1500 ms | Sweep the front-right leg through an arc. |
| `MPX_GAIT_MOVE_RL` | `moveLB` | returns | 1500 ms | Sweep the rear-left leg through an arc. |
| `MPX_GAIT_MOVE_RR` | `moveRB` | returns | 1500 ms | Sweep the rear-right leg through an arc. |
| `MPX_GAIT_TROT` | `stanford` | cycles | — | Stanford trot - the smoothest walk. Speed is set by mpx_walk_speed_set(). |
| `MPX_GAIT_FRONT_KICK` | `frontkick` | returns | 2000 ms | Kick forward with a front leg, then recover. |
| `MPX_GAIT_WIGGLE` | `wiggle` | cycles | 2000 ms | Rear up and wiggle. |
| `MPX_GAIT_BUTT_SHRUG` | `buttshrug` | cycles | 2000 ms | Front up, rear shrug. |
| `MPX_GAIT_WIGGLE_LEFT` | `wiggleL` | cycles | 2000 ms | Wiggle, leaning left. |
| `MPX_GAIT_WIGGLE_RIGHT` | `wiggleR` | cycles | 2000 ms | Wiggle, leaning right. |
| `MPX_GAIT_BUTT_SHRUG_LEFT` | `buttshrugL` | cycles | 2000 ms | Butt shrug, leaning left. |
| `MPX_GAIT_BUTT_SHRUG_RIGHT` | `buttshrugR` | cycles | 2000 ms | Butt shrug, leaning right. |

> **Wire name** is what the firmware matches on. You should never need it —
> `mpx_gait()` takes the enum, so a typo is a compile error instead of a
> robot that quietly does nothing.


---

## Host functions

The raw imports, as the firmware registers them. The friendly wrappers in
`mpx/*.h` compile down to these with nothing added — read this to know what a
call really costs.

**ABI v4 · 70 functions**

**ABI**

| Function | Signature |
|---|---|
| `mpx_abi_version` | `()i` |

**Logging**

| Function | Signature |
|---|---|
| `print` | `($i)i` |

**Gaits**

| Function | Signature |
|---|---|
| `robot_gait` | `($)i` |

**Body**

| Function | Signature |
|---|---|
| `robot_set_body_pose` | `(fff)i` |

**Gait config**

| Function | Signature |
|---|---|
| `robot_set_config` | `(iiiii)i` |

**Feet**

| Function | Signature |
|---|---|
| `robot_ik_fr` | `(fff)i` |
| `robot_ik_fl` | `(fff)i` |
| `robot_ik_rr` | `(fff)i` |
| `robot_ik_rl` | `(fff)i` |

**Joints and sensing**

| Function | Signature |
|---|---|
| `robot_get_mode` | `()i` |
| `robot_set_attitude_speed` | `(i)i` |
| `robot_set_attitude_speed_xyz` | `(iii)i` |
| `robot_get_period` | `()i` |
| `robot_get_height` | `()i` |
| `robot_get_up_height` | `()i` |
| `robot_get_stride` | `()i` |
| `robot_get_tilt` | `()i` |
| `robot_set_servo_angle` | `(ii)i` |
| `robot_flush` | `()i` |
| `robot_set_servo_speed` | `(ii)i` |
| `robot_read_position` | `(i)i` |
| `robot_read_angle_cdeg` | `(i)i` |
| `robot_read_speed` | `(i)i` |
| `robot_read_load` | `(i)i` |
| `robot_read_voltage` | `(i)i` |
| `robot_read_temperature` | `(i)i` |
| `robot_read_moving` | `(i)i` |
| `robot_read_current` | `(i)i` |
| `robot_set_offset` | `(ii)i` |
| `robot_get_offset` | `(i)i` |
| `robot_ping_servo` | `(i)i` |
| `robot_delay_ms` | `(i)i` |
| `robot_imu_read` | `(i)i` |
| `robot_imu_print` | `()i` |

**Servo bus**

| Function | Signature |
|---|---|
| `servo_lock` | `()i` |
| `servo_unlock` | `()i` |
| `servo_is_locked` | `()i` |
| `servo_set_gain` | `(iif)i` |
| `servo_get_gain` | `(iii)i` |
| `servo_save_config` | `(i)i` |
| `servo_restore_config` | `(i)i` |
| `servo_stage` | `(iffff)i` |
| `servo_commit` | `()i` |
| `servo_write_all` | `(ii)i` |
| `servo_read` | `(ii)i` |
| `servo_read_all` | `(i)i` |
| `servo_poll` | `()i` |
| `servo_direct` | `(iiff)i` |
| `servo_scan` | `()i` |

**v3/v4 additions**

| Function | Signature |
|---|---|
| `mpx_control_take` | `(i)i` |
| `mpx_control_release` | `()i` |
| `mpx_control_owner` | `()i` |
| `mpx_millis` | `()i` |
| `mpx_sleep_until` | `(i)i` |
| `mpx_drive` | `(fff)i` |
| `mpx_drive_stop` | `()i` |
| `mpx_set_walk_speed` | `(i)i` |
| `mpx_get_walk_speed` | `()i` |
| `mpx_foot` | `(ifff)i` |
| `mpx_set_all_servo_speed` | `(i)i` |
| `mpx_reset_offsets` | `()i` |
| `mpx_read_temperature_c` | `(i)f` |
| `mpx_param_f` | `($f)f` |
| `mpx_param_i` | `($i)i` |
| `mpx_overlay` | `(if)i` |
| `mpx_overlay_get` | `(i)f` |
| `mpx_overlay_clear` | `()i` |
| `mpx_tick_every` | `(i)i` |
| `mpx_tick_stop` | `()i` |
| `mpx_trace` | `($f)i` |
