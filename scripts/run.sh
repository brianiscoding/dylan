#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="config.json"

# Check for nghttp2 installation
if ! command -v nghttp >/dev/null 2>&1; then
    if ! command -v brew >/dev/null 2>&1; then
        exit 1
    fi
    brew install nghttp2
fi
# update configs
python3 ./configure.py $CONFIG_FILE

sudo pfctl -f pf.conf &> /dev/null
python3 ./client.py $CONFIG_FILE

# logs
sudo pfctl -vvsr 2> /dev/null

./scripts/clean.sh