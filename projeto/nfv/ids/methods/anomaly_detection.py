"""
This file contain implementations of multiple anomaly detection techniques
"""
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import logging
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import RandomOverSampler
import ids.internal_configuration as config
from ids.methods.read_data import ReadData

class AnomalyDetector:
    def __init__(self, method="iforest", dataset_name="kdd99"):
        """Initializes the detector
            Args:
            @param method: Chooses the method used for anomaly detection
        """
        logging.info("[ANML] Starting module.")
        self.catalog = {
            "knn" : {
                "learning": "supervised",
                "description": "K-nearest neighbor"
            },
            "kmeans" : {
                "learning" : "unsupervised",
                "description": "K-means"
            },
            "iforest" : {
                "learning" : "unsupervised",
                "description": "Isolation Forest"
            },
            "osvm": {
                "learning" : "unsupervised",
                "description": "One-class Support Vector Machine"
            },
            "lof": {
                "learning" : "unsupervised",
                "description": "Local Outlier Factor"
            }
        }
        self.__methods = self.catalog.keys()
        self.set_method(method)
        if dataset_name in config.datasets_names:
            self.dataset_name = dataset_name
            self.dataset_columns = list(config.features[self.dataset_name]["features"].keys())
        else:
            raise Warning(f"Dataset {dataset_name} not in the IDS configuration file.")
        logging.info("Using dataset: %s", dataset_name)
        self.load_dataset()

        self.is_trained = False
        self.model = None

    def load_dataset(self):
        """
            Loads the dataset into the detector
            
            Args:
                fpath(str): Path of the dataset.
        """
        filename = config.features[self.dataset_name]["filename"]
        #sorry for the next line... did not want to hardcoded the path...
        folder = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        fpath = os.path.join(folder, "datasets", self.dataset_name, filename)
        # Reads and preprocess the data according to ids.configuration
        self.data = ReadData(dataset_name=self.dataset_name,
                             fpath=fpath)

        # Now, scale the dataset and get three datasets as well as the encoder
        self.train, self.x_train, self.y_train, self.scaler, self.label_encoders = self.data.scale_dataset()

        

    def set_method(self, method):
        if method not in self.__methods:
            raise ValueError("Method {} is not valid.".format(method))
        logging.info("[ANML] Using %s as a method.", method)
        self.method = method

    def train_model(self, split = False, test_size = 1.0, argument=None):
        """
        Train a model given a method and dataset
        
        Args:
            split(bool): False if the whole dataset should be used for training.
            test_size(float): The percentage of the test_size. 0.0 <= x < 1.0.
        """
        logging.info("[ANML] Started learning.") 
        if split is True:
            if 0 <= test_size <= 1.0:
                self.train, self.test_df = train_test_split(self.train, test_size=test_size)
            else:
                raise RuntimeError("Value for test_size is invalid")

        if self.method == "iforest":
            if argument is None:
                model = IsolationForest(max_samples=100, random_state=0)
            else:
                model = IsolationForest(max_samples=argument["max_samples"], random_state=argument["random_state"])

            model.fit(self.x_train)
        elif self.method == "osvm":
            if argument is None:
                split_sample = 2
            else:
                split_sample = argument["split_sample"]
            sample_size = len(self.x_train) // split_sample
            indices = np.random.choice(len(self.x_train), size=sample_size, replace=False)
            x_sample = self.x_train[indices]

            if argument is None:
                model = OneClassSVM(gamma='auto', kernel="rbf")
            else:
                model = OneClassSVM(gamma=argument["gamma"], kernel=argument["kernel"])
            model.fit(x_sample)

        elif self.method == "lof":
            if argument is None:
                model = LocalOutlierFactor(n_neighbors=10, novelty=True, contamination=0.45)
            else:
                model = LocalOutlierFactor(n_neighbors=argument["n_neighbors"],
                                           novelty=True, 
                                           contamination=argument["contamination"])

            model.fit(self.x_train)
        else:
            raise RuntimeError("Unsupported method selected.")
        self.model = model
        print("Training done")
        logging.info("[ANML] Learning finished.")
        self.is_trained = True


            
    def predict_instance(self, raw_line: str):
        """
        Predicts the label of a new instance from a CSV-like string.

        Args:
            raw_line (str): A single comma-separated line like from a CSV row.

        Returns:
            tuple: (predicted_label, actual_label or None)
        """
        if not self.is_trained:
            raise RuntimeError("Model is not trained yet.")

        # Column names must match dataset structure
        # Parse string to values
        values = raw_line.strip().split(',')
        if len(values) != len(self.dataset_columns):
            raise ValueError("Input string does not have the correct number of features.")

        # Build Series
        sample = pd.Series(values, index=self.dataset_columns)

        # Store label and drop it
        actual_label = sample["label"].strip('.')
        print(actual_label, config.features[self.dataset_name]["normal_traffic"])
        if actual_label == config.features[self.dataset_name]["normal_traffic"]:
        #if actual_label == "normal":
            actual_label = 1
        else:
            actual_label = -1

        sample = sample.drop("label")

        # Apply LabelEncoders to symbolic columns
        for col, le in self.label_encoders.items():
            if col in sample:
                sample[col] = le.transform([sample[col]])[0]

        # Convert to numeric and scale
        sample = sample.astype(float)
        sample_scaled = self.scaler.transform([sample.values])

        # Predict
        predicted = self.model.predict(sample_scaled)
        return predicted[0], actual_label

 
        

# anml = AnomalyDetector()
# anml.train_model()
# line = "0,tcp,http,SF,159,4087,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,5,5,0.00,0.00,0.00,0.00,1.00,0.00,0.00,11,79,1.00,0.00,0.09,0.04,0.00,0.00,0.00,0.00,normal."
# print(anml.predict_instance(line))

# line = "0,icmp,ecr_i,SF,1032,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,510,510,0.00,0.00,0.00,0.00,1.00,0.00,0.00,255,255,1.00,0.00,1.00,0.00,0.00,0.00,0.00,0.00,smurf."
# print(anml.predict_instance(line))