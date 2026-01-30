#!/usr/bin/env bash

set -euo pipefail

CONFIG_FILE="config.json"

URL=$(jq -r '.url' $CONFIG_FILE)

for loss_out in $(seq -f "%.2f" 0 05 2); do
for loss_in in $(seq -f "%.2f" 0 1 1); do
    jq ".loss_in = $loss_in | .loss_out = $loss_out" $CONFIG_FILE > tmp.json && mv tmp.json $CONFIG_FILE
    python3 ./configure.py $CONFIG_FILE
    sudo pfctl -f pf.conf &> /dev/null

    start=$(gdate +%s%N)
    if timeout 5s python3 client.py "$URL"; then
        end=$(gdate +%s%N)
        duration=$(( (end - start)/10000000 ))  # centiseconds
        echo "$loss_in $loss_out ${duration} cs"
    else
        if [ $? -eq 124 ]; then
            echo "$loss_in $loss_out >5s"
        else
            echo "$loss_in $loss_out error"
        fi
    fi

    # cleanup
    sudo pfctl -F all &> /dev/null
done
done

rm -f pf.conf
rm -f tmp.json

# 00 00 161 cs
# 10 00 237 cs
# 20 00 431 cs
# 30 00 463 cs

# 00 05 161 cs
# 10 05 206 cs
# 20 05 474 cs
# 30 05 >5s

# 00 10 183 cs
# 10 10 210 cs
# 20 10 >5s
# 30 10 >5s

# 00 15 251 cs
# 10 15 430 cs
# 20 15 224 cs

# 00 20 401 cs
# 10 20 262 cs
# 20 20 >5s