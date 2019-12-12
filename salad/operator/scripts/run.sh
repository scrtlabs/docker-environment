#!/usr/bin/env bash

set -e

./scripts/configure.py

echo 'Running deployment...'
npx truffle migrate --network compose
echo 'Done deployment!'

node ./operator/src/server.js
