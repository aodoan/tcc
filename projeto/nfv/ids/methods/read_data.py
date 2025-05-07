import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder ,StandardScaler
from imblearn.over_sampling import RandomOverSampler
#from ids.configuration import datasets, features
import ids.configuration as configuration
# dataset
csv_file = "./ids/datasets/kdd99/kddcup.data_10_percent_corrected"  # change to your actual file name

feature_names = [
    "duration", "protocol_type", "service", "flag", "src_bytes", "dst_bytes", "land",
    "wrong_fragment", "urgent", "hot", "num_failed_logins", "logged_in", "num_compromised",
    "root_shell", "su_attempted", "num_root", "num_file_creations", "num_shells",
    "num_accessfiles", "num_outbound_cmds", "is_host_login", "is_guest_login", "count",
    "srv_count", "serror_rate", "srv_serror_rate", "rerror_rate", "srv_rerror_rate",
    "same_srv_rate", "diff_srv_rate", "srv_diff_host_rate", "dst_host_count",
    "dst_host_srv_count", "dst_host_same_srv_rate", "dst_host_diff_srv_rate",
    "dst_host_same_src_port_rate", "dst_host_srv_diff_host_rate", "dst_host_serror_rate",
    "dst_host_srv_serror_rate", "dst_host_rerror_rate", "dst_host_srv_rerror_rate",
    "category"
]

# # Load CSV into a DataFrame
# df = pd.read_csv(csv_file, names=feature_names)

# print(df.shape)
# df.drop_duplicates(keep='first', inplace=True)
# print(df.shape)
# print(df.columns)

class ReadData:
    def __init__(self, dataset, fpath):
        """Reads a dataset and prepare to train
            @param dataset: Name of the dataset. (e.g. kdd99, ...)
            @param fpath: Path of the .csv file.
        """
        if dataset not in configuration.datasets:
            raise RuntimeError("%s is not a valid dataset. Please see the manual", dataset)
        
        if os.path.isfile(fpath) is False:
            raise RuntimeError("%s is not a file. Aborting", fpath)

        self.features_dict = configuration.features[dataset]["features"]
        self.features = list(self.features_dict.keys())
        
        # Read file and store in a dataframe
        self.df = pd.read_csv(fpath, names=self.features)

        # Apply the transformations according to IDS Configuration
        if configuration.drop_duplicates:
            self.df.drop_duplicates(keep='first', inplace=True) 
        if configuration.convert_labels:
            normal_label = configuration.features[dataset]["normal_traffic"]
            self.df["label"] = (self.df["label"] != normal_label).astype(int)

    def shape(self):
        if self.df is not None:
            return self.df.shape

    def get_df(self):
        if self.df is not None:
            return self.df
        
    def scale_dataset(self):
        df_copy = self.df.copy()

        # Encode symbolic columns with LabelEncoder
        symbolic_cols = df_copy.select_dtypes(include=["object"]).columns.tolist()
        for col in symbolic_cols:
            le = LabelEncoder()
            df_copy[col] = le.fit_transform(df_copy[col])
    
        # Separate features and label
        X = df_copy.iloc[:, :-1].values
        y = df_copy.iloc[:, -1].values

        # Scale features
        scaler = StandardScaler()
        X = scaler.fit_transform(X)

        # Oversample if needed
        if configuration.oversample:
            ros = RandomOverSampler()
            X, y = ros.fit_resample(X, y)

        # Combine X and y for output
        data = np.hstack((X, np.reshape(y, (-1, 1))))
        return data, X, y

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



    
a = ReadData("kdd99", csv_file)
df = a.get_df()

train, x_train, y_train = a.scale_dataset()
