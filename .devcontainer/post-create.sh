#!/usr/bin/env bash
set -euo pipefail

echo "============================================="
echo " MPX-Dog Skill Dev Kit — Post-Create Setup"
echo "============================================="

# ── Install mpx-cli (from workspace source) ──────────────────
CLI_DIR="${PWD}/mpx-cli"

if [[ -d "${CLI_DIR}" ]]; then
    echo ""
    echo "📦 Installing mpx-cli from ${CLI_DIR}..."
    pip install -e "${CLI_DIR}" --quiet
    echo "   ✅ mpx-cli installed"
else
    echo ""
    echo "⚠️  mpx-cli source not found at ${CLI_DIR}"
    echo "   You can install it later with: pip install -e ${CLI_DIR}"
fi

# ── Verify toolchains ────────────────────────────────────────
echo ""
echo "🔧 Verifying WASM toolchains..."
if command -v mpx-cli &> /dev/null; then
    mpx-cli build --show-toolchains
else
    # Manual verification
    for tool in /opt/wasi-sdk/bin/clang /opt/wabt/bin/wat2wasm asc; do
        if command -v "${tool}" &> /dev/null; then
            echo "   ✅ ${tool} found"
        else
            echo "   ⚠️  ${tool} not found"
        fi
    done
fi

# ── Summary ──────────────────────────────────────────────────
echo ""
echo "============================================="
echo " ✅ Setup complete!"
echo ""
echo " Quick start:"
echo "   1. Check toolchain status:"
echo "      mpx-cli build --show-toolchains"
echo ""
echo "   2. Build the provided examples:"
echo "      mpx-cli build examples/hello-wasm/src/test_skill.c --validate"
echo "      mpx-cli build examples/robot-demo/src/robot_skill.c --validate"
echo ""
echo "   3. Create a new skill:"
echo "      mpx-cli init my-skill --lang c"
echo ""
echo "   4. Build the new skill:"
echo "      mpx-cli build my-skill/src/my-skill.c -o build/my-skill.wasm --validate"
echo ""
echo "   5. Upload & run (on robot Wi-Fi):"
echo "      mpx-cli upload -i 192.168.2.1 build/my-skill.wasm"
echo "      mpx-cli run -i 192.168.2.1 my-skill.wasm"
echo ""
echo "   Override robot IP via -i (or set \$MPX_HOST env var):"
echo "      mpx-cli -i 192.168.2.1 run my-skill.wasm"
echo "      export MPX_HOST=192.168.2.1"
echo "============================================="
