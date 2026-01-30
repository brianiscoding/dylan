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

URL=$(jq -r '.url' $CONFIG_FILE)
VERBOSE=$(jq -r '.verbose' $CONFIG_FILE)

start=$(gdate +%s%N)
if timeout 15s python3 ./client.py $URL $([ $VERBOSE = "true" ] && echo "--verbose"); then
    end=$(gdate +%s%N)
    duration=$(( (end - start)/1000000 ))  # milliseconds
    sudo pfctl -vvsr 2> /dev/null # logs
    echo "SUCCESS: ${duration} ms"
else
    if [ $? -eq 124 ]; then
        echo "ERROR: timeout 10s"
    else
        echo "ERROR: unknown"
    fi
fi

./scripts/clean.sh