import argparse
import pandas as pd
from sklearn.model_selection import train_test_split
import os
import csv

def main():
    parser = argparse.ArgumentParser(description='Split a CSV into training and testing datasets.')
    parser.add_argument('-i', '--input', required=True, help='Path to input CSV file')
    parser.add_argument('-p', '--percentage', type=float, required=True, help='Percentage of training data (0-100)')
    args = parser.parse_args()

    input_path = args.input
    train_pct = args.percentage / 100.0

    # Load data
    with open(input_path, 'r') as f:
        has_header = csv.Sniffer().has_header(f.read(6000))
        f.seek(0)
        df = pd.read_csv(f, header=0 if has_header else None)

    if has_header:
        df.columns = range(df.shape[1])  # Remove column names

    # Split dataset
    train_df, test_df = train_test_split(df, train_size=train_pct, shuffle=True)

    # Output file paths
    base_dir = os.path.dirname(input_path)
    base_name = os.path.basename(input_path)
    train_pct_fmt = int(train_pct * 100)
    test_pct_fmt = 100 - train_pct_fmt

    train_path = os.path.join(base_dir, f"training{train_pct_fmt}_{base_name}")
    test_path = os.path.join(base_dir, f"testing{test_pct_fmt}_{base_name}")

    # Save CSVs without headers and without index
    train_df.to_csv(train_path, index=False, header=False)
    test_df.to_csv(test_path, index=False, header=False)

if __name__ == "__main__":
    main()
