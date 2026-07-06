#!/usr/bin/env bash
# Build the AnomalyAnchor Casper contract to WASM.
# Requires: rustup + cargo (installed on the VM), wasm32 target.
set -euo pipefail

source "$HOME/.cargo/env" 2>/dev/null || true
rustup target add wasm32-unknown-unknown >/dev/null 2>&1 || true

CONTRACT_DIR="$(cd "$(dirname "$0")/../contracts/anomaly_anchor" && pwd)"
cd "$CONTRACT_DIR"

echo "Building anomaly_anchor (release, wasm32)…"
cargo build --release --target wasm32-unknown-unknown

WASM="$CONTRACT_DIR/target/wasm32-unknown-unknown/release/anomaly_anchor.wasm"
ls -la "$WASM"
echo "WASM=$WASM"
