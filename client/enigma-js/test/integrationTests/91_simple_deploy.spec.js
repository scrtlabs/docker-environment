/* eslint-disable require-jsdoc */
import fs from 'fs';
import os from 'os';
import path from 'path';
import Web3 from 'web3';
import {Enigma, utils, eeConstants} from 'enigma-js/lib/enigma-js.node';
// import utils from 'enigma-js';
// import eeConstants from 'enigma-js';
import {EnigmaContractAddress, EnigmaTokenContractAddress, proxyAddress, ethNodeAddr} from './addressLoader';
import * as constants from './testConstants';
import cluster_sdk from '../../../cluster-sdk';


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// describe('Enigma tests', () => {
//     it('initializes', async () => {
//         await cluster_sdk.scaleWorkers({namespace: 'app',targetNum: 1});
//         sleep(1000);
//     });
// });

describe('Enigma tests', () => {
    let accounts;
    let web3;
    let enigma;
    let epochSize;
    it('initializes', () => {
        const provider = new Web3.providers.HttpProvider(ethNodeAddr);
        web3 = new Web3(provider);
        return web3.eth.getAccounts().then(async (result) => {
            accounts = result;
            await web3.eth.sendTransaction({to:"0x18A787C1e5fb92D7dFF1f920Ee740901Dc72BC1b", from:accounts[0], value:web3.utils.toWei("0.5", "ether")});
            await web3.eth.sendTransaction({to:"0x18A787C1e5fb92D7dFF1f920Ee740901Dc72BC1b", from:accounts[0], value:web3.utils.toWei("0.5", "ether")});
            await web3.eth.sendTransaction({to:"0x18A787C1e5fb92D7dFF1f920Ee740901Dc72BC1b", from:accounts[0], value:web3.utils.toWei("0.5", "ether")});
            await web3.eth.sendTransaction({to:"0x18A787C1e5fb92D7dFF1f920Ee740901Dc72BC1b", from:accounts[0], value:web3.utils.toWei("0.5", "ether")});
            await web3.eth.sendTransaction({to:"0x18A787C1e5fb92D7dFF1f920Ee740901Dc72BC1b", from:accounts[0], value:web3.utils.toWei("0.5", "ether")});

            enigma = new Enigma(
                web3,
                EnigmaContractAddress,
                EnigmaTokenContractAddress,
                proxyAddress,
                {
                    gas: 4712388,
                    gasPrice: 100000000000,
                    from: accounts[0],
                },
            );
            enigma.admin();
            enigma.setTaskKeyPair('cupcake');
            expect(Enigma.version()).toEqual('0.0.1');
        });
    });

    let task;
    const homedir = os.homedir();
    it('should deploy secret contract while restarting worker', async () => {
        // let net_status = await cluster_sdk.getStatus({namespace: 'app'});
        // extracts the number of the worker out of the status hashmap
        // let num_worker = '1';
        // Object.keys(net_status).forEach((k) => { if (k.startsWith('worker')) num_worker = k[k.length - 1]});
        // console.log('num worker is ' + num_worker);
        let scTaskFn = 'construct()';
        let scTaskArgs = '';
        let scTaskGasLimit = 1000000;
        let scTaskGasPx = utils.toGrains(1);
        let preCode;
        try {
            preCode = fs.readFileSync(path.resolve(__dirname, 'secretContracts/calculator.wasm'));
        } catch(e) {
            console.log('Error:', e.stack);
        }
        await sleep(5000);
        task = await new Promise((resolve, reject) => {
            enigma.deploySecretContract(scTaskFn, scTaskArgs, scTaskGasLimit, scTaskGasPx, accounts[0], preCode)
                .on(eeConstants.DEPLOY_SECRET_CONTRACT_RESULT, (receipt) => resolve(receipt))
                .on(eeConstants.ERROR, (error) => reject(error));
        });
    }, 110000);

    it('should get the failed task receipt', async () => {
        do {
            await sleep(1000);
            console.log("the task is " + JSON.stringify(task) + '\n');
            task = await enigma.getTaskRecordStatus(task);
            process.stdout.write('Waiting. Current Task Status is '+task.ethStatus+'\r');
        } while (task.ethStatus != 2);
        expect(task.ethStatus).toEqual(2);
        process.stdout.write('Completed. Final Task Status is '+task.ethStatus+'\n');
    }, constants.TIMEOUT_COMPUTE_LONG);

    // it('should fail to verify deployed contract', async () => {
    //     const result = await enigma.admin.isDeployed(task.scAddr);
    //     expect(result).toEqual(false);
    // });
    //
    // it('should fail to get deployed contract bytecode hash', async () => {
    //     const result = await enigma.admin.getCodeHash(task.scAddr);
    //     expect(result).toBeFalsy;
    // });
});
