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

export ETHEREUM_PEER='contract'  # TODO grab this from configuration.
export CONTRACT_ADDRESS_HOST='contract'  # used by the salad client library TODO grab this from configuration.

./scripts/migrate.sh
node ./operator/src/server.js
