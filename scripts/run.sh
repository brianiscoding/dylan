#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="config.json"
URL=$(jq -r '.url' $CONFIG_FILE)
VERBOSE=$(jq -r '.verbose' $CONFIG_FILE)
TIMEOUT=15s

# getting sudo permissions upfront
sudo pfctl -sr &>/dev/null

# create pf config
python3 ./configure_pf.py $CONFIG_FILE
# run packet filter for chaos
sudo pfctl -f pf.conf &>/dev/null

# run the main script with timeout
start_ms=$(gdate +%s%3N)
# if timeout $TIMEOUT python3 ./client.py $URL $([ $VERBOSE = "true" ] && echo "--verbose") > output.log 2>&1; then
if timeout $TIMEOUT python3 ./client.py $URL $([ $VERBOSE = "true" ] && echo "--verbose"); then
  # milliseconds
  end_ms=$(gdate +%s%3N)
  duration_ms=$((end_ms - start_ms))
  # display pf status
  sudo pfctl -vvsr 2>/dev/null
  # log time
  echo "SUCCESS: ${duration_ms}ms"
else
  if [ $? -eq 124 ]; then
    echo "ERROR: timeout >${TIMEOUT}"
  else
    echo "ERROR: unknown"
    ./scripts/clean.sh
    exit 1
  fi
fi

# clean up pf rules
./scripts/clean.sh