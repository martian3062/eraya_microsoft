//! ERAYA on-chain contracts (Odra / Casper 2.0).
//!
//! `AgentRegistry` — verifiable on-chain identity + reputation for the four
//! swarm archetypes. `TradePolicy` — the Quant Desk risk envelope stored
//! on-chain: the user's single risk dial is written to the chain, the full
//! derived policy is computed *in the contract* (same integer math as
//! `backend/core/quant/engine.py::risk_profile`), and every executed trade is
//! recorded as an on-chain event.
#![cfg_attr(not(test), no_std)]

extern crate alloc;

pub mod agent_registry;
pub mod trade_policy;
