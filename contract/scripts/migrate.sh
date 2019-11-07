#!/usr/bin/env bash

python3 scripts/contract_startup.py
# Wait until ganache-cli started and listens on port 9545.
while [ -z "$(ss -tln | grep 9545)" ]; do
  echo 'Waiting for ganache-cli to start ...'
  sleep 2
done
echo 'ganache-cli started.'

echo 'Running deployment...'
truffle migrate --network develop
echo 'Done deployment!'

echo 'Serving enigmacontract address and enigmatoken address'
python3 scripts/contract_server.py