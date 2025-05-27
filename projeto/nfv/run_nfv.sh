#!/bin/bash

gateway_port=30126
fwd_port=40125
set -e

# Get full path to venv's python
VENV_PY="$(pwd)/venv/bin/python"

# 1. Do NOT activate the virtualenv — just use its Python directly
$VENV_PY -m mano.vim &
PID1=$!

$VENV_PY -m mano.vnfm &
PID2=$!

$VENV_PY  -m ids.ids &  # IDS runs with root but using venv Python
PID3=$!

$VENV_PY -m gateway.gateway &
PID4=$!

$VENV_PY -m mano.nfvo &
PID5=$!

$VENV_PY -m gateway.forwarder &
PID6=$!

cleanup() {
    echo "Stopping all processes..."
    kill $PID1 $PID2 $PID4 $PID5 $PID6
    sudo kill $PID3
    wait
    echo "All processes stopped."
    exit 0
}

trap cleanup SIGINT
wait
