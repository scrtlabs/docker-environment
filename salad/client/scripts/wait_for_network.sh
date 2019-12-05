#!/usr/bin/env bash

set -e

# Wait until the operator server is started and listens on port 8080.
while ! nc -z -w2 "$OPERATOR_HOST" 8080; do  # -w2 means wait for 2 seconds
  echo 'Waiting for the operator server to start at' "$OPERATOR_HOST"
  sleep 5
done
echo 'Operator server started.'
