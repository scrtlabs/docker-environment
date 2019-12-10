/* eslint-disable require-jsdoc */
import fs from 'fs';
import os from 'os';
import path from 'path';
import Web3 from 'web3';
import Enigma from '../../src/Enigma';
import utils from '../../src/enigma-utils';
import * as eeConstants from '../../src/emitterConstants';
//import utils from '../../src/enigma-utils';
//import * as eeConstants from '../../src/emitterConstants';
import {EnigmaContractAddress, EnigmaTokenContractAddress, proxyAddress, ethNodeAddr} from './addressLoader';
import * as constants from './testConstants';


function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

describe('Enigma tests', () => {
    let accounts;
    let web3;
    let enigma1;
    let enigma2;
    let epochSize;
    it('initializes', () => {
        const provider = new Web3.providers.HttpProvider(ethNodeAddr);
        web3 = new Web3(provider);
        return web3.eth.getAccounts().then((result) => {
            accounts = result;
            enigma1 = new Enigma(
                web3,
                EnigmaContractAddress,
                EnigmaTokenContractAddress,
                "http://worker:3346",
                {
                    gas: 4712388,
                    gasPrice: 100000000000,
                    from: accounts[0],
                },
            );
            enigma2 = new Enigma(
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
            enigma1.admin();
            enigma1.setTaskKeyPair('cupcake', 'user1');
            enigma2.admin();
            enigma2.setTaskKeyPair('muffin', 'user2');
            expect(Enigma.version()).toEqual('0.0.1');
        });
    });

    const homedir = os.homedir();
    const factorAddr = fs.readFileSync(path.join(homedir, '.enigma', 'addr-factorization.txt'), 'utf-8');
    let task1;
    let task2;
    it('should execute compute task', async () => {
        let taskFn = 'find_number_of_prime_factors(uint64)';
        let taskArgs1 = [[8972, 'uint64']];
        let taskArgs2 = [[440, 'uint64']];
        let taskGasLimit = 100000;
        let taskGasPx = utils.toGrains(1);
        task1 = new Promise((resolve, reject) => {
            enigma1.computeTask(taskFn, taskArgs1, taskGasLimit, taskGasPx, accounts[0], factorAddr,1, 'user1')
                .on(eeConstants.SEND_TASK_INPUT_RESULT, (result) => resolve(result))
                .on(eeConstants.ERROR, (error) => reject(error));
        });

        task2 = new Promise((resolve, reject) => {
            enigma2.computeTask(taskFn, taskArgs2, taskGasLimit, taskGasPx, accounts[0], factorAddr, 1, 'user2')
                .on(eeConstants.SEND_TASK_INPUT_RESULT, (result) => resolve(result))
                .on(eeConstants.ERROR, (error) => reject(error));
        });
        task1 = await task1;
        task2 = await task2;
    }, constants.TIMEOUT_COMPUTE_LONG);

    it('should get the pending tasks', async () => {
        task1 = await enigma1.getTaskRecordStatus(task1);
        expect(task1.ethStatus).toEqual(1);
        task2 = await enigma2.getTaskRecordStatus(task2);
        expect(task2.ethStatus).toEqual(1);
    });

    it('should get the confirmed tasks', async () => {
        do {
            await sleep(1000);
            task1 = await enigma1.getTaskRecordStatus(task1);
            task2 = await enigma2.getTaskRecordStatus(task2);
            process.stdout.write('Waiting. Current Task1 Status is '+task1.ethStatus+'\r');
            process.stdout.write('Waiting. Current Task2 Status is '+task2.ethStatus+'\r');
        } while (task1.ethStatus != 2 || task2.ethStatus != 2);
        expect(task1.ethStatus).toEqual(2);
        expect(task2.ethStatus).toEqual(2);
        process.stdout.write('Completed. Final Task1 Status is '+task1.ethStatus+'\n');
        process.stdout.write('Completed. Final Task2 Status is '+task2.ethStatus+'\n');
    }, constants.TIMEOUT_COMPUTE_LONG);

    it('should get and validate the result1', async () => {
        task1 = await new Promise((resolve, reject) => {
            enigma1.getTaskResult(task1)
                .on(eeConstants.GET_TASK_RESULT_RESULT, (result) => resolve(result))
                .on(eeConstants.ERROR, (error) => reject(error));
        });
        expect(task1.engStatus).toEqual('SUCCESS');
        expect(task1.encryptedAbiEncodedOutputs).toBeTruthy();
        expect(task1.usedGas).toBeTruthy();
        expect(task1.workerTaskSig).toBeTruthy();
        task1 = await enigma1.decryptTaskResult(task1, 'user1');
        expect(parseInt(task1.decryptedOutput, 16)).toEqual(2);
    });

    it('should get and validate the result2', async () => {
        task2 = await new Promise((resolve, reject) => {
            enigma2.getTaskResult(task2)
                .on(eeConstants.GET_TASK_RESULT_RESULT, (result) => resolve(result))
                .on(eeConstants.ERROR, (error) => reject(error));
        });
        expect(task2.engStatus).toEqual('SUCCESS');
        expect(task2.encryptedAbiEncodedOutputs).toBeTruthy();
        expect(task2.usedGas).toBeTruthy();
        expect(task2.workerTaskSig).toBeTruthy();
        task2 = await enigma2.decryptTaskResult(task2, 'user2');
        expect(parseInt(task2.decryptedOutput, 16)).toEqual(5);
    });

});
