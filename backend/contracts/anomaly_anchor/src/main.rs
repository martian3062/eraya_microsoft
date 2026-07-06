#![no_std]
#![no_main]

//! ERAYA AnomalyAnchor — a minimal Casper smart contract that anchors detected
//! network anomalies on-chain. KAVACHA calls `record_anomaly` for each
//! high-severity finding; the record is stored in a dictionary keyed by anomaly
//! id, and a monotonic counter is bumped. Off-chain code reads the dictionary /
//! counter via state queries and links to https://testnet.cspr.live.

extern crate alloc;

use alloc::string::String;
use alloc::vec;

use casper_contract::contract_api::{runtime, storage};
use casper_contract::unwrap_or_revert::UnwrapOrRevert;
use casper_types::contracts::NamedKeys;
use casper_types::{
    CLType, EntryPoint, EntryPointAccess, EntryPointType, EntryPoints, Parameter,
};

const DICT_NAME: &str = "anomalies";
const COUNT_KEY: &str = "anomaly_count";
const CONTRACT_KEY: &str = "anomaly_anchor_contract";
const ARG_ID: &str = "anomaly_id";
const ARG_KIND: &str = "kind";
const ARG_SEV: &str = "severity_bps";
const ARG_HASH: &str = "evidence_hash";

/// Public entry point: append one anomaly record and bump the counter.
#[no_mangle]
pub extern "C" fn record_anomaly() {
    let id: String = runtime::get_named_arg(ARG_ID);
    let kind: String = runtime::get_named_arg(ARG_KIND);
    let severity_bps: u32 = runtime::get_named_arg(ARG_SEV);
    let evidence_hash: String = runtime::get_named_arg(ARG_HASH);

    let dict_uref = runtime::get_key(DICT_NAME)
        .unwrap_or_revert()
        .into_uref()
        .unwrap_or_revert();

    let record = alloc::format!("{}|{}|{}", kind, severity_bps, evidence_hash);
    storage::dictionary_put(dict_uref, &id, record);

    let count_uref = runtime::get_key(COUNT_KEY)
        .unwrap_or_revert()
        .into_uref()
        .unwrap_or_revert();
    let current: u64 = storage::read(count_uref).unwrap_or_revert().unwrap_or(0);
    storage::write(count_uref, current + 1);
}

/// Installer: create storage, register the entry point, store the contract.
#[no_mangle]
pub extern "C" fn call() {
    let dict_uref = storage::new_dictionary(DICT_NAME).unwrap_or_revert();
    let count_uref = storage::new_uref(0u64);

    let mut named_keys = NamedKeys::new();
    named_keys.insert(String::from(DICT_NAME), dict_uref.into());
    named_keys.insert(String::from(COUNT_KEY), count_uref.into());

    let mut entry_points = EntryPoints::new();
    entry_points.add_entry_point(EntryPoint::new(
        "record_anomaly",
        vec![
            Parameter::new(ARG_ID, CLType::String),
            Parameter::new(ARG_KIND, CLType::String),
            Parameter::new(ARG_SEV, CLType::U32),
            Parameter::new(ARG_HASH, CLType::String),
        ],
        CLType::Unit,
        EntryPointAccess::Public,
        EntryPointType::Contract,
    ));

    let (contract_hash, _version) = storage::new_contract(
        entry_points,
        Some(named_keys),
        Some(String::from("anomaly_anchor_package")),
        Some(String::from("anomaly_anchor_access")),
    );
    runtime::put_key(CONTRACT_KEY, contract_hash.into());
}
