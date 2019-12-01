/* eslint-disable require-jsdoc */
import fs from 'fs';
import os from 'os';
import path from 'path';
import Web3 from 'web3';
import { Enigma, utils, eeConstants } from 'enigma-js/lib/enigma-js.node';
// import utils from 'enigma-js';
// import eeConstants from 'enigma-js';
import { EnigmaContractAddress, EnigmaTokenContractAddress, proxyAddress, ethNodeAddr } from './addressLoader';
import * as constants from './testConstants';


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

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
            await web3.eth.sendTransaction({ to: accounts[1], from: accounts[0], value: web3.utils.toWei("0.5", "ether") });
            await web3.eth.sendTransaction({ to: accounts[1], from: accounts[0], value: web3.utils.toWei("0.5", "ether") });
            await web3.eth.sendTransaction({ to: accounts[1], from: accounts[0], value: web3.utils.toWei("0.5", "ether") });
            await web3.eth.sendTransaction({ to: accounts[1], from: accounts[0], value: web3.utils.toWei("0.5", "ether") });
            await web3.eth.sendTransaction({ to: accounts[1], from: accounts[0], value: web3.utils.toWei("0.5", "ether") });
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
    }, constants.TIMEOUT_COMPUTE_LONG);

    let scTask;
    let task;
    const homedir = os.homedir();
    it('should deploy secret contract', async () => {
        let scTaskFn = 'construct()';
        let scTaskArgs = '';
        let scTaskGasLimit = 1000000;
        let scTaskGasPx = utils.toGrains(1);
        let preCode;
        try {
            preCode = fs.readFileSync(path.resolve(__dirname, 'secretContracts/factorization.wasm'));
        } catch (e) {
            console.log('Error:', e.stack);
        }
        scTask = await new Promise((resolve, reject) => {
            enigma.deploySecretContract(scTaskFn, scTaskArgs, scTaskGasLimit, scTaskGasPx, accounts[0], preCode)
                .on(eeConstants.DEPLOY_SECRET_CONTRACT_RESULT, (receipt) => resolve(receipt))
                .on(eeConstants.ERROR, (error) => reject(error));
        });
        console.log('Deployed factorization with address:', scTask.scAddr);
        fs.writeFile(path.join(homedir, '.enigma', 'addr-factorization.txt'), scTask.scAddr, { flag: 'w', encoding: 'utf8' }, function (err) {
            if (err) {
                return console.log(err);
            }
        });
    }, constants.TIMEOUT_DEPLOY);

    it('should get the confirmed deploy contract task', async () => {
        do {
            await sleep(1000);
            scTask = await enigma.getTaskRecordStatus(scTask);
            process.stdout.write('Waiting. Current Task Status is ' + scTask.ethStatus + '\r');
        } while (scTask.ethStatus != 2);
        expect(scTask.ethStatus).toEqual(2);
        process.stdout.write('Completed. Final Task Status is ' + scTask.ethStatus + '\n');
    }, constants.TIMEOUT_DEPLOY);

    it('should verify deployed contract', async () => {
        const result = await enigma.admin.isDeployed(scTask.scAddr);
        expect(result).toEqual(true);
    });

    it('should get deployed contract bytecode hash', async () => {
        const result = await enigma.admin.getCodeHash(scTask.scAddr);
        expect(result).toBeTruthy();
        console.log('Deployed contract bytecode hash is: ' + result);
    });
});
