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

# If the operator's private key has not been supplied externally, provide it here.
if [[ -z "$OPERATOR_ETH_PRIVATE_KEY" ]]; then
    ACCOUNT_1="$(./scripts/create_account.js)"

    ADDRESS_1="$(echo "$ACCOUNT_1" | cut -d' ' -f1)"
    PRIVATE_KEY_1="$(echo "$ACCOUNT_1" | cut -d' ' -f2)"
    export OPERATOR_ETH_PRIVATE_KEY="$PRIVATE_KEY_1"

    ./scripts/distribute_funds.py "$ADDRESS_1"
fi

node ./operator/src/server.js -t
