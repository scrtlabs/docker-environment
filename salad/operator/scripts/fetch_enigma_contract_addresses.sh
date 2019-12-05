#!/usr/bin/env bash

set -e

echo 'Fetching Enigma smart contract addresses and saving them to the .env file'

ENIGMA_CONTRACT_ADDRESS="ENIGMA_CONTRACT_ADDRESS=$(
    curl --request GET -sL --url "http://$CONTRACT_ADDRESS_HOST:8081/contract/address?name=enigmacontract.txt"
)"
ENIGMA_TOKEN_CONTRACT_ADDRESS="ENIGMA_TOKEN_CONTRACT_ADDRESS=$(
    curl --request GET -sL --url "http://$CONTRACT_ADDRESS_HOST:8081/contract/address?name=enigmatokencontract.txt"
)"

echo 'Saving contract addresses to .env and operator/.env'

echo "$ENIGMA_CONTRACT_ADDRESS" >> .env
echo "$ENIGMA_CONTRACT_ADDRESS" >> operator/.env
echo "$ENIGMA_TOKEN_CONTRACT_ADDRESS" >> .env
echo "$ENIGMA_TOKEN_CONTRACT_ADDRESS" >> operator/.env
