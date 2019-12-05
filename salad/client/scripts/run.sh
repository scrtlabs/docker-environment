#!/usr/bin/env bash

set -e

export OPERATOR_HOST='salad_operator'
export CONTRACT_ADDRESS_HOST='contract'

sed -i -e 's/ETH_HOST=localhost/ETH_HOST=contract/g' .env
sed -i -e 's/ENIGMA_HOST=localhost/ENIGMA_HOST=worker/g' .env
sed -i -e 's/ENIGMA_PORT=3333/ENIGMA_PORT=3346/g' .env
sed -i -e 's/MONGO_HOST=localhost/MONGO_HOST=mongo/g' .env
sed -i -e 's/OPERATOR_HOST=localhost/OPERATOR_HOST=salad_operator/g' .env

./scripts/wait_for_network.sh
./scripts/fetch_enigma_contract_addresses.sh

echo 'You may start running tests.'

# Just do nothing forever, so that the container doesn't stop running
cat
