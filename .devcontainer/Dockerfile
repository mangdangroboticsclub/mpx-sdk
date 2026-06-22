# MPX-Dog Skill Development Kit — Dev Container
#
# Lightweight container for building WebAssembly skills for the MPX-Dog
# robot. Includes all three WASM toolchains (WASI SDK, WABT, AssemblyScript)
# plus the mpx-cli tool for building and deploying skills over Wi-Fi.
#
# No ESP-IDF, no flashing tools — this is strictly for skill development.

FROM python:3.12-slim-bookworm

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# ── System packages ──────────────────────────────────────────────
RUN apt-get update -y && apt-get install -y \
    curl \
    git \
    build-essential \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── Node.js (for AssemblyScript) ─────────────────────────────────
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g assemblyscript \
    && npm cache clean --force

# ── WASI SDK (C/C++ → WASM) ─────────────────────────────────────
RUN curl -sL "https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-24/wasi-sdk-24.0-x86_64-linux.tar.gz" \
    | tar xz -C /opt \
    && mv /opt/wasi-sdk-24.0-x86_64-linux /opt/wasi-sdk

# ── WABT (WAT → WASM) ───────────────────────────────────────────
RUN curl -sL "https://github.com/WebAssembly/wabt/releases/download/1.0.41/wabt-1.0.41-linux-x64.tar.gz" \
    | tar xz -C /opt \
    && mv /opt/wabt-1.0.41 /opt/wabt

# ── PATH ─────────────────────────────────────────────────────────
ENV PATH="/opt/wasi-sdk/bin:/opt/wabt/bin:${PATH}"

CMD ["/bin/bash"]
