#!/bin/bash

# Dataset to send
DATASET_NAME="kdd99"
DATASET_FILE="../ml/testing30_kddcup.data_10_percent_corrected"
# Results folder
OUTPUT_DIR="results_official/${DATASET_NAME}"
P_VALUE=2
NUM_RUNS=100

# Loop over methods
for METHOD in iforest lof osvm; do
    python3 -m client.tester \
        -z "$DATASET_NAME" \
        -d "$DATASET_FILE" \
        -o "$OUTPUT_DIR" \
        -p "$P_VALUE" \
        -n "$NUM_RUNS" \
        -m "$METHOD"
done
