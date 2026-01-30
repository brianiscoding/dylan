#!/usr/bin/env bash

sudo pfctl -F all &> /dev/null
sudo pfctl -sr 2> /dev/null
rm -f pf.conf