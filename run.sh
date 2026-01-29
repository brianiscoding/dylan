#!/usr/bin/env bash

set -euo pipefail

if ! command -v nghttp >/dev/null 2>&1; then
    if ! command -v brew >/dev/null 2>&1; then
        exit 1
    fi
    brew install nghttp2
fi

python3 ./configure.py
sudo pfctl -f pf.conf &> /dev/null
python3 ./run.py
sudo pfctl -vvsr 2> /dev/null
sudo pfctl -F all &> /dev/null
sudo pfctl -sr 2> /dev/null