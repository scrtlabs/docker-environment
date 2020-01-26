#! /usr/bin/env node

const Web3 = require('web3');

function main() {
    const web3 = new Web3();
    web3.eth.accounts.wallet.create(1);
    let account = web3.eth.accounts.wallet[0];
    console.log(account.address, account.privateKey);
}

main();
