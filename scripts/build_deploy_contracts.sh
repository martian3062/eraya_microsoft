#!/usr/bin/env bash
# Build + test + deploy the ERAYA Odra contracts (run on Linux with Rust).
#
#   ./scripts/build_deploy_contracts.sh test     # cargo odra test (MockVM, no chain)
#   ./scripts/build_deploy_contracts.sh build    # produce wasm/*.wasm
#   ./scripts/build_deploy_contracts.sh deploy   # put both contracts on testnet
#
# deploy needs: CASPER_SECRET_KEY_PATH, CASPER_NODE_RPC_URL
#               (optional CASPER_CHAIN_NAME, default casper-test)
# After deploy, set on the backend:
#   CASPER_AGENT_REGISTRY_HASH=hash-…   CASPER_TRADE_POLICY_HASH=hash-…
set -euo pipefail
cd "$(dirname "$0")/../contracts"

ensure_toolchain() {
  command -v cargo >/dev/null || { echo "rust missing — install rustup first"; exit 1; }
  rustup target add wasm32-unknown-unknown
  command -v cargo-odra >/dev/null || cargo install cargo-odra --locked
}

case "${1:-test}" in
  test)
    ensure_toolchain
    cargo odra test
    ;;
  build)
    ensure_toolchain
    cargo odra build -b casper
    ls -la wasm/
    ;;
  deploy)
    : "${CASPER_SECRET_KEY_PATH:?set CASPER_SECRET_KEY_PATH}"
    : "${CASPER_NODE_RPC_URL:?set CASPER_NODE_RPC_URL}"
    CHAIN="${CASPER_CHAIN_NAME:-casper-test}"
    for wasm in wasm/AgentRegistry.wasm wasm/TradePolicy.wasm; do
      [ -f "$wasm" ] || { echo "$wasm missing — run build first"; exit 1; }
      echo "── deploying $wasm to $CHAIN"
      casper-client put-transaction session \
        --node-address "$CASPER_NODE_RPC_URL" \
        --chain-name "$CHAIN" \
        --secret-key "$CASPER_SECRET_KEY_PATH" \
        --wasm-path "$wasm" \
        --session-entry-point call \
        --payment-amount 300000000000 \
        --gas-price-tolerance 1 \
        --pricing-mode classic \
        --standard-payment true
      echo "   → note the transaction hash; fetch the contract package hash from"
      echo "     testnet.cspr.live and export CASPER_*_HASH for the backend."
    done
    ;;
  *)
    echo "usage: $0 [test|build|deploy]"; exit 1;;
esac
