import {EnigmaContract, EnigmaTokenContract} from "./contractLoader";

var EnigmaContractAddress = null;
var EnigmaTokenContractAddress = null;
var proxyAddress = null;
var ethNodeAddr = null;
if (typeof process.env.ENIGMA_ENV !== 'undefined' && process.env.ENIGMA_ENV !== 'LOCAL') {
  const fs = require('fs');
  const addrs = JSON.parse(fs.readFileSync('./test/contracts/addresses.json'));
  EnigmaContractAddress = addrs['contract'];
  EnigmaTokenContractAddress = addrs['token'];
  proxyAddress = addrs['proxy'];
  ethNodeAddr = addrs['eth_node'];
} else {
  EnigmaContractAddress = EnigmaContract.networks['4447'].address;
  EnigmaTokenContractAddress = EnigmaTokenContract.networks['4447'].address;
  proxyAddress = 'http://localhost:3346';
  ethNodeAddr = 'http://localhost:9545';
}

export {EnigmaContractAddress, EnigmaTokenContractAddress, proxyAddress, ethNodeAddr}
