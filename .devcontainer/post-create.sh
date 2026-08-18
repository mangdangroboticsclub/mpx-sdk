#!/usr/bin/env bash
set -euo pipefail

echo "MPX SDK — setting up"
echo

# ── Install mpx-cli from source ───────────────────────────────
CLI_DIR="${PWD}/cli"
if [[ -d "${CLI_DIR}" ]]; then
    pip install -e "${CLI_DIR}" --quiet
    echo "  ok    mpx-cli installed (editable, from ./cli)"
else
    echo "  !     ./cli not found — run this from the SDK root"
fi

# ── Point every build at the one copy of the headers ──────────
# mpx-cli finds sdk/include by walking up from the source anyway; setting it
# explicitly means a build from outside the repo works too, and makes the
# resolution visible instead of magic.
if [[ -d "${PWD}/sdk/include" ]]; then
    echo "export MPX_SDK_INCLUDE=${PWD}/sdk/include" >> "${HOME}/.bashrc"
    export MPX_SDK_INCLUDE="${PWD}/sdk/include"
    echo "  ok    MPX_SDK_INCLUDE=${MPX_SDK_INCLUDE}"
fi

echo
if command -v mpx-cli &> /dev/null; then
    mpx-cli doctor || true
fi

cat <<'EOT'

Next:

  1.  Join the robot's Wi-Fi (MPX-Dog), then:
        echo "MPX_HOST=192.168.2.1" > .env

  2.  Run something:
        mpx-cli deploy examples/01-hello
        mpx-cli logs -f

  3.  Make your own:
        mpx-cli init my_move && cd my_move && mpx-cli deploy

  Read docs/start/ first, then docs/guide/how-motion-works.md.
EOT
