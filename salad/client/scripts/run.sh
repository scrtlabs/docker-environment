#!/usr/bin/env bash

set -e


# TODO modify the docker file for salad client to install the python libraries.
./scripts/configure.py

echo 'You may start running tests.'

# Just do nothing forever, so that the container doesn't stop running
cat
