#!/usr/bin/env bash

set -e

./scripts/configure.py

if ! ./scripts/take_salad_contract_addresses_from_environment.js; then
    echo 'Running deployment...'
    ENV=$(echo "$ENIGMA_ENV" | tr '[:upper:]' '[:lower:]')
    npx truffle migrate --network $ENV
    ./scripts/wait_for_epoch_transition.js
    echo 'Done deployment!'
fi

node ./operator/src/server.js
