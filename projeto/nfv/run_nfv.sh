#!/bin/bash

gateway_port=30126
fwd_port=40125
set -e

VENV_PY="$(pwd)/venv/bin/python"

# Start each in its own process group (using setsid)
setsid $VENV_PY -m mano.vim &
PID1=$!

setsid $VENV_PY -m mano.vnfm &
PID2=$!

setsid $VENV_PY -m ids.ids &
PID3=$!

setsid $VENV_PY -m gateway.gateway &
PID4=$!

setsid $VENV_PY -m mano.nfvo &
PID5=$!

setsid $VENV_PY -m gateway.forwarder &
PID6=$!

cleanup() {
    echo "Stopping all processes..."

    # Kill process groups (-PGID)
    kill -- -$PID1
    kill -- -$PID2
    sudo kill -- -$PID3
    kill -- -$PID4
    kill -- -$PID5
    kill -- -$PID6

    wait
    echo "All processes stopped."
    exit 0
}

trap cleanup SIGINT
wait
