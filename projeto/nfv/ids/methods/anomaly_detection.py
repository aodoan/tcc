"""
This file contain implementations of multiple anomaly detection techniques
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import RandomOverSampler

class AnomalyDetector:
    def __init__(self, method="knn"):
        """Initializes the detector"""
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
            "svm": {
                "learning" : "unsupervised",
                "description": "One-class Support Vector Machine"
            }
        }
        self.__methods = self.catalog.keys()
        self.set_method(method)
        self.is_trained = False

    def set_method(self, method):
        if method not in self.__methods:
            raise ValueError("Method {} is not valid.".format(method))
        self.method = method

    def train(self, dataset, method=None):
        """Train a model given a method and dataset"""
        if self.is_trained:
            print("Already trained")

    def scale_dataset(self, dataframe, oversample=False):
        # Transform symbolic categories to dummy numbers
        symbolic_cols = dataframe.select_dtypes(include=["object"]).columns.tolist()
        df_encoded = pd.get_dummies(dataframe, columns=symbolic_cols)

        # Separate features and label
        X = df_encoded.iloc[:, :-1].values
        y = df_encoded.iloc[:, -1].values

        # Scale features
        scaler = StandardScaler()
        X = scaler.fit_transform(X)

        # Oversample if needed
        if oversample:
            ros = RandomOverSampler()
            X, y = ros.fit_resample(X, y)

        # Combine X and y for output
        data = np.hstack((X, np.reshape(y, (-1, 1))))

        return data, X, y


a = AnomalyDetector("randomstuff")
