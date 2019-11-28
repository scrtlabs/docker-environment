#!/usr/bin/env bash

set -e

# Wait until ganache-cli is started and listens on port 9545.
while ! nc -z -w2 "$ETHEREUM_PEER" 9545; do  # -w2 means wait for 2 seconds
  echo 'Waiting for ganache-cli to start ...'
  sleep 2
done
echo 'ganache-cli started.'

# Wait until the contract address server is started and listens on port 8081.
while ! nc -z -w2 "$CONTRACT_ADDRESS_HOST" 8081; do  # -w2 means wait for 2 seconds
  echo 'Waiting for the contract address server to start ...'
  sleep 2
done
echo 'contract address server started.'

echo 'Running deployment...'
npx truffle migrate --network compose
echo 'Done deployment!'
