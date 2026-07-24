#!/usr/bin/env python
"""
External agent hires the ERAYA swarm over x402 — live walkthrough.

This is NOT part of ERAYA. It plays the role of a third-party agent (an
elizaOS action, a LangChain tool, an MCP client, or plain curl) that wants
the swarm's quant intelligence and pays for it with Casper x402
micropayments:

    (1) GET the paid resource                    -> 402 Payment Required
    (2) read the X-Payment-* challenge headers   (address, amount, nonce)
    (3) pay on Casper testnet                    (real when a key is
                                                  configured server-side;
                                                  demo-signed otherwise)
    (4) retry with the X-Payment proof header    -> 200 + quant signal

Usage:
    python scripts/external_agent_hire.py [--base http://127.0.0.1:8022]
                                          [--payer <casper-public-key>]
"""
from __future__ import annotations

import argparse
import sys
import time
import uuid

import httpx

if hasattr(sys.stdout, "reconfigure"):  # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUANT_RESOURCE = "/api/domains/casper_defi/quant-signal/"
DEMO_PAYER = "01deadbeef" + uuid.uuid4().hex[:54]  # ad-hoc external agent id


def step(n: int, text: str) -> None:
    print(f"  [{n}] {text}")
    time.sleep(0.4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8022")
    ap.add_argument("--payer", default=DEMO_PAYER,
                    help="Casper public key of the hiring agent")
    args = ap.parse_args()
    url = args.base.rstrip("/") + QUANT_RESOURCE

    print("\n═══ external agent → hiring the ERAYA swarm via x402 ═══\n")
    step(1, f"GET {QUANT_RESOURCE}  (no payment attached)")
    r1 = httpx.get(url, timeout=30)
    if r1.status_code != 402:
        print(f"      unexpected: HTTP {r1.status_code} — is x402 enabled?")
        return 1

    addr = r1.headers.get("X-Payment-Address", "")
    amount = r1.headers.get("X-Payment-Amount", "0")
    nonce = r1.headers.get("X-Payment-Nonce", "")
    net = r1.headers.get("X-Payment-Network", "?")
    step(2, f"HTTP 402 Payment Required — {int(amount):,} motes "
            f"({int(amount)/1e9:.4f} CSPR) on '{net}'")
    print(f"      pay-to : {addr[:20]}…{addr[-6:]}")
    print(f"      nonce  : {nonce}")

    step(3, "paying + signing proof "
            "(on-chain verified when the facilitator has CSPR.cloud)")
    proof = f"casper:{args.payer}:{amount}:sig_{uuid.uuid4().hex[:16]}"

    step(4, "retry with X-Payment proof header")
    r2 = httpx.get(url, headers={"X-Payment": proof, "X-Payment-Nonce": nonce},
                   timeout=30)
    if r2.status_code != 200:
        print(f"      REJECTED: HTTP {r2.status_code} — {r2.text[:200]}")
        return 1

    d = r2.json()
    x = d.get("x402", {})
    print(f"\n  ✔ HTTP 200 — swarm delivered its quant signal "
          f"(paid={x.get('paid')}, mode={x.get('mode')}, "
          f"verified_on_chain={x.get('verified')})\n")
    print(f"      pair     : {d.get('pair')}")
    print(f"      price    : ${d.get('price')}")
    print(f"      score    : {d.get('score'):+} (threshold ±{d.get('threshold')})")
    print(f"      verdict  : {d.get('verdict')}")
    print(f"      RSI-14   : {d.get('rsi14')}   vol(ann): {d.get('vol_annual_pct')}%")
    comp = d.get("components") or {}
    print("      ensemble : " + ", ".join(f"{k} {v:+}" for k, v in comp.items()))
    feed = d.get("feed") or {}
    print(f"      feed     : {feed.get('source')} (live={feed.get('live')})")
    print("\n  Any agent that speaks HTTP can do this — elizaOS, LangChain,")
    print("  MCP tools, curl. The ERAYA swarm is a hireable economic actor.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
