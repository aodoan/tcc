#!/bin/bash

gateway_port=30125

# Exit immediately if any command fails (optional safety)
set -e

# 1. Activate the virtual environment
source ./venv/bin/activate

python3 -m mano.vim &
PID1=$!
python3 -m mano.vnfm &
PID2=$!
python3 -m ids.ids &
PID3=$!
python3 -m gateway.gateway $gateway_port &
PID4=$!
echo Gateway in TCP port: $gateway_port
# Function to kill everything on CTRL+C
cleanup() {
    echo "Stopping all processes..."
    kill $PID1 $PID2 $PID3 $PID4
    wait
    echo "All processes stopped."
    exit 0
}

# Trap CTRL+C (SIGINT) and call cleanup
trap cleanup SIGINT

# Wait for all scripts to finish
wait

