//! The Quant Desk risk envelope + trade record, on-chain.
//!
//! The user's single risk dial (1-10) is written on-chain and the FULL policy
//! is derived inside the contract with the same integer math as
//! `backend/core/quant/engine.py::risk_profile` (values in basis points).
//! Every executed trade is recorded and emitted as an event, so the swarm's
//! trading activity is publicly auditable on Casper.
use odra::prelude::*;

#[odra::odra_error]
pub enum Error {
    NotOwner = 1,
    RiskOutOfRange = 2,
    TradeNotFound = 3,
}

#[odra::odra_type]
pub struct Policy {
    pub risk: u8,
    pub max_position_bps: u32,
    pub stop_loss_bps: u32,
    pub take_profit_bps: u32,
    pub max_trades_day: u32,
    pub cooldown_s: u32,
    pub drawdown_halt_bps: u32,
}

#[odra::odra_type]
pub struct TradeRecord {
    pub id: u64,
    pub side: String,          // "BUY" | "SELL"
    pub qty_units: u64,        // CSPR units traded
    pub price_micro_usd: u64,  // fill price * 1e6
    pub score_milli: i32,      // ensemble score * 1000
    pub risk: u8,
    pub block_time: u64,
}

#[odra::event]
pub struct RiskUpdated {
    pub risk: u8,
    pub max_position_bps: u32,
    pub stop_loss_bps: u32,
}

#[odra::event]
pub struct TradeExecuted {
    pub id: u64,
    pub side: String,
    pub qty_units: u64,
    pub price_micro_usd: u64,
    pub score_milli: i32,
}

/// Integer lerp over the 1-10 dial: a + (b - a) * (r - 1) / 9.
fn lerp(a: i64, b: i64, r: u8) -> i64 {
    a + (b - a) * (r as i64 - 1) / 9
}

#[odra::module(events = [RiskUpdated, TradeExecuted], errors = Error)]
pub struct TradePolicy {
    owner: Var<Address>,
    risk: Var<u8>,
    trade_count: Var<u64>,
    trades: Mapping<u64, TradeRecord>,
}

#[odra::module]
impl TradePolicy {
    pub fn init(&mut self) {
        self.owner.set(self.env().caller());
        self.risk.set(3);
        self.trade_count.set(0);
    }

    pub fn set_risk(&mut self, risk: u8) {
        self.assert_owner();
        if !(1..=10).contains(&risk) {
            self.env().revert(Error::RiskOutOfRange);
        }
        self.risk.set(risk);
        let p = self.policy();
        self.env().emit_event(RiskUpdated {
            risk,
            max_position_bps: p.max_position_bps,
            stop_loss_bps: p.stop_loss_bps,
        });
    }

    /// Mirror of engine.risk_profile, basis points / integer domain.
    pub fn policy(&self) -> Policy {
        let r = self.risk.get_or_default().max(1);
        Policy {
            risk: r,
            max_position_bps: lerp(500, 6000, r) as u32,
            stop_loss_bps: lerp(120, 600, r) as u32,
            take_profit_bps: lerp(200, 1000, r) as u32,
            max_trades_day: lerp(4, 40, r) as u32,
            cooldown_s: lerp(600, 45, r) as u32,
            drawdown_halt_bps: lerp(200, 1200, r) as u32,
        }
    }

    pub fn record_trade(
        &mut self,
        side: String,
        qty_units: u64,
        price_micro_usd: u64,
        score_milli: i32,
    ) -> u64 {
        self.assert_owner();
        let id = self.trade_count.get_or_default() + 1;
        self.trade_count.set(id);
        let record = TradeRecord {
            id,
            side: side.clone(),
            qty_units,
            price_micro_usd,
            score_milli,
            risk: self.risk.get_or_default(),
            block_time: self.env().get_block_time(),
        };
        self.trades.set(&id, record);
        self.env().emit_event(TradeExecuted { id, side, qty_units, price_micro_usd, score_milli });
        id
    }

    pub fn get_trade(&self, id: u64) -> Option<TradeRecord> {
        self.trades.get(&id)
    }

    pub fn trade_count(&self) -> u64 {
        self.trade_count.get_or_default()
    }

    pub fn risk(&self) -> u8 {
        self.risk.get_or_default()
    }

    fn assert_owner(&self) {
        if Some(self.env().caller()) != self.owner.get() {
            self.env().revert(Error::NotOwner);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use odra::host::{Deployer, NoArgs};

    #[test]
    fn default_policy_matches_engine_math() {
        let env = odra_test::env();
        let policy = TradePolicyHostRef::deploy(&env, NoArgs);
        let p = policy.policy();
        // risk 3 -> t = 2/9; matches backend risk_profile(3)
        assert_eq!(p.risk, 3);
        assert_eq!(p.max_position_bps, 500 + (6000 - 500) * 2 / 9);   // 1722
        assert_eq!(p.stop_loss_bps, 120 + (600 - 120) * 2 / 9);       // 226
        assert_eq!(p.max_trades_day, 4 + (40 - 4) * 2 / 9);           // 12
    }

    #[test]
    fn set_risk_bounds_and_update() {
        let env = odra_test::env();
        let mut policy = TradePolicyHostRef::deploy(&env, NoArgs);
        policy.set_risk(10);
        assert_eq!(policy.risk(), 10);
        assert_eq!(policy.policy().max_position_bps, 6000);
        assert_eq!(policy.policy().cooldown_s, 45);
        assert!(policy.try_set_risk(0).is_err());
        assert!(policy.try_set_risk(11).is_err());
    }

    #[test]
    fn record_and_read_trades() {
        let env = odra_test::env();
        let mut policy = TradePolicyHostRef::deploy(&env, NoArgs);
        policy.set_risk(8);
        let id = policy.record_trade("BUY".into(), 3_131_833, 1525, 620);
        assert_eq!(id, 1);
        let id2 = policy.record_trade("SELL".into(), 3_131_833, 1600, -500);
        assert_eq!(id2, 2);
        assert_eq!(policy.trade_count(), 2);
        let t = policy.get_trade(1).unwrap();
        assert_eq!(t.side, "BUY");
        assert_eq!(t.risk, 8);
    }

    #[test]
    fn non_owner_rejected() {
        let env = odra_test::env();
        let mut policy = TradePolicyHostRef::deploy(&env, NoArgs);
        env.set_caller(env.get_account(1));
        assert!(policy.try_set_risk(5).is_err());
        assert!(policy.try_record_trade("BUY".into(), 1, 1, 1).is_err());
    }
}
