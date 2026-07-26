#!/usr/bin/env bash
# Arm/disarm provider API keys on the live VM WITHOUT writing them to VM disk.
#
#   ./scripts/keys_live.sh on     # inject keys (systemd manager memory) + restart
#   ./scripts/keys_live.sh off    # purge keys + restart (graceful fallback mode)
#   ./scripts/keys_live.sh status # which providers the live service sees
#
# Keys live ONLY in a local file (never in the repo, never on the VM's disk):
#   default D:/newvm/eraya_keys.env — override with ERAYA_KEYS_FILE=…
# Injection uses `systemctl set-environment` + the unit's PassEnvironment=,
# so values exist only in systemd/service process memory and vanish on VM
# reboot — re-run `on` after a reboot to re-arm.
set -euo pipefail

VM="pardeep@35.186.145.34"
SSH_KEY="${ERAYA_VM_KEY:-D:/newvm/vm3/vm3_rsa}"
KEYS_FILE="${ERAYA_KEYS_FILE:-D:/newvm/eraya_keys.env}"
VARS=(GROQ_API_KEY GROQ_API_KEY_2 KIMI_API_KEY SARVAM_API_KEY PINECONE_API_KEY TABPFN_API_KEY FIRECRAWL_API_KEY HF_TOKEN)

case "${1:-status}" in
  on)
    [ -f "$KEYS_FILE" ] || { echo "keys file not found: $KEYS_FILE"; exit 1; }
    # Ship assignments via stdin (not argv) so they don't land in shell history.
    grep -E "^[A-Z0-9_]+=." "$KEYS_FILE" | ssh -i "$SSH_KEY" "$VM" '
      sudo bash -c "
        while IFS= read -r line; do systemctl set-environment \"\$line\"; done
        systemctl restart eraya-backend
      "'
    echo "keys armed (in-memory only) + service restarted"
    ;;
  off)
    ssh -i "$SSH_KEY" "$VM" "sudo bash -c 'systemctl unset-environment ${VARS[*]} 2>/dev/null; systemctl restart eraya-backend'"
    echo "keys purged from systemd memory + service restarted (fallback mode)"
    ;;
  status)
    ssh -i "$SSH_KEY" "$VM" "curl -s http://127.0.0.1:8022/api/domains/providers/status/" \
      | python -c "import json,sys; p=json.load(sys.stdin)['providers']; print('llm_chain:',p['llm_chain']); print('configured:',p['configured'])"
    ;;
  *) echo "usage: $0 [on|off|status]"; exit 1;;
esac
