#!/usr/bin/env node

const Web3 = require('web3');
const {Enigma} = require('enigma-js/node');

const main = async () => {
    const provider = new Web3.providers.WebsocketProvider(`ws://${process.env.ETH_HOST}:${process.env.ETH_PORT}`);
    const web3 = new Web3(provider);

    let enigmaHost = process.env.ENIGMA_HOST || 'localhost';
    let enigmaPort = process.env.ENIGMA_PORT || '3333';
    const enigmaAddr = process.env.ENIGMA_CONTRACT_ADDRESS;
    const enigmaTokenAddr = process.env.ENIGMA_TOKEN_CONTRACT_ADDRESS;

    const enigma = new Enigma(
        web3,
        enigmaAddr,
        enigmaTokenAddr,
        'http://' + enigmaHost + ':' + enigmaPort,
        {
            gas: 4712388,
            from: web3.eth.accounts[0],
        },
    );

    const enigmaContract = enigma.enigmaContract;
    console.log('Waiting for an epoch to pass after the contract deployment');
    await new Promise(resolve =>
        enigmaContract.events.WorkersParameterized({})
            .once('data', data => {
                console.log(`got data ${data}`);
                resolve(data);
            })
    );
    console.log('an epoch has passed');
};

main().catch(err => { console.log(err); process.exit(1) });
