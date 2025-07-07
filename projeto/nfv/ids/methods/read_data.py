"""
This file implements the ReadData class, which is responsible for 
reading datasets_name and preprocessing them for anomaly detection analysis.
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, StandardScaler
from imblearn.over_sampling import RandomOverSampler
import ids.internal_configuration as internal_configuration

class ReadData:
    def __init__(self, dataset_name, fpath):
        """
        Reads and preprocesses a dataset.

        Args:
            dataset_name (str): Name of the dataset (e.g., "kdd99").
            fpath (str): Path to the .csv file.
        """
        if dataset_name not in internal_configuration.datasets_names:
            raise RuntimeError(f"{dataset_name} is not a valid dataset_name. Please see the manual.")

        if not os.path.isfile(fpath):
            raise RuntimeError(f"{fpath} is not a file. Aborting.")

        self.features_dict = internal_configuration.features[dataset_name]["features"]
        self.features = list(self.features_dict.keys())
        print(self.features)
        
        # Read file and store in a dataframe
        self.df = pd.read_csv(fpath, names=self.features)

        # Apply the transformations according to IDS Configuration
        if internal_configuration.drop_duplicates:
            self.df.drop_duplicates(keep='first', inplace=True) 
        if internal_configuration.convert_labels:
            normal_label = internal_configuration.features[dataset_name]["normal_traffic"]
            self.df["label"] = (self.df["label"] != normal_label).astype(int)

    def shape(self):
        if self.df is not None:
            return self.df.shape

    def get_df(self):
        if self.df is not None:
            return self.df
        
    from sklearn.preprocessing import LabelEncoder, StandardScaler

    def scale_dataset(self):
        """Prepare the dataset and return encoders and scaler"""
        df_copy = self.df.copy()

        # Encode symbolic columns
        symbolic_cols = df_copy.select_dtypes(include=["object"]).columns.tolist()
        label_encoders = {}
        for col in symbolic_cols:
            le = LabelEncoder()
            df_copy[col] = le.fit_transform(df_copy[col])
            label_encoders[col] = le

        # Separate features and label
        X = df_copy.iloc[:, :-1].values
        y = df_copy.iloc[:, -1].values

        # Scale features
        scaler = StandardScaler()
        X = scaler.fit_transform(X)

        # Oversample if needed
        if internal_configuration.oversample:
            ros = RandomOverSampler()
            X, y = ros.fit_resample(X, y)

        # Combine X and y for output
        data = np.hstack((X, np.reshape(y, (-1, 1))))

        return data, X, y, scaler, label_encoders


    def split_dataset(df, train_frac=0.6, valid_frac=0.2, random_state=None):
        """Shuffle and split a DataFrame into train, validation, and test sets."""
        if train_frac + valid_frac >= 1.0:
            raise ValueError("Train + Validation fraction must be less than 1.0")

        df_shuffled = df.sample(frac=1, random_state=random_state).reset_index(drop=True)
        train_end = int(train_frac * len(df))
        valid_end = int((train_frac + valid_frac) * len(df))

        train = df_shuffled.iloc[:train_end]
        valid = df_shuffled.iloc[train_end:valid_end]
        test = df_shuffled.iloc[valid_end:]

        return train, valid, test


