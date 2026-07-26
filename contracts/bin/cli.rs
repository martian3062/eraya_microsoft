//! Deploy + interact CLI for the ERAYA contracts (odra-cli).
//!
//! Deploys AgentRegistry + TradePolicy, registers the four swarm archetypes
//! on-chain, and sets the initial risk dial. Livenet config comes from the
//! ODRA_CASPER_LIVENET_* environment variables.

use eraya_contracts::agent_registry::AgentRegistry;
use eraya_contracts::trade_policy::TradePolicy;
use odra::host::{HostEnv, NoArgs};
use odra_cli::{
    deploy::DeployScript, DeployedContractsContainer, DeployerExt, OdraCli,
};

pub struct ErayaDeployScript;

impl DeployScript for ErayaDeployScript {
    fn deploy(
        &self,
        env: &HostEnv,
        container: &mut DeployedContractsContainer,
    ) -> Result<(), odra_cli::deploy::Error> {
        let mut registry =
            AgentRegistry::load_or_deploy(env, NoArgs, container, 400_000_000_000)?;
        let mut policy =
            TradePolicy::load_or_deploy(env, NoArgs, container, 400_000_000_000)?;

        env.set_gas(20_000_000_000);
        for (id, arch) in [
            ("perceiver-casper-001", "perceiver"),
            ("planner-casper-001", "planner"),
            ("recoverer-casper-001", "recoverer"),
            ("guardian-casper-001", "guardian"),
        ] {
            let _ = registry.try_register_agent(
                id.to_string(),
                arch.to_string(),
                format!("demo:{id}"),
            );
        }
        let _ = policy.try_set_risk(3);
        Ok(())
    }
}

pub fn main() {
    OdraCli::new()
        .about("ERAYA contracts deploy/interact CLI")
        .deploy(ErayaDeployScript)
        .contract::<AgentRegistry>()
        .contract::<TradePolicy>()
        .build()
        .run();
}
