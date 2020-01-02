#! /usr/bin/env node
// This script is designed to run in the /scripts directory in `enigmampc/salad`.
//
// This script either fetches the Enigma and EnigmaToken smart contract addresses, and Salad smart and secret contract
// addresses from environment variables, and exits successfully, or it returns an exit code of 1 if it can't find
// the Salad contracts (it doesn't care as much about the Enigma contracts are those will always be in the environment).
//
// This is used to determine if the Salad contracts have already been deployed.
require('dotenv').config();
const log = console;
const {Store, CONFIG_COLLECTION} = require("@salad/operator/src/store");

async function main() {
    // If both are unset:
    if (!(process.env.SALAD_SMART_CONTRACT_ADDRESS && process.env.SALAD_SECRET_CONTRACT_ADDRESS)) {
        log.info('Salad smart and secret contracts are not pre-deployed.');
        process.exit(1);
    }

    log.info('Salad smart and secret contracts are pre-deployed. not performing migration');

    const store = new Store();
    try {
        await store.initAsync();
        // This is ok because we proceed to set all the keys in this collection, between runs of the operator.
        await store.truncate(CONFIG_COLLECTION);

        log.info(`inserting the following addresses to the operator's db: ${JSON.stringify({
            enigma_contract_address: process.env.ENIGMA_CONTRACT_ADDRESS,
            enigma_token_contract_address: process.env.ENIGMA_TOKEN_CONTRACT_ADDRESS,
            salad_smart_contract_address: process.env.SALAD_SMART_CONTRACT_ADDRESS,
            salad_secret_contract_address: process.env.SALAD_SECRET_CONTRACT_ADDRESS
        })}`);

        let enigmaAddr = process.env.ENIGMA_CONTRACT_ADDRESS;
        let enigmaTokenAddr = process.env.ENIGMA_TOKEN_CONTRACT_ADDRESS;
        await store.insertEnigmaContractAddresses(enigmaAddr, enigmaTokenAddr);
        await store.insertSmartContractAddress(process.env.SALAD_SMART_CONTRACT_ADDRESS);
        await store.insertSecretContractAddress(process.env.SALAD_SECRET_CONTRACT_ADDRESS);
    } catch (e) {
        log.error('Error while taking contract addresses from env', e);
    } finally {
        await store.closeAsync();
    }
}

main().catch(err => { log.error(err); process.exit(1) });
