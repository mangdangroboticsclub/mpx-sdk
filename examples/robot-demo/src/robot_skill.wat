;; robot_skill.wat — MPX-Dog WASM Skill: Full Robot Demo (WAT)
;;
;; Compile:
;;   mpx-cli build src/robot_skill.wat -o build/robot_skill.wasm --validate
;;
;; Upload & run:
;;   mpx-cli upload build/robot_skill.wasm
;;   mpx-cli run robot_skill.wasm
;;
;; Sequence: init → step → advance → turnL → jump → none

(module
    ;; ── Import robot host functions from "env" ──────────────────
    (import "env" "print"          (func $print          (param i32 i32)))
    (import "env" "robot_gait"     (func $robot_gait     (param i32)))
    (import "env" "robot_set_config" (func $robot_set_config
        (param i32 i32 i32 i32 i32)))
    (import "env" "robot_delay_ms" (func $robot_delay_ms (param i32)))
    (import "env" "robot_ping_servo" (func $robot_ping_servo
        (param i32) (result i32)))

    ;; ── Export linear memory (1 page = 64 KB) ──────────────────
    (memory (export "memory") 2)

    ;; ── String data at fixed offsets ───────────────────────────
    (data (i32.const 0) "robot_skill: starting demo\n")
    (data (i32.const 64) "robot_skill: servo 1 OK\n")
    (data (i32.const 128) "robot_skill: servo 1 NOT RESPONDING\n")
    (data (i32.const 192) "robot_skill: init pose\n")
    (data (i32.const 256) "robot_skill: stepping\n")
    (data (i32.const 320) "robot_skill: advancing\n")
    (data (i32.const 384) "robot_skill: turn left\n")
    (data (i32.const 448) "robot_skill: jump\n")
    (data (i32.const 512) "robot_skill: stopping\n")
    (data (i32.const 576) "robot_skill: demo complete\n")

    ;; Gait name strings
    (data (i32.const 640) "init")
    (data (i32.const 704) "step")
    (data (i32.const 768) "advance")
    (data (i32.const 832) "turnL")
    (data (i32.const 896) "jump")
    (data (i32.const 960) "none")

    ;; ── Helper: print a log string ─────────────────────────────
    (func $log_msg (param $offset i32) (param $len i32)
        local.get $offset
        local.get $len
        call $print
    )

    ;; ── Entry point ─────────────────────────────────────────────
    (func (export "on_start")
        ;; --- Intro ---
        i32.const 0
        i32.const 28
        call $log_msg

        ;; --- Step 1: Ping servo 1 ---
        i32.const 1
        call $robot_ping_servo
        i32.const 0
        i32.gt_s
        if
            i32.const 64
            i32.const 23
            call $log_msg
        else
            i32.const 128
            i32.const 33
            call $log_msg
        end

        ;; --- Step 2: Configure gait parameters ---
        i32.const 100      ;; period
        i32.const 70       ;; height
        i32.const 10       ;; lift
        i32.const 10       ;; stride
        i32.const 10       ;; tilt
        call $robot_set_config

        ;; --- Step 3: Init pose ---
        i32.const 192
        i32.const 24
        call $log_msg
        i32.const 640      ;; "init"
        call $robot_gait
        i32.const 3000
        call $robot_delay_ms

        ;; --- Step 4: Step in place ---
        i32.const 256
        i32.const 25
        call $log_msg
        i32.const 704      ;; "step"
        call $robot_gait
        i32.const 3000
        call $robot_delay_ms

        ;; --- Step 5: Walk forward ---
        i32.const 320
        i32.const 26
        call $log_msg
        i32.const 768      ;; "advance"
        call $robot_gait
        i32.const 3000
        call $robot_delay_ms

        ;; --- Step 6: Turn left ---
        i32.const 384
        i32.const 26
        call $log_msg
        i32.const 832      ;; "turnL"
        call $robot_gait
        i32.const 2000
        call $robot_delay_ms

        ;; --- Step 7: Jump ---
        i32.const 448
        i32.const 21
        call $log_msg
        i32.const 896      ;; "jump"
        call $robot_gait
        i32.const 3000
        call $robot_delay_ms

        ;; --- Step 8: Stop ---
        i32.const 512
        i32.const 25
        call $log_msg
        i32.const 960      ;; "none"
        call $robot_gait
        i32.const 1000
        call $robot_delay_ms

        ;; --- Done ---
        i32.const 576
        i32.const 28
        call $log_msg
    )
)
