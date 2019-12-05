#!/usr/bin/env bash

set -e

sed -i -e 's/ETH_HOST=localhost/ETH_HOST=contract/g' .env
sed -i -e 's/ENIGMA_HOST=localhost/ENIGMA_HOST=worker/g' .env
sed -i -e 's/ENIGMA_PORT=3333/ENIGMA_PORT=3346/g' .env
sed -i -e 's/MONGO_HOST=localhost/MONGO_HOST=mongo/g' .env

sed -i -e 's/ETH_HOST=localhost/ETH_HOST=contract/g' operator/.env
sed -i -e 's/ENIGMA_HOST=localhost/ENIGMA_HOST=worker/g' operator/.env
sed -i -e 's/MONGO_HOST=localhost/MONGO_HOST=mongo/g' operator/.env

if [[ "$SGX_MODE" == 'SW' ]]; then
    sed -i -e 's/SGX_MODE=HW/SGX_MODE=SW/g' .env
fi

# used by the salad client library
export ETH_HOST='contract'
export CONTRACT_ADDRESS_HOST='contract'

./scripts/wait_for_network.sh
./scripts/fetch_enigma_contract_addresses.sh

echo 'Running deployment...'
npx truffle migrate --network compose
echo 'Done deployment!'

node ./operator/src/server.js
