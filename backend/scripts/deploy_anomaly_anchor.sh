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
PAYMENT="${CONTRACT_PAYMENT_MOTES:-150000000000}"   # 150 CSPR for contract install
CLIENT="${CASPER_CLIENT_BIN:-casper-client}"

WASM="${1:-$(cd "$(dirname "$0")/../contracts/anomaly_anchor" && pwd)/target/wasm32-unknown-unknown/release/anomaly_anchor.wasm}"
[ -f "$WASM" ] || { echo "WASM not found: $WASM  (run build_contract.sh first)"; exit 1; }

echo "Deploying $WASM to $CHAIN via $CASPER_NODE_RPC_URL…"
OUT=$("$CLIENT" put-deploy \
  --node-address "$CASPER_NODE_RPC_URL" \
  --chain-name "$CHAIN" \
  --secret-key "$CASPER_SECRET_KEY_PATH" \
  --payment-amount "$PAYMENT" \
  --session-path "$WASM")
echo "$OUT"
HASH=$(echo "$OUT" | python3 -c "import sys,json;print(json.load(sys.stdin)['result']['deploy_hash'])" 2>/dev/null || true)
if [ -n "$HASH" ]; then
  echo "deploy_hash=$HASH"
  echo "explorer: https://testnet.cspr.live/deploy/$HASH"
  echo "Poll:  $CLIENT get-deploy $HASH --node-address $CASPER_NODE_RPC_URL"
  echo "After success, read the contract hash from the account's named keys and set"
  echo "CASPER_ANOMALY_CONTRACT in /etc/eraya-backend.env."
fi
