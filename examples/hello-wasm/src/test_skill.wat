;; test_skill.wat — Minimal MPX-Dog WASM Skill (WAT)
;;
;; Compile:
;;   mpx-cli build src/test_skill.wat -o build/test_skill.wasm
;;
;; Upload & run:
;;   mpx-cli upload build/test_skill.wasm
;;   mpx-cli run test_skill.wasm

(module
    ;; Import "print" from the "env" host module
    (import "env" "print" (func $print (param i32 i32)))

    ;; Export linear memory (1 page = 64 KB)
    (memory (export "memory") 1)

    ;; Store the message string at offset 0
    (data (i32.const 0) "Hello from WASM on ESP32-S3!")

    ;; Entry point — called by the sandbox as "on_start"
    (func (export "on_start")
        i32.const 0      ;; string pointer (offset 0)
        i32.const 30     ;; string length
        call $print
    )
)
