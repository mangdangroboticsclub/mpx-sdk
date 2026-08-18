# The ABI

A skill is a WebAssembly module. It can only reach the robot through functions
the firmware registers with the runtime, and the exact set of those — their
names, argument types and return types — is the ABI.

WAMR checks signatures at instantiation. If a module disagrees with the
firmware, it either fails to link or traps on the first call to the function
that moved. That is why a version number exists and why every skill should
start with `MPX_REQUIRE_ABI()`.

## One source of truth

The firmware's `NativeSymbol` table is the only place a host function really
exists:

```
mangdang/main/sdk/wasm_host_functions.h     ← the table. Edit here.
        │
        │  python tools/gen_abi.py --write
        ▼
   abi/host_functions.json                  machine-readable
   sdk/assemblyscript/mpx_env.ts            AssemblyScript bindings
   sdk/wat/host-functions.md                WAT imports
   docs/reference/host-functions.md         the reference page
   docs/reference/errors.md                 the error table

   sdk/include/mpx/abi.h                    CHECKED, not overwritten
```

`sdk/include/mpx/abi.h` is prose around a generated body, so the generator
verifies its declarations rather than rewriting its comments. Everything else
is produced wholesale.

```bash
python tools/gen_abi.py --check     # CI; non-zero on drift
python tools/gen_abi.py --write
python tools/gen_docs.py --check    # gaits.md and cli.md
```

**Run `--check` in CI.** This is not a style preference. The repo previously
carried four hand-maintained copies of the same header; two had gone stale and
one still described ABI v1, which meant it would load and then trap with no
explanation. A snapshot of a moving target goes stale by default.

## Adding a host function

1. **Implement it** in `main/sdk/wasm_host_functions.cc`. Return `int32_t`.
   Check `wasm::was_cancelled()` first and return `MPX_ERR_CANCELLED`. If it
   writes joints, check `control_allows(...)` and return `MPX_ERR_BUSY`.
2. **Declare it** in `main/sdk/wasm_host_functions.h`.
3. **Add it to `NATIVE_SYMBOLS[]`** with its WAMR signature string.
4. **Bump `MPX_ABI_VERSION`** if you changed or removed anything. Purely
   additive? It still needs a bump, because a module built against the new
   header imports a symbol older firmware does not have and will fail to
   instantiate.
5. `python tools/gen_abi.py --write`
6. **Add the friendly wrapper** to the right `sdk/include/mpx/*.h`, as a
   `static inline` in degrees and with a name a maker would guess.
7. **Document it** in the relevant `docs/guide/` page. The reference page
   regenerates itself; the guide is where it means something.

### Signature strings

| Letter | Type | Notes |
|---|---|---|
| `i` | i32 | also pointers-as-integers |
| `f` | f32 | |
| `I` / `F` | i64 / f64 | |
| `$` | string pointer | WAMR converts it to a native pointer for you |

`"(iff)i"` is "takes an int and two floats, returns an int".

**A signature that omits the result silently discards it.** That was the ABI v1
bug: seventeen functions computed an error code that no skill could ever see,
so a misspelled gait name and a successful call were indistinguishable.

## Versions

| Version | What changed |
|---|---|
| **v1** | Original. Seventeen functions computed error codes the signature discarded, so no skill could see them. |
| **v2** | Every host function returns `int32_t`. Added `mpx_abi_version()`, `robot_read_angle_cdeg()` (a read in the *same* frame as the write, so a closed loop converges), the `servo_*` bus family, and made three calibration parameters read-only from a skill. |
| **v3** | Added continuous drive (`mpx_drive`), a clock (`mpx_millis`, `mpx_sleep_until`), per-run parameters, an optional `on_stop` export, opt-in control arbitration (`mpx_control_take`), one-call foot placement, and the walk-speed and temperature accessors that existed in the firmware but not in the ABI. Nothing was removed or changed in meaning. |

v3 is opt-in in behaviour: a skill that never calls the new functions sees
exactly v2 semantics. It is still a breaking change at the *link* level,
because a module built against the v3 header imports symbols v2 firmware does
not provide.

## The compatibility shim

`sdk/include/mpx_compat.h` maps the v2 names onto their v3 equivalents so
existing sources keep compiling for one release. Names whose *meaning* changed
warn. It will be removed; port off it.
