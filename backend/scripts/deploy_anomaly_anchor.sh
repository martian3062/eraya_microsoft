#!/usr/bin/env bash
# Deploy the AnomalyAnchor contract to Casper testnet via casper-client.
#
# Prerequisites (env, e.g. from /etc/eraya-backend.env):
#   CASPER_NODE_RPC_URL     testnet node RPC (e.g. http://<node>:7777/rpc)
#   CASPER_SECRET_KEY_PATH  funded testnet secret_key.pem
#   CASPER_CHAIN_NAME       defaults to casper-test
# Requires casper-client on PATH (prebuilt binary or `cargo install casper-client`).
set -euo pipefail

: "${CASPER_NODE_RPC_URL:?set CASPER_NODE_RPC_URL}"
: "${CASPER_SECRET_KEY_PATH:?set CASPER_SECRET_KEY_PATH}"
CHAIN="${CASPER_CHAIN_NAME:-casper-test}"
CLIENT="${CASPER_CLIENT_BIN:-casper-client}"
GAS_TOL="${CASPER_GAS_PRICE_TOLERANCE:-1}"
PRICING="${CASPER_PRICING_MODE:-fixed}"

WASM="${1:-$(cd "$(dirname "$0")/../contracts/anomaly_anchor" && pwd)/target/wasm32-unknown-unknown/release/anomaly_anchor.wasm}"
[ -f "$WASM" ] || { echo "WASM not found: $WASM  (run build_contract.sh first)"; exit 1; }

echo "Deploying $WASM to $CHAIN via $CASPER_NODE_RPC_URL (Casper 2.0 put-transaction)…"
OUT=$("$CLIENT" put-transaction session \
  --node-address "$CASPER_NODE_RPC_URL" \
  --chain-name "$CHAIN" \
  --secret-key "$CASPER_SECRET_KEY_PATH" \
  --wasm-path "$WASM" \
  --install-upgrade \
  --pricing-mode "$PRICING" \
  --gas-price-tolerance "$GAS_TOL")
echo "$OUT"
HASH=$(echo "$OUT" | python3 -c "import sys,json;d=json.load(sys.stdin)['result'];h=d.get('transaction_hash') or d.get('deploy_hash');print(list(h.values())[0] if isinstance(h,dict) else h)" 2>/dev/null || true)
if [ -n "$HASH" ]; then
  echo "transaction_hash=$HASH"
  echo "explorer: https://testnet.cspr.live/transaction/$HASH"
  echo "Poll:  $CLIENT get-transaction $HASH --node-address $CASPER_NODE_RPC_URL"
  echo "After success, read the contract hash from the account's named keys:"
  echo "  $CLIENT get-account --account-identifier $CASPER_PUBLIC_KEY --node-address $CASPER_NODE_RPC_URL"
  echo "then set CASPER_ANOMALY_CONTRACT in /etc/eraya-backend.env."
fi
