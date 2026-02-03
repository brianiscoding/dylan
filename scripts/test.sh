#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="config.json"
URL=$(jq -r '.url' $CONFIG_FILE)
TIMEOUT=10s

# getting sudo permissions upfront
sudo pfctl -sr &>/dev/null

echo $URL
echo "loss_in loss_out duration"
for loss_out in $(seq -f "%.2f" 0 .05 .2); do
  for loss_in in $(seq -f "%.2f" 0 .1 1); do
    # update config.json with loss rates
    jq ".loss_in = $loss_in | .loss_out = $loss_out" $CONFIG_FILE >tmp.json && mv tmp.json $CONFIG_FILE
    # create pf config
    python3 ./configure_pf.py $CONFIG_FILE
    # run packet filter for chaos
    sudo pfctl -f pf.conf &>/dev/null

    # run the main script with timeout
    start_ms=$(gdate +%s%3N)
    if timeout $TIMEOUT python3 client.py $URL; then
      # milliseconds
      end_ms=$(gdate +%s%3N)
      duration_ms=$((end_ms - start_ms))
      echo "$loss_in $loss_out ${duration_ms}ms"
    else
      if [ $? -eq 124 ]; then
        echo "$loss_in $loss_out >${TIMEOUT}"
        break
      else
        echo "$loss_in $loss_out error"
        ./scripts/clean.sh
        exit 1
      fi
    fi
  done
done

# clean up pf rules
./scripts/clean.sh

# https://www.toyota.com
# loss_in loss_out duration
# 0.00 0.00 546ms
# 0.10 0.00 947ms
# 0.20 0.00 748ms
# 0.30 0.00 806ms
# 0.40 0.00 1105ms
# 0.50 0.00 >10s
# 0.00 0.20 566ms
# 0.10 0.20 1703ms
# 0.20 0.20 >10s
# 0.00 0.40 >10s
# 0.00 0.60 >10s
# shfmt scripts/test.sh -i 2