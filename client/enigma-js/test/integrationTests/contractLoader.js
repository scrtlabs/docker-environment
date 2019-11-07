import EnigmaTokenContract from '../contracts/EnigmaToken';
import SampleContract from '../contracts/Sample';
// import EnigmaContract from '../contracts/Enigma';

var EnigmaContract = null;
if (typeof process.env.SGX_MODE !== 'undefined' && process.env.SGX_MODE == 'SW') {
  EnigmaContract = require('../contracts/EnigmaSimulation');
} else {
  EnigmaContract = require('../contracts/Enigma');
}

export {EnigmaContract, EnigmaTokenContract, SampleContract}
