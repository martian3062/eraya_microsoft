#!/usr/bin/env bash
# Build + test + deploy the ERAYA Odra contracts (run on Linux with Rust).
#
#   ./scripts/build_deploy_contracts.sh test     # cargo odra test (MockVM, no chain)
#   ./scripts/build_deploy_contracts.sh build    # produce wasm/*.wasm (MVP-lowered)
#   ./scripts/build_deploy_contracts.sh deploy   # odra-cli livenet deploy to testnet
#
# Toolchain notes (learned against Casper testnet, July 2026):
#   * rust-toolchain.toml pins the nightly cargo-odra needs; rustup auto-installs it.
#   * wasm-opt must be binaryen >= 131 (apt's v120 lacks
#     --llvm-memory-copy-fill-lowering; without it the Casper VM rejects the
#     wasm with "Bulk memory operations are not supported").
#   * deploy needs: CASPER_SECRET_KEY_PATH (+ optional CASPER_NODE_URL,
#     default https://node.testnet.casper.network).
#
# The deploy command deploys AgentRegistry + TradePolicy, registers the four
# swarm archetypes on-chain, and sets the initial risk dial (bin/cli.rs).
# Contract package hashes are printed as cspr.live links; export them as
#   CASPER_AGENT_REGISTRY_HASH=hash-…  CASPER_TRADE_POLICY_HASH=hash-…
# for the backend (core/casper/contracts.py).
set -euo pipefail
cd "$(dirname "$0")/../contracts"
export PATH="$HOME/.cargo/bin:$PATH"

ensure_toolchain() {
  command -v cargo >/dev/null || { echo "rust missing — install rustup first"; exit 1; }
  command -v cargo-odra >/dev/null || cargo install cargo-odra --locked
  if ! wasm-opt --help 2>/dev/null | grep -q llvm-memory-copy-fill-lowering; then
    echo "── wasm-opt too old; installing binaryen release into ~/binaryen"
    URL=$(curl -s https://api.github.com/repos/WebAssembly/binaryen/releases/latest \
          | grep -oE "https://[^\"]+x86_64-linux\.tar\.gz" | head -1)
    curl -sL "$URL" -o /tmp/binaryen.tar.gz
    mkdir -p ~/binaryen && tar xzf /tmp/binaryen.tar.gz -C ~/binaryen --strip-components=1
    ln -sf ~/binaryen/bin/wasm-opt ~/.cargo/bin/wasm-opt
  fi
  command -v wasm-strip >/dev/null || { echo "install wabt (wasm-strip)"; exit 1; }
}

case "${1:-test}" in
  test)
    ensure_toolchain
    cargo odra test
    ;;
  build)
    ensure_toolchain
    cargo odra build
    ls -la wasm/
    ;;
  deploy)
    : "${CASPER_SECRET_KEY_PATH:?set CASPER_SECRET_KEY_PATH}"
    NODE="${CASPER_NODE_URL:-https://node.testnet.casper.network}"
    export ODRA_BACKEND=livenet
    export ODRA_CASPER_LIVENET_SECRET_KEY_PATH="$CASPER_SECRET_KEY_PATH"
    export ODRA_CASPER_LIVENET_NODE_ADDRESS="$NODE"
    export ODRA_CASPER_LIVENET_CHAIN_NAME="${CASPER_CHAIN_NAME:-casper-test}"
    export ODRA_CASPER_LIVENET_EVENTS_URL="$NODE/events"
    cargo run --release --bin eraya_contracts_cli -- deploy
    ;;
  *)
    echo "usage: $0 [test|build|deploy]"; exit 1;;
esac
