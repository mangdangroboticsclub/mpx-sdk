# MPX-Dog Host Functions Reference

All host functions are registered under the **`"env"`** module by the ESP32 firmware.
They are callable from within any WASM skill (C/C++, AssemblyScript, or raw WAT).

---

## Part 1 — Raw Imports

These are the low-level host functions. Each table shows the function name, its
WAMR signature (the type string the firmware uses to register it), and a description.

### SDK / Logging

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `print(ptr, len)` | `($i)` | Print a string to the robot's ESP log. `ptr` is a native pointer to the text, `len` is the byte length. |

### High-Level Gait Control

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `robot_gait(name)` | `($)` | Start a named gait (see [Gait names](#gait-names) below). |
| `robot_get_mode()` | `()i` | Returns the current gait mode as an integer (maps to [`GaitCmd`](#gait-enum) enum). |

#### Gait names

| Name | Description |
|------|-------------|
| `"none"` | Stop all gait |
| `"init"` | Return to init/stand pose |
| `"step"` | Step in place |
| `"roll"` | Roll body |
| `"pitch"` | Pitch body |
| `"stretch"` | Stretch legs |
| `"advance"` | Walk forward |
| `"back"` | Walk backward |
| `"left"` | Sidestep left |
| `"right"` | Sidestep right |
| `"turnL"` | Turn left |
| `"turnR"` | Turn right |
| `"twerk"` | Twerk! |
| `"jump"` | Jump |
| `"jumpfwd"` | Jump forward |
| `"testspeed"` | Speed test |
| `"lookup"` | Look up (gait-based) |
| `"lookdown"` | Look down (gait-based) |
| `"lookleft"` | Look left (gait-based) |
| `"lookright"` | Look right (gait-based) |
| `"lookul"` | Look upper-left |
| `"lookur"` | Look upper-right |
| `"lookll"` | Look lower-left |
| `"looklr"` | Look lower-right |
| `"flegL"` | Foreleg lift left |
| `"flegR"` | Foreleg lift right |
| `"blegL"` | Backleg lift left |
| `"blegR"` | Backleg lift right |
| `"heightup"` | Height up |
| `"heightdown"` | Height down |
| `"balance"` | Balance body |
| `"bowback"` | Bow backward |
| `"bodycycle"` | Cycle body motion |
| `"headellipse"` | Head ellipse motion |
| `"moveLF"` | Move left front leg |
| `"moveRF"` | Move right front leg |
| `"moveLB"` | Move left back leg |
| `"moveRB"` | Move right back leg |

### Configuration

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `robot_set_config(period, height, up_height, stride, tilt)` | `(iiiii)` | Set all gait parameters at once. |
| `robot_get_period()` | `()i` | Get gait period in milliseconds. |
| `robot_get_height()` | `()i` | Get body height in millimetres. |
| `robot_get_up_height()` | `()i` | Get foot lift height in millimetres. |
| `robot_get_stride()` | `()i` | Get stride length in millimetres. |
| `robot_get_tilt()` | `()i` | Get max tilt angle in degrees. |

**Parameter reference:**

| Param | Range / Typical | Description |
|-------|-----------------|-------------|
| `period` | 60–200 ms | Gait period per phase |
| `height` | 50–100 mm | Body height from ground |
| `up_height` | 5–20 mm | How high the foot lifts during swing |
| `stride` | 5–30 mm | Step length |
| `tilt` | 0–20° | Maximum body tilt during gait |

### Low-Level Servo Control

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `robot_set_servo_angle(id, centideg)` | `(ii)` | Set a servo's target angle. `id` is 1–12, `centideg` is angle × 100 (e.g. 4500 = 45.00°). |
| `robot_flush()` | `()` | Send all buffered servo commands to the bus. |
| `robot_set_servo_speed(id, speed)` | `(ii)` | Set servo movement speed. `0` = max speed, higher = slower. |
| `robot_read_position(id)` | `(i)i` | Read raw position (0–1023). Returns -1 on error. |
| `robot_read_speed(id)` | `(i)i` | Read signed speed. Returns -1 on error. |
| `robot_read_load(id)` | `(i)i` | Read signed load. Returns -1 on error. |
| `robot_read_voltage(id)` | `(i)i` | Read voltage (0.1 V units). Returns -1 on error. |
| `robot_read_temperature(id)` | `(i)i` | Read temperature (°C). Returns -1 on error. |
| `robot_read_moving(id)` | `(i)i` | Read moving status: 0 = stopped, 1 = moving. Returns -1 on error. |
| `robot_read_current(id)` | `(i)i` | Read signed current (mA). Returns -1 on error. |

#### Servo ID map

| ID | Leg | Joint |
|----|-----|-------|
| 1 | Front Right | Hip |
| 2 | Front Right | Shoulder |
| 3 | Front Right | Knee |
| 4 | Front Left | Hip |
| 5 | Front Left | Shoulder |
| 6 | Front Left | Knee |
| 7 | Rear Right | Hip |
| 8 | Rear Right | Shoulder |
| 9 | Rear Right | Knee |
| 10 | Rear Left | Hip |
| 11 | Rear Left | Shoulder |
| 12 | Rear Left | Knee |

### Calibration

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `robot_set_offset(id, centideg)` | `(ii)` | Set angular offset for a servo (centidegrees, e.g. 150 = 1.50°). |
| `robot_get_offset(id)` | `(i)i` | Get angular offset in centidegrees. |
| `robot_ping_servo(id)` | `(i)i` | Ping a servo. Returns model number (>0) on success, ≤0 on failure. |

### Utility

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `robot_delay_ms(ms)` | `(i)` | Block the WASM thread for a real-time delay. **This is the only reliable way to pause** — pure-WASM busy-loops run at near-zero wall time inside the interpreter. |

### Inverse Kinematics (per-leg)

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `robot_ik_fr(x, th0, z)` | `(fff)` | Front-right leg IK target. |
| `robot_ik_fl(x, th0, z)` | `(fff)` | Front-left leg IK target. |
| `robot_ik_rr(x, th0, z)` | `(fff)` | Rear-right leg IK target. |
| `robot_ik_rl(x, th0, z)` | `(fff)` | Rear-left leg IK target. |

All IK functions take three `float` parameters:

| Param | Unit | Description |
|-------|------|-------------|
| `x` | mm | Forward/backward position |
| `th0` | degrees | Hip rotation angle |
| `z` | mm | Height |

### IMU

| Function | WAMR Sig | Description |
|----------|----------|-------------|
| `robot_imu_read(buffer_ptr)` | `(i)` | Read the latest IMU 6-DOF sample into a buffer (must be ≥ 24 bytes). Layout: `[ax, ay, az, gx, gy, gz]` as `float`. |
| `robot_imu_print()` | `()` | Print the latest IMU data to the robot's ESP log. |

**IMU data layout** (6 floats = 24 bytes):

| Index | Field | Unit | Description |
|-------|-------|------|-------------|
| 0 | `ax` | g | Accelerometer X |
| 1 | `ay` | g | Accelerometer Y |
| 2 | `az` | g | Accelerometer Z |
| 3 | `gx` | dps | Gyroscope X |
| 4 | `gy` | dps | Gyroscope Y |
| 5 | `gz` | dps | Gyroscope Z |

---

## Part 2 — High-Level Abstractions

These are convenience wrappers provided by the SDK headers
([`mpx_host.h`](mpx-cli/src/mpx_cli/commands/resource/mpx_host.h) for C,
[`mpx_env.ts`](mpx-cli/src/mpx_cli/commands/resource/mpx_env.ts) for AssemblyScript).
They compile down to the raw host functions above — no firmware changes needed.

### Gait Enum

A type-safe enum replaces raw string names:

| Enum | Value | String |
|------|-------|--------|
| `GAIT_NONE` / `Gait.NONE` | 0 | `"none"` |
| `GAIT_INIT` / `Gait.INIT` | 1 | `"init"` |
| `GAIT_STEP` / `Gait.STEP` | 2 | `"step"` |
| `GAIT_ROLL` / `Gait.ROLL` | 3 | `"roll"` |
| `GAIT_PITCH` / `Gait.PITCH` | 4 | `"pitch"` |
| `GAIT_STRETCH` / `Gait.STRETCH` | 5 | `"stretch"` |
| `GAIT_ADVANCE` / `Gait.ADVANCE` | 6 | `"advance"` |
| `GAIT_BACK` / `Gait.BACK` | 7 | `"back"` |
| `GAIT_LEFT` / `Gait.LEFT` | 8 | `"left"` |
| `GAIT_RIGHT` / `Gait.RIGHT` | 9 | `"right"` |
| `GAIT_TURN_L` / `Gait.TURN_L` | 10 | `"turnL"` |
| `GAIT_TURN_R` / `Gait.TURN_R` | 11 | `"turnR"` |
| `GAIT_TWERK` / `Gait.TWERK` | 12 | `"twerk"` |
| `GAIT_JUMP` / `Gait.JUMP` | 13 | `"jump"` |
| `GAIT_JUMP_FWD` / `Gait.JUMP_FWD` | 14 | `"jumpfwd"` |
| `GAIT_TEST_SPD` / `Gait.TEST_SPD` | 15 | `"testspeed"` |
| `GAIT_LOOK_UP` / `Gait.LOOK_UP` | 16 | `"lookup"` |
| `GAIT_LOOK_DOWN` / `Gait.LOOK_DOWN` | 17 | `"lookdown"` |
| `GAIT_LOOK_LEFT` / `Gait.LOOK_LEFT` | 18 | `"lookleft"` |
| `GAIT_LOOK_RIGHT` / `Gait.LOOK_RIGHT` | 19 | `"lookright"` |
| `GAIT_LOOK_UL` / `Gait.LOOK_UL` | 20 | `"lookul"` |
| `GAIT_LOOK_UR` / `Gait.LOOK_UR` | 21 | `"lookur"` |
| `GAIT_LOOK_LL` / `Gait.LOOK_LL` | 22 | `"lookll"` |
| `GAIT_LOOK_LR` / `Gait.LOOK_LR` | 23 | `"looklr"` |
| `GAIT_FORELEG_LIFT_L` / `Gait.FORELEG_LIFT_L` | 24 | `"flegL"` |
| `GAIT_FORELEG_LIFT_R` / `Gait.FORELEG_LIFT_R` | 25 | `"flegR"` |
| `GAIT_BACKLEG_LIFT_L` / `Gait.BACKLEG_LIFT_L` | 26 | `"blegL"` |
| `GAIT_BACKLEG_LIFT_R` / `Gait.BACKLEG_LIFT_R` | 27 | `"blegR"` |
| `GAIT_HEIGHT_UP` / `Gait.HEIGHT_UP` | 28 | `"heightup"` |
| `GAIT_HEIGHT_DOWN` / `Gait.HEIGHT_DOWN` | 29 | `"heightdown"` |
| `GAIT_BALANCE` / `Gait.BALANCE` | 30 | `"balance"` |
| `GAIT_BOW_BACK` / `Gait.BOW_BACK` | 31 | `"bowback"` |
| `GAIT_BODY_CYCLE` / `Gait.BODY_CYCLE` | 32 | `"bodycycle"` |
| `GAIT_HEAD_ELLIPSE` / `Gait.HEAD_ELLIPSE` | 33 | `"headellipse"` |
| `GAIT_MOVE_LF` / `Gait.MOVE_LF` | 34 | `"moveLF"` |
| `GAIT_MOVE_RF` / `Gait.MOVE_RF` | 35 | `"moveRF"` |
| `GAIT_MOVE_LB` / `Gait.MOVE_LB` | 36 | `"moveLB"` |
| `GAIT_MOVE_RB` / `Gait.MOVE_RB` | 37 | `"moveRB"` |

**C:** `robot_gait_enum(GAIT_ADVANCE);`
**AS:** `robotGait(Gait.ADVANCE);`

### Degree-Based Servo Control

Set servo angles in degrees instead of centidegrees:

| Helper | Description |
|--------|-------------|
| `robot_set_servo_deg(id, deg)` / `setServoDeg(id, deg)` | Set angle in degrees (auto × 100). |
| `robot_set_servo_raw(id, raw)` (C only) | Set angle in raw 0–1023 units. |
| `robot_set_servo(id, deg, speed)` / `setServo(id, deg, speed)` | Set angle + speed in one call. |

### Config Struct

A struct bundles the five config parameters:

```c
// C
robot_config_t cfg = { .period = 100, .height = 70, .up_height = 10, .stride = 10, .tilt = 10 };
robot_set_config_ex(cfg);
robot_config_t current = robot_get_config_ex();
```

```ts
// AssemblyScript
const cfg = new RobotConfig(100, 70, 10, 10, 10);
setRobotConfig(cfg);
const current = getRobotConfig();
```

### Choreography Helpers

One-liner actions that combine gait + delay + stop:

| C | AssemblyScript | Behaviour |
|---|---------------|-----------|
| `robot_walk_forward(ms)` | `walkForward(ms)` | Walk forward for N ms |
| `robot_walk_backward(ms)` | `walkBackward(ms)` | Walk backward for N ms |
| `robot_turn_left(ms)` | `turnLeft(ms)` | Turn left for N ms |
| `robot_turn_right(ms)` | `turnRight(ms)` | Turn right for N ms |
| `robot_strafe_left(ms)` | `strafeLeft(ms)` | Sidestep left for N ms |
| `robot_strafe_right(ms)` | `strafeRight(ms)` | Sidestep right for N ms |
| `robot_jump()` | `jump()` | Single jump |
| `robot_stand()` | `stand()` | Stand to init pose |
| `robot_dance(ms)` | `dance(ms)` | Twerk dance for N ms |
| `robot_step_in_place(ms)` | `stepInPlace(ms)` | Step in place for N ms |
| `robot_look_up(ms)` | `lookUp(ms)` | Look up for N ms |
| `robot_look_down(ms)` | `lookDown(ms)` | Look down for N ms |
| `robot_look_left(ms)` | `lookLeft(ms)` | Look left for N ms |
| `robot_look_right(ms)` | `lookRight(ms)` | Look right for N ms |
| `robot_look_upper_left(ms)` | `lookUpperLeft(ms)` | Look upper-left for N ms |
| `robot_look_upper_right(ms)` | `lookUpperRight(ms)` | Look upper-right for N ms |
| `robot_look_lower_left(ms)` | `lookLowerLeft(ms)` | Look lower-left for N ms |
| `robot_look_lower_right(ms)` | `lookLowerRight(ms)` | Look lower-right for N ms |
| `robot_foreleg_lift_left(ms)` | `forelegLiftL(ms)` | Lift left foreleg for N ms |
| `robot_foreleg_lift_right(ms)` | `forelegLiftR(ms)` | Lift right foreleg for N ms |
| `robot_backleg_lift_left(ms)` | `backlegLiftL(ms)` | Lift left back leg for N ms |
| `robot_backleg_lift_right(ms)` | `backlegLiftR(ms)` | Lift right back leg for N ms |
| `robot_height_up(ms)` | `heightUp(ms)` | Raise body height for N ms |
| `robot_height_down(ms)` | `heightDown(ms)` | Lower body height for N ms |
| `robot_balance(ms)` | `balance(ms)` | Balance on the spot for N ms |
| `robot_bow_back(ms)` | `bowBack(ms)` | Bow backward for N ms |
| `robot_body_cycle(ms)` | `bodyCycle(ms)` | Cycle body for N ms |
| `robot_head_ellipse(ms)` | `headEllipse(ms)` | Head ellipse motion for N ms |
| `robot_move_lf(ms)` | `moveLF(ms)` | Move left front leg for N ms |
| `robot_move_rf(ms)` | `moveRF(ms)` | Move right front leg for N ms |
| `robot_move_lb(ms)` | `moveLB(ms)` | Move left back leg for N ms |
| `robot_move_rb(ms)` | `moveRB(ms)` | Move right back leg for N ms |

### Full Pose Helper

Set all 12 servos at once and flush:

```c
// C
robot_apply_pose((robot_pose_t){
    .fr_shoulder = -30, .fr_knee = 60,
    .fl_shoulder =  30, .fl_knee = 60,
    // ...
});
```

```ts
// AssemblyScript
applyPose(new RobotPose(
    0, -30, 60,   // FR: hip, shoulder, knee
    0,  30, 60,   // FL
    0,  30, 60,   // RR
    0, -30, 60,   // RL
));
```

### Integer Printing

Print an integer directly to the log (handles negatives):

**C only:** `MPX_print_int(42);`

### IK Helpers

Set per-leg IK targets from a structured object:

```ts
// AssemblyScript only
const target = new ikTarget(10.0, 5.0, -30.0);
ikFR(target);
ikFL(target);
ikRR(target);
ikRL(target);
```

### IMU Data

Read IMU data into a structured object:

```ts
// AssemblyScript only
const imu = readImu();
// imu.ax, imu.ay, imu.az, imu.gx, imu.gy, imu.gz
```

---

## SDK Headers

The canonical declarations live in the SDK source tree:

| Language | File |
|----------|------|
| C / C++ | [`mpx-cli/src/mpx_cli/commands/resource/mpx_host.h`](mpx-cli/src/mpx_cli/commands/resource/mpx_host.h) |
| AssemblyScript | [`mpx-cli/src/mpx_cli/commands/resource/mpx_env.ts`](mpx-cli/src/mpx_cli/commands/resource/mpx_env.ts) |
| WAT | [`mpx-cli/src/mpx_cli/commands/resource/host_functions_wat.md`](mpx-cli/src/mpx_cli/commands/resource/host_functions_wat.md) |

When you run `mpx-cli init`, the appropriate header is copied into your
project's `include/` directory automatically.
