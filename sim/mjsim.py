#!/usr/bin/env python3
"""mjsim — run a real .wasm skill through MuJoCo, with the robot's own motor tuning.

WHY THIS EXISTS

MPX Studio answers "are my angles sane?" in the browser, instantly, with no
physics. That covers most of what a skill author needs. What it cannot answer is
"will the joint actually GET there?" — because reaching a commanded angle depends
on gravity, contact, link inertia and the servo's control gains, and none of those
exist in a kinematic preview.

This runs the same .wasm the robot runs, feeds its joint commands into MuJoCo
using your model, and reports the gap between what the skill ASKED for and what
the robot would actually DO.

    python tools/mjsim.py my_skill.wasm
    python tools/mjsim.py my_skill.wasm --video walk.mp4
    python tools/mjsim.py my_skill.wasm --kp 1200 --kv 12      # try a tuning

ON MOTOR TUNING — READ THIS BEFORE TRUSTING A NUMBER

Your driver boards are tuned with:

    Kp = 65      Kd = 800      Kp-current = 0.0006      Kff-current = 0.00022

Those are AT32 firmware units — encoder counts and PWM duty — and they do NOT
convert directly into MuJoCo's actuator gains, which are N·m/rad and N·m·s/rad.
Pasting 65 into MuJoCo would model a servo roughly 13x softer than the model's
own default and tell you confident nonsense.

So this script runs with the MJCF's actuator gains (kp=875, kv=8) and labels
every run **DEFAULT MOTOR TUNING**. That is honest: it means "the stock servo
behaviour", not "your exact Kp=65". Deriving the real mapping needs one
measurement on hardware — command a step, record the response with Servo Studio's
scope, fit kp/kv until the sim's overshoot matches — and that is deliberately a
later stage.

Until then: trust this for *will it fall, will it track, does the gait work*.
Do not trust it to tell you a specific Kp value to flash.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import mujoco
    import numpy as np
    from wasmtime import Engine, Func, FuncType, Instance, Module, Store, ValType
except ImportError as e:
    sys.exit(f"error: {e}\n   pip install mujoco wasmtime numpy")


# ── Servo id (firmware) -> actuator name (MJCF) ──────────────────────────────
# The firmware numbers servos 1-12 front-right first; the MJCF names its joints
# by leg abbreviation. This table is the only place the two vocabularies meet.
SERVO_TO_ACTUATOR = {
    1: "base_rf1", 2: "rf1_rf2", 3: "rf2_rf3",     # front right: hip, shoulder, knee
    4: "base_lf1", 5: "lf1_lf2", 6: "lf2_lf3",     # front left
    7: "base_rb1", 8: "rb1_rb2", 9: "rb2_rb3",     # rear right
   10: "base_lb1", 11: "lb1_lb2", 12: "lb2_lb3",   # rear left
}
JOINT_NAMES = {1:"FR hip",2:"FR shoulder",3:"FR knee", 4:"FL hip",5:"FL shoulder",6:"FL knee",
               7:"RR hip",8:"RR shoulder",9:"RR knee",10:"RL hip",11:"RL shoulder",12:"RL knee"}

GAITS = ["none","init","step","roll","pitch","stretch","advance","back","left","right",
"turnL","turnR","twerk","jump","jumpfwd","testspeed","lookup","lookdown","lookleft","lookright",
"lookul","lookur","lookll","looklr","flegL","flegR","blegL","blegR","heightup","heightdown",
"balance","bowback","bodycycle","headellipse","moveLF","moveRF","moveLB","moveRB","stanford",
"frontkick","wiggle","buttshrug","wiggleL","wiggleR","buttshrugL","buttshrugR"]

LIMIT_DEG = 135.0          # SERVO_RANGE_DEG / 2, from robot.h


# ── 1. Run the skill, recording what it asks for ─────────────────────────────

def record(wasm_path: Path) -> dict:
    """Execute the .wasm with host functions that record instead of actuating.

    Same imports the firmware registers (ABI v2 — every one returns i32), so a
    module built by `mpx-cli deploy` or by MPX Studio runs here unmodified.
    """
    store = Store(Engine())
    module = Module.from_file(store.engine, str(wasm_path))

    frames: list[tuple[int, dict[int, float]]] = []
    pending: dict[int, float] = {}
    log: list[str] = []
    warnings: list[str] = []
    clock = {"ms": 0}
    mem_ref: dict[str, object] = {}

    def cstr(ptr: int, limit: int = 128) -> str:
        mem = mem_ref.get("m")
        if mem is None:
            return ""
        raw = bytearray()
        for i in range(limit):
            b = mem.read(store, ptr + i, ptr + i + 1)
            if not b or b[0] == 0:
                break
            raw += b
        return raw.decode("utf-8", "replace")

    def h_print(ptr, n):
        mem = mem_ref.get("m")
        if mem is not None:
            log.append(mem.read(store, ptr, ptr + n).decode("utf-8", "replace"))
        return 0

    def h_gait(ptr):
        name = cstr(ptr)
        if name not in GAITS:
            warnings.append(f'unknown gait "{name}" — the robot would ignore it')
            return -1
        # A gait is the firmware's own trajectory generator, which this script
        # does not model. Say so rather than silently simulating nothing.
        warnings.append(f'gait("{name}") is generated on-robot and is not simulated here')
        return 0

    def h_set(sid, cdeg):
        if not (1 <= sid <= 12):
            warnings.append(f"servo id {sid} is outside 1-12")
            return -1
        deg = cdeg / 100.0
        if abs(deg) > LIMIT_DEG:
            warnings.append(f"{JOINT_NAMES[sid]} commanded to {deg:.1f}°, past the ±{LIMIT_DEG:.0f}° limit")
        pending[sid] = deg
        return 0

    def h_flush():
        if pending:
            frames.append((clock["ms"], dict(pending)))
        return 0

    def h_delay(ms):
        clock["ms"] += max(0, ms)
        return 0

    i32 = ValType.i32()
    sig = {
        # A well-written skill checks this first and returns early if it does
        # not match — which is exactly what happened the first time this script
        # ran, because the generic fallback answered 0. The skill was right and
        # the harness was wrong.
        "mpx_abi_version":       ([], lambda: 2),
        "print":                 ([i32, i32], h_print),
        "robot_gait":            ([i32], h_gait),
        "robot_set_servo_angle": ([i32, i32], h_set),
        "robot_flush":           ([], h_flush),
        "robot_delay_ms":        ([i32], h_delay),
    }
    imports = []
    for imp in module.imports:
        name = imp.name
        # Build every import from the MODULE'S OWN declared type, never from an
        # assumption. The first version hardcoded i32 for unmodelled functions
        # and blew up on robot_ik_fr, which takes three f32 — so any skill using
        # the built-in IK could not be simulated at all.
        ftype = imp.type
        params = list(ftype.params)
        results = list(ftype.results)
        if name in sig:
            _, fn = sig[name]
            imports.append(Func(store, FuncType(params, results), fn))
        else:
            # Unmodelled: answer "ok" so an unsimulated call does not look like
            # a bug in the skill.
            def stub(*a, _n=len(results)):
                return 0 if _n else None
            imports.append(Func(store, FuncType(params, results), stub))

    inst = Instance(store, module, imports)
    mem_ref["m"] = inst.exports(store).get("memory")
    start = inst.exports(store).get("on_start")
    if start is None:
        sys.exit("error: this module has no on_start export — the robot would reject it too")
    start(store)

    return {"frames": frames, "log": log, "warnings": warnings, "ms": clock["ms"]}


# ── 2. Play it through MuJoCo ────────────────────────────────────────────────

def simulate(model_path: Path, rec: dict, kp=None, kv=None, video=None, settle_s=0.5):
    m = mujoco.MjModel.from_xml_path(str(model_path))
    d = mujoco.MjData(m)

    if kp is not None:
        m.actuator_gainprm[:, 0] = kp
        m.actuator_biasprm[:, 1] = -kp
    if kv is not None:
        m.actuator_biasprm[:, 2] = -kv
    used_kp = float(m.actuator_gainprm[0, 0])
    used_kv = float(-m.actuator_biasprm[0, 2])

    act = {sid: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
           for sid, name in SERVO_TO_ACTUATOR.items()}
    missing = [JOINT_NAMES[s] for s, i in act.items() if i < 0]
    if missing:
        sys.exit(f"error: model has no actuator for {missing}")

    frames = rec["frames"]
    if not frames:
        sys.exit("error: the skill never called robot_flush(), so it commands no joint angles")

    # Let the robot settle onto the floor holding the first pose, so the run
    # measures the gait rather than a drop from spawn height.
    target = np.zeros(m.nu)
    for sid, deg in frames[0][1].items():
        target[act[sid]] = np.radians(deg)
    d.ctrl[:] = target
    for _ in range(int(settle_s / m.opt.timestep)):
        mujoco.mj_step(m, d)

    renderer = None
    if video:
        # Rendering needs a GL context. A desktop has one; a headless container
        # needs OSMesa or EGL, and failing to make a video must not throw away
        # a simulation that otherwise ran fine.
        try:
            renderer = mujoco.Renderer(m, 480, 640)
        except Exception as e:
            print(f"   (no video: {type(e).__name__} — this needs a GL context. "
                  f"On a headless box try MUJOCO_GL=osmesa and "
                  f"'apt install libosmesa6-dev'. The simulation still runs.)")
    out_frames, trace = [], []
    fall_at = None
    z0 = float(d.qpos[2])

    total_ms = frames[-1][0] if frames else 0
    steps = max(1, int((total_ms / 1000.0) / m.opt.timestep))
    fi = 0
    for step in range(steps):
        t_ms = step * m.opt.timestep * 1000.0
        while fi + 1 < len(frames) and frames[fi + 1][0] <= t_ms:
            fi += 1
        for sid, deg in frames[fi][1].items():
            target[act[sid]] = np.radians(deg)
        d.ctrl[:] = target
        mujoco.mj_step(m, d)

        if step % 5 == 0:
            # Everything needed to redraw the run later WITHOUT a GL context.
            # Rendering an mp4 needs OSMesa or a GPU; a container often has
            # neither, and "I cannot see it" makes the whole tool useless. The
            # joint angles and body pose are the simulation — a picture can be
            # rebuilt from them anywhere.
            row = {"t": round(t_ms / 1000.0, 3),
                   "x": round(float(d.qpos[0]), 4),
                   "y": round(float(d.qpos[1]), 4),
                   "z": round(float(d.qpos[2]), 4),
                   "up": round(float(d.xmat[1].reshape(3, 3)[2, 2]), 3),
                   "cmd": {}, "act": {}}
            for sid in SERVO_TO_ACTUATOR:
                jid = m.actuator_trnid[act[sid], 0]
                row["act"][sid] = round(float(np.degrees(d.qpos[m.jnt_qposadr[jid]])), 2)
            for sid, deg in frames[fi][1].items():
                row["cmd"][sid] = round(deg, 2)
            trace.append(row)

        # Upright check: the body's own z axis should still point up.
        up = d.xmat[1].reshape(3, 3)[2, 2] if m.nbody > 1 else 1.0
        if fall_at is None and (up < 0.5 or d.qpos[2] < z0 * 0.45):
            fall_at = t_ms / 1000.0

        if renderer and step % max(1, int(1 / (30 * m.opt.timestep))) == 0:
            renderer.update_scene(d, camera=-1)
            out_frames.append(renderer.render())

    if renderer and out_frames:
        try:
            import imageio.v3 as iio
            iio.imwrite(video, out_frames, fps=30)
        except Exception as e:
            print(f"   (could not write {video}: {e})")

    return {"trace": trace, "fall_at": fall_at, "kp": used_kp, "kv": used_kv,
            "final_z": float(d.qpos[2]), "start_z": z0,
            "travel": float(np.hypot(d.qpos[0], d.qpos[1]))}


# ── 3. Report ────────────────────────────────────────────────────────────────

def report(rec, sim, tuned: bool):
    print()
    print("═" * 68)
    if tuned:
        print("  CUSTOM MOTOR TUNING   kp=%.0f  kv=%.1f" % (sim["kp"], sim["kv"]))
        print("  Not your robot's shipped tuning — results will not match hardware")
        print("  until the AT32<->MuJoCo gain mapping is measured.")
    else:
        print("  DEFAULT MOTOR TUNING")
        print("  Driver boards ship with Kp=65 Kd=800 Kp-current=0.0006")
        print("  Kff-current=0.00022. Those are AT32 units; this run uses the")
        print("  model's equivalent (kp=%.0f kv=%.1f). Good for 'does the gait" % (sim["kp"], sim["kv"]))
        print("  work'. Not a source of Kp values to flash.")
    print("═" * 68)

    for line in rec["log"]:
        print(f'  skill said: "{line}"')
    for w in dict.fromkeys(rec["warnings"]):
        print(f"  ⚠  {w}")

    tr = sim["trace"]
    print(f"\n  {len(rec['frames'])} commanded frames over {rec['ms']/1000:.1f}s")

    if sim["fall_at"] is not None:
        print(f"\n  ❌ THE ROBOT FELL at {sim['fall_at']:.2f}s")
        print(f"     body height {sim['start_z']*1000:.0f} mm → {sim['final_z']*1000:.0f} mm")
    else:
        print(f"\n  ✅ stayed upright for the whole run")
        print(f"     body height {sim['start_z']*1000:.0f} mm → {sim['final_z']*1000:.0f} mm"
              f"   ·   travelled {sim['travel']*1000:.0f} mm")

    # Tracking error: the whole reason to run physics rather than kinematics.
    if tr:
        print("\n  Did the joints actually get there?")
        print("    Two angle conventions, because both are in play:")
        print("      relative  ±135° from centre — what robot_set_servo_angle() takes")
        print("      absolute   0-270°, 135 = centre — what Servo Studio and the boards show")
        print(f"    {'joint':<14}{'mean err':>10}{'worst':>9}{'range (rel)':>18}{'range (abs)':>16}")
        errs = {}
        for row in tr:
            for sid in row["cmd"]:
                errs.setdefault(sid, []).append(abs(row["cmd"][sid] - row["act"][sid]))
        rng = {}
        for row in tr:
            for sid, v in row["act"].items():
                lo, hi = rng.get(sid, (v, v))
                rng[sid] = (min(lo, v), max(hi, v))
        for sid in sorted(errs):
            e = errs[sid]
            lo, hi = rng.get(sid, (0, 0))
            flag = "  ← soft" if max(e) > 12 else ""
            print(f"    {JOINT_NAMES[sid]:<14}{sum(e)/len(e):>9.1f}°{max(e):>8.1f}°"
                  f"{f'{lo:+.0f}..{hi:+.0f}':>18}{f'{135+lo:.0f}..{135+hi:.0f}':>16}{flag}")
        worst = max((max(v) for v in errs.values()), default=0)
        if worst > 12:
            print("\n    A joint lagging its command by more than ~12° under load means")
            print("    the servo is too soft for this motion: raise Kp, slow the")
            print("    trajectory, or carry less weight on that leg.")



# ── Finding the model ────────────────────────────────────────────────────────

def model_candidates() -> list[Path]:
    """Where robot.xml plausibly lives, nearest first.

    This matters more than it looks. The dev container mounts only the SDK
    repo, so a model sitting at C:\\output_mjcf on the host is invisible from
    inside — passing that path produces a "file not found" that reads like a
    typo rather than a mounting problem. Searching, and naming what was
    searched, turns it into an instruction.
    """
    repo = Path(__file__).resolve().parent.parent
    sim = Path(__file__).resolve().parent
    here = Path.cwd()
    names = ["robot.xml"]
    roots = [sim / "model", sim / "model" / "output_mjcf", sim,
             repo / "sim" / "model", repo / "model", repo,
             here, here / "model", here.parent / "output_mjcf",
             Path("/workspaces/output_mjcf"), Path("/output_mjcf"),
             Path("C:/output_mjcf/output_mjcf")]
    return [r / n for r in roots for n in names]


def find_model() -> Path | None:
    for c in model_candidates():
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


# ── Making it visible without a GPU ──────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>mjsim — __TITLE__</title><style>
:root{--y:#FFE605;--bg:#1a1a19;--pn:#232320;--ln:#33332e;--ink:#f2f2ee;--i2:#a8a89e;
      --i3:#6f6f68;--bad:#ED7676;--good:#6AAE6C}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
  font:14px/1.5 ui-sans-serif,system-ui,sans-serif}
header{background:var(--y);color:#000;padding:12px 20px}
header h1{margin:0;font-size:1rem;font-weight:800}
header p{margin:2px 0 0;font-size:.78rem;font-weight:600;opacity:.75}
main{max-width:1180px;margin:0 auto;padding:16px 20px 50px}
.card{background:var(--pn);border:1px solid var(--ln);border-radius:14px;padding:13px 15px}
.card h3{margin:0 0 9px;font-size:.66rem;font-weight:800;letter-spacing:.08em;
  text-transform:uppercase;color:var(--i3)}
.cols{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:14px}
@media(max-width:900px){.cols{grid-template-columns:1fr}}
.verdict{padding:11px 13px;border-radius:11px;background:var(--pn);
  border-left:4px solid var(--i3);margin-bottom:14px}
.verdict.ok{border-left-color:var(--good)}.verdict.bad{border-left-color:var(--bad)}
.verdict b{display:block;font-size:.9rem;margin-bottom:2px}
.verdict span{display:block;font-size:.78rem;color:var(--i2)}
svg{display:block;width:100%;overflow:visible}
.scrub{display:flex;align-items:center;gap:9px;margin-top:10px}
.scrub input{flex:1;accent-color:var(--y)}
button{background:var(--y);color:#000;border:0;border-radius:9px;padding:7px 13px;
  font-weight:800;font-size:.78rem;cursor:pointer}
.t{font-family:ui-monospace,monospace;font-size:.75rem;color:var(--i2);min-width:150px;
  text-align:right}
.axis{fill:var(--i3);font-size:9px;font-family:ui-monospace,monospace}
.gl{stroke:var(--ln);stroke-width:1}
.lim{stroke:var(--i3);stroke-width:1.4;stroke-dasharray:4 4}
.cmd{fill:none;stroke:var(--i3);stroke-width:1.6;stroke-dasharray:3 3}
.act{fill:none;stroke:var(--y);stroke-width:2}
.cur{stroke:var(--i2);stroke-width:1}
.panes{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.pane{background:#1e1e1c;border:1px solid var(--ln);border-radius:10px;padding:8px 10px 2px}
.pane h4{margin:0 0 4px;font-size:.74rem;font-weight:700}
.lg{display:flex;gap:14px;font-size:.68rem;color:var(--i2);margin:0 0 8px}
.sw{display:inline-block;width:14px;height:3px;border-radius:2px;margin-right:5px;
  vertical-align:middle;background:var(--y)}
.sw.d{background:none;border-top:2px dashed var(--i3);height:0}
table{width:100%;border-collapse:collapse;font-size:.77rem}
th,td{text-align:left;padding:4px 6px;border-bottom:1px solid var(--ln)}
th{color:var(--i3);font-size:.63rem;text-transform:uppercase;letter-spacing:.06em}
td.n{text-align:right;font-variant-numeric:tabular-nums;font-family:ui-monospace,monospace}
tr.w td{color:var(--bad)}
.note{font-size:.76rem;color:var(--i3);margin:9px 0 0}
</style></head><body>
<header><h1>mjsim — __TITLE__</h1><p>__TUNING__</p></header>
<main>
<div class="verdict __VCLASS__"><b>__VTITLE__</b><span>__VSUB__</span></div>
<div class="cols">
  <div class="card"><h3>The run — frame <span id="fn">0</span></h3>
    <svg id="stage" viewBox="0 0 420 300"></svg>
    <div class="scrub"><button id="play">▶</button>
      <input type="range" id="sc" min="0" max="0" value="0"><span class="t" id="tm"></span></div>
    <p class="note">Rebuilt from the simulated joint angles, so it needs no GPU.
      Solid = where the joint actually went. The body outline is drawn at the
      height MuJoCo computed.</p>
  </div>
  <div>
    <div class="card"><h3>Commanded vs actual</h3>
      <div class="lg"><span><i class="sw"></i>actual (physics)</span>
        <span><i class="sw d"></i>commanded (your skill)</span></div>
      <div class="panes" id="panes"></div></div>
    <div class="card" style="margin-top:13px"><h3>Body height</h3>
      <svg id="hz" viewBox="0 0 420 110"></svg></div>
    <div class="card" style="margin-top:13px"><h3>Tracking error</h3>
      <table id="tbl"></table></div>
  </div>
</div></main>
<script>
const T = __TRACE__, GEO = __GEO__, FALL = __FALL__, LIMIT = 135;
const NAME = {1:"FR hip",2:"FR shoulder",3:"FR knee",4:"FL hip",5:"FL shoulder",6:"FL knee",
 7:"RR hip",8:"RR shoulder",9:"RR knee",10:"RL hip",11:"RL shoulder",12:"RL knee"};
const SH={RF:2,LF:5,RB:8,LB:11}, KN={RF:3,LF:6,RB:9,LB:12};
const $=s=>document.querySelector(s);
const L1=GEO.L1, L2=GEO.L2, HIPS=GEO.hips;

function stage(i){
  const f=T[i]; if(!f) return "";
  const S=1.25, cx=210, gy=250;
  const bodyY = gy - f.z*1000*S;
  let o="";
  o+=`<line x1="20" y1="${gy}" x2="400" y2="${gy}" stroke="#2c2c28" stroke-width="2"/>`;
  const bx1=cx-HIPS.LB[0]*S, bx2=cx-HIPS.LF[0]*S;
  const tilt=(1-f.up)*90;
  o+=`<g transform="rotate(${tilt.toFixed(1)} ${cx} ${bodyY})">`;
  o+=`<line x1="${bx1}" y1="${bodyY}" x2="${bx2}" y2="${bodyY}" stroke="#3a3a34"
       stroke-width="12" stroke-linecap="round"/>`;
  for(const leg of ["LB","RB","RF","LF"]){
    const sh=f.act[SH[leg]]||0, kn=f.act[KN[leg]]||0;
    const a1=(90+sh)*Math.PI/180, a2=a1+(kn-180)*Math.PI/180;
    const hx=cx-HIPS[leg][0]*S;
    const kx=hx-L1*Math.cos(a1)*S, ky=bodyY+L1*Math.sin(a1)*S;
    const fx=kx-L2*Math.cos(a2)*S, fy=ky+L2*Math.sin(a2)*S;
    const far=leg[0]==="R", col=far?"#8a7d05":"var(--y)";
    o+=`<line x1="${hx}" y1="${bodyY}" x2="${kx}" y2="${ky}" stroke="${col}"
         stroke-width="${far?4:6}" stroke-linecap="round"/>
        <line x1="${kx}" y1="${ky}" x2="${fx}" y2="${fy}" stroke="${col}"
         stroke-width="${far?3.5:5}" stroke-linecap="round"/>
        <circle cx="${fx}" cy="${fy}" r="${far?3:4}" fill="${far?"#8a7d05":"var(--ink)"}"/>`;
  }
  o+=`</g>`;
  o+=`<text x="20" y="24" class="axis">body ${(f.z*1000).toFixed(0)} mm · `
    +`travelled ${(Math.hypot(f.x,f.y)*1000).toFixed(0)} mm</text>`;
  if(FALL!==null && f.t>=FALL)
    o+=`<text x="20" y="42" class="axis" fill="#ED7676">FALLEN (t=${FALL.toFixed(2)}s)</text>`;
  return o;
}

function line(vals,W,H,PL,lo,hi,cls){
  const PR=8,PT=8,PB=14, iw=W-PL-PR, ih=H-PT-PB, sp=(hi-lo)||1;
  const X=i=>PL+(vals.length<2?iw/2:(i/(vals.length-1))*iw);
  const Y=v=>PT+ih-((v-lo)/sp)*ih;
  return `<path class="${cls}" d="${vals.map((v,i)=>`${i?"L":"M"}${X(i).toFixed(1)} ${Y(v).toFixed(1)}`).join(" ")}"/>`;
}

function panes(){
  const used=[...new Set(T.flatMap(f=>Object.keys(f.cmd)))].map(Number).sort((a,b)=>a-b);
  $("#panes").innerHTML=used.slice(0,8).map(sid=>{
    const act=T.map(f=>f.act[sid]??0), cmd=T.map(f=>f.cmd[sid]??null);
    const filled=[]; let last=0;
    for(const c of cmd){ if(c!==null)last=c; filled.push(last); }
    const all=act.concat(filled);
    const lo=Math.min(-20,...all), hi=Math.max(20,...all);
    const W=200,H=92,PL=30;
    let lim="";
    for(const L of [LIMIT,-LIMIT]) if(L>=lo&&L<=hi){
      const y=8+(H-22)-((L-lo)/((hi-lo)||1))*(H-22);
      lim+=`<line class="lim" x1="${PL}" x2="${W-8}" y1="${y}" y2="${y}"/>`;}
    return `<div class="pane"><h4>${NAME[sid]}</h4><svg viewBox="0 0 ${W} ${H}">
      <text class="axis" x="${PL-4}" y="14" text-anchor="end">${hi.toFixed(0)}°</text>
      <text class="axis" x="${PL-4}" y="${H-12}" text-anchor="end">${lo.toFixed(0)}°</text>
      ${lim}${line(filled,W,H,PL,lo,hi,"cmd")}${line(act,W,H,PL,lo,hi,"act")}
      <line class="cur" id="c${sid}" x1="${PL}" x2="${PL}" y1="8" y2="${H-14}"/></svg></div>`;
  }).join("");

  const z=T.map(f=>f.z*1000), lo=Math.min(...z)*0.9, hi=Math.max(...z)*1.05;
  let mark="";
  if(FALL!==null){ const i=T.findIndex(f=>f.t>=FALL);
    if(i>=0){ const x=40+(i/(T.length-1))*(420-48);
      mark=`<line x1="${x}" x2="${x}" y1="8" y2="96" stroke="#ED7676" stroke-width="1.5"/>
            <text x="${x+4}" y="20" class="axis" fill="#ED7676">fell</text>`; }}
  $("#hz").innerHTML=`<text class="axis" x="36" y="14" text-anchor="end">${hi.toFixed(0)}</text>
    <text class="axis" x="36" y="98" text-anchor="end">${lo.toFixed(0)}</text>
    ${line(z,420,110,40,lo,hi,"act")}${mark}
    <line class="cur" id="ch" x1="40" x2="40" y1="8" y2="96"/>`;

  const errs={};
  for(const f of T) for(const s in f.cmd)
    (errs[s]=errs[s]||[]).push(Math.abs(f.cmd[s]-(f.act[s]??0)));
  $("#tbl").innerHTML=`<tr><th>Joint</th><th style="text-align:right">Mean</th>
    <th style="text-align:right">Worst</th><th style="text-align:right">Rel ±135</th>
    <th style="text-align:right">Abs 0-270</th></tr>`
    +Object.keys(errs).sort((a,b)=>a-b).map(s=>{
    const e=errs[s], mx=Math.max(...e);
    const vs=T.map(f=>f.act[s]??0), lo=Math.min(...vs), hi=Math.max(...vs);
    return `<tr class="${mx>12?"w":""}"><td>${NAME[s]}</td>
      <td class="n">${(e.reduce((a,b)=>a+b,0)/e.length).toFixed(1)}°</td>
      <td class="n">${mx.toFixed(1)}°</td>
      <td class="n">${lo.toFixed(0)}..${hi.toFixed(0)}</td>
      <td class="n">${(135+lo).toFixed(0)}..${(135+hi).toFixed(0)}</td></tr>`;}).join("")
    +`<tr><td colspan="5" class="note" style="border:0">Relative is what
      <code>robot_set_servo_angle()</code> takes (±135° from centre). Absolute is what
      Servo Studio and the driver boards report (0-270°, 135 = centre). Same joint,
      two vocabularies — <code>abs = 135 + rel</code>.</td></tr>`;
}

function paint(i){
  $("#stage").innerHTML=stage(i); $("#fn").textContent=i;
  const f=T[i];
  $("#tm").textContent=`${i+1} / ${T.length} · ${f?f.t.toFixed(2):0}s`;
  document.querySelectorAll('[id^="c"]').forEach(el=>{
    const W=el.id==="ch"?420:200, PL=el.id==="ch"?40:30;
    const x=PL+(T.length<2?0:(i/(T.length-1))*(W-PL-8));
    el.setAttribute("x1",x); el.setAttribute("x2",x);});
}
panes();
$("#sc").max=T.length-1; $("#sc").oninput=e=>paint(+e.target.value);
let pl=null;
$("#play").onclick=()=>{ if(pl){clearInterval(pl);pl=null;$("#play").textContent="▶";return;}
  $("#play").textContent="❚❚";
  pl=setInterval(()=>{const s=$("#sc"); s.value=(+s.value+1)>+s.max?0:+s.value+1;
    paint(+s.value);},50);};
paint(0);
</script></body></html>"""


def write_html(path, rec, sim, tuned, title):
    """Rebuild the run as a self-contained page — no GL, no ffmpeg, no server."""
    import json
    fall = sim["fall_at"]
    ok = fall is None
    geo = {"L1": 50.0, "L2": 56.0,
           "hips": {"LF": [50.0, 23.5], "RF": [50.0, -23.5],
                    "RB": [-66.0, -23.5], "LB": [-66.0, 23.5]}}
    sub = (f"{len(rec['frames'])} commanded frames over {rec['ms']/1000:.1f}s · "
           f"body {sim['start_z']*1000:.0f} mm → {sim['final_z']*1000:.0f} mm · "
           f"travelled {sim['travel']*1000:.0f} mm")
    tuning = ("DEFAULT MOTOR TUNING — the model's stock servo response "
              f"(kp={sim['kp']:.0f}, kv={sim['kv']:.1f}). Your boards ship with "
              "Kp=65 Kd=800 Kp-current=0.0006 Kff-current=0.00022, which are AT32 "
              "units and are not the same numbers."
              if not tuned else
              f"CUSTOM TUNING kp={sim['kp']:.0f} kv={sim['kv']:.1f} — not your robot's "
              "shipped tuning.")
    html = (HTML_TEMPLATE
            .replace("__TITLE__", title)
            .replace("__TUNING__", tuning)
            .replace("__VCLASS__", "ok" if ok else "bad")
            .replace("__VTITLE__", "Stayed upright" if ok
                     else f"The robot fell at {fall:.2f}s")
            .replace("__VSUB__", sub)
            .replace("__TRACE__", json.dumps(sim["trace"]))
            .replace("__GEO__", json.dumps(geo))
            .replace("__FALL__", "null" if fall is None else f"{fall:.3f}"))
    Path(path).write_text(html, encoding="utf-8")


def view_live(model_path, rec, kp=None, kv=None):
    """Play the skill in MuJoCo's own 3D viewer, in real time.

    This is the one part that genuinely needs a display, so it will not work
    inside the dev container. Run it from a terminal on your desktop with the
    same packages installed.
    """
    try:
        import mujoco.viewer
    except ImportError:
        print("error: mujoco.viewer unavailable — pip install mujoco"); return 1

    import time
    m = mujoco.MjModel.from_xml_path(str(model_path))
    d = mujoco.MjData(m)
    if kp is not None:
        m.actuator_gainprm[:, 0] = kp; m.actuator_biasprm[:, 1] = -kp
    if kv is not None:
        m.actuator_biasprm[:, 2] = -kv

    act = {s: mujoco.mj_name2id(m, mujoco.mjtObj.mjOBJ_ACTUATOR, n)
           for s, n in SERVO_TO_ACTUATOR.items()}
    frames = rec["frames"]
    if not frames:
        print("error: the skill commands no joint angles"); return 1

    target = np.zeros(m.nu)
    for sid, deg in frames[0][1].items():
        target[act[sid]] = np.radians(deg)

    print("  opening the viewer — close the window to stop.")
    print("  the skill loops, so you can watch it as many times as you like.")
    with mujoco.viewer.launch_passive(m, d) as v:
        while v.is_running():
            d.ctrl[:] = target
            for _ in range(int(0.5 / m.opt.timestep)):     # settle
                mujoco.mj_step(m, d); 
            v.sync()
            t0 = time.time()
            fi = 0
            total = frames[-1][0] / 1000.0
            while v.is_running():
                t = time.time() - t0
                if t > total:
                    break
                while fi + 1 < len(frames) and frames[fi + 1][0] <= t * 1000:
                    fi += 1
                for sid, deg in frames[fi][1].items():
                    target[act[sid]] = np.radians(deg)
                d.ctrl[:] = target
                mujoco.mj_step(m, d)
                v.sync()
                time.sleep(max(0, m.opt.timestep - (time.time() - t0 - t)))
            mujoco.mj_resetData(m, d)                       # loop
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("wasm", type=Path, help="the skill to run")
    ap.add_argument("--model", type=Path, default=None,
                    help="path to robot.xml (searched for if omitted)")
    ap.add_argument("--kp", type=float, help="override actuator kp (advanced)")
    ap.add_argument("--kv", type=float, help="override actuator kv (advanced)")
    ap.add_argument("--view", action="store_true",
                    help="open MuJoCo's interactive 3D viewer and play the skill "
                         "in real time (needs a display — run this on your desktop, "
                         "not inside the container)")
    ap.add_argument("--video", help="write an mp4 (needs a GL context)")
    ap.add_argument("--html", default="mjsim-run.html",
                    help="write a viewable HTML replay (default: mjsim-run.html; "
                         "pass '' to skip). Needs no GPU.")
    args = ap.parse_args()

    if not args.wasm.exists():
        return print(f"error: no such file: {args.wasm}") or 1
    model = args.model or find_model()
    if model is None:
        print("error: could not find robot.xml (the MuJoCo model).\n")
        print("   A dev container only mounts this repo, so a Windows path like")
        print("   C:/output_mjcf/... is not visible from inside it. Copy the model")
        print("   in once and it will be found automatically from then on:\n")
        print("       cp -r /path/to/output_mjcf  sim/model/      # from the repo root")
        print("       # on Windows, before opening the container:")
        print("       #   xcopy /E /I C:\\output_mjcf\\output_mjcf model\n")
        print("   Searched:")
        for c in model_candidates():
            print(f"     {c}")
        return 1
    if not model.exists():
        return print(f"error: model not found: {model}") or 1

    rec = record(args.wasm)

    if args.view:
        return view_live(model, rec, args.kp, args.kv)

    sim = simulate(model, rec, args.kp, args.kv, args.video)
    report(rec, sim, tuned=(args.kp is not None or args.kv is not None))
    if args.html:
        write_html(args.html, rec, sim, tuned=(args.kp is not None or args.kv is not None),
                   title=args.wasm.name)
        print(f"\n  ▶ open this to watch it:  {Path(args.html).resolve()}")
    if args.video:
        print(f"  video: {args.video}")
    print()
    return 1 if sim["fall_at"] is not None else 0


if __name__ == "__main__":
    sys.exit(main())
