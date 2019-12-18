#!/usr/bin/env bash

set -e

./scripts/configure.py

echo 'Running deployment...'
ENV=$(echo "$ENIGMA_ENV" | tr '[:upper:]' '[:lower:]')
npx truffle migrate --network $ENV
echo 'Done deployment!'

node ./operator/src/server.js
