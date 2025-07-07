"""
    This file contain implementation of IDSConfig, responsible for handling
    the external configuration of the IDS
"""
import json
import os

class IDSConfig:
    def __init__(self, filename='config.json'):
        # The config file is expected to be in the same folder as
        # this script.
        cwd = os.path.dirname(os.path.abspath(__file__))
        self.filename = os.path.join(cwd, filename)
        self.config = {}
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.filename):
            with open(self.filename, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {}

    def get_config(self):
        return self.config

    def update(self, new_config):
        with open(self.filename, 'w') as f:
            json.dump(new_config, f, indent=4)


#cfg = IDSConfig()
#js = cfg.get_config()
#print(js["lof"])
#js["lof"] = {}
#cfg.update(js)