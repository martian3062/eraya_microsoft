//! On-chain identity + reputation registry for ERAYA swarm agents.
use odra::prelude::*;

#[odra::odra_error]
pub enum Error {
    NotOwner = 1,
    AgentExists = 2,
    AgentNotFound = 3,
}

#[odra::odra_type]
pub struct AgentInfo {
    pub archetype: String,
    pub public_key: String,
    pub registered_at: u64,
    pub reputation: i64,
    pub active: bool,
}

#[odra::event]
pub struct AgentRegistered {
    pub agent_id: String,
    pub archetype: String,
    pub public_key: String,
}

#[odra::event]
pub struct ReputationChanged {
    pub agent_id: String,
    pub delta: i64,
    pub reputation: i64,
}

#[odra::module(events = [AgentRegistered, ReputationChanged], errors = Error)]
pub struct AgentRegistry {
    owner: Var<Address>,
    agents: Mapping<String, AgentInfo>,
    agent_ids: Var<Vec<String>>,
}

#[odra::module]
impl AgentRegistry {
    pub fn init(&mut self) {
        self.owner.set(self.env().caller());
        self.agent_ids.set(Vec::new());
    }

    pub fn register_agent(&mut self, agent_id: String, archetype: String, public_key: String) {
        self.assert_owner();
        if self.agents.get(&agent_id).is_some() {
            self.env().revert(Error::AgentExists);
        }
        let info = AgentInfo {
            archetype: archetype.clone(),
            public_key: public_key.clone(),
            registered_at: self.env().get_block_time(),
            reputation: 0,
            active: true,
        };
        self.agents.set(&agent_id, info);
        let mut ids = self.agent_ids.get_or_default();
        ids.push(agent_id.clone());
        self.agent_ids.set(ids);
        self.env().emit_event(AgentRegistered { agent_id, archetype, public_key });
    }

    pub fn bump_reputation(&mut self, agent_id: String, delta: i64) {
        self.assert_owner();
        let mut info = self
            .agents
            .get(&agent_id)
            .unwrap_or_revert_with(&self.env(), Error::AgentNotFound);
        info.reputation += delta;
        let reputation = info.reputation;
        self.agents.set(&agent_id, info);
        self.env().emit_event(ReputationChanged { agent_id, delta, reputation });
    }

    pub fn set_active(&mut self, agent_id: String, active: bool) {
        self.assert_owner();
        let mut info = self
            .agents
            .get(&agent_id)
            .unwrap_or_revert_with(&self.env(), Error::AgentNotFound);
        info.active = active;
        self.agents.set(&agent_id, info);
    }

    pub fn get_agent(&self, agent_id: String) -> Option<AgentInfo> {
        self.agents.get(&agent_id)
    }

    pub fn agent_count(&self) -> u32 {
        self.agent_ids.get_or_default().len() as u32
    }

    pub fn list_agents(&self) -> Vec<String> {
        self.agent_ids.get_or_default()
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
    fn register_list_and_reputation() {
        let env = odra_test::env();
        let mut registry = AgentRegistry::deploy(&env, NoArgs);

        for (id, arch) in [
            ("perceiver-casper-001", "perceiver"),
            ("planner-casper-001", "planner"),
            ("recoverer-casper-001", "recoverer"),
            ("guardian-casper-001", "guardian"),
        ] {
            registry.register_agent(id.into(), arch.into(), format!("01{arch}"));
        }
        assert_eq!(registry.agent_count(), 4);
        assert_eq!(registry.list_agents().len(), 4);

        registry.bump_reputation("guardian-casper-001".into(), 7);
        registry.bump_reputation("guardian-casper-001".into(), -2);
        let guardian = registry.get_agent("guardian-casper-001".into()).unwrap();
        assert_eq!(guardian.reputation, 5);
        assert!(guardian.active);

        registry.set_active("guardian-casper-001".into(), false);
        assert!(!registry.get_agent("guardian-casper-001".into()).unwrap().active);
    }

    #[test]
    fn duplicate_registration_reverts() {
        let env = odra_test::env();
        let mut registry = AgentRegistry::deploy(&env, NoArgs);
        registry.register_agent("a".into(), "perceiver".into(), "01aa".into());
        let err = registry.try_register_agent("a".into(), "perceiver".into(), "01aa".into());
        assert!(err.is_err());
    }

    #[test]
    fn non_owner_cannot_register() {
        let env = odra_test::env();
        let mut registry = AgentRegistry::deploy(&env, NoArgs);
        env.set_caller(env.get_account(1));
        let err = registry.try_register_agent("x".into(), "planner".into(), "01bb".into());
        assert!(err.is_err());
    }
}
