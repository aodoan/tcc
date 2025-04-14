"""
NFVO is responsible for:
1 - Resource orchestration to multiple VIMs
2 - Lifecycle management of SFCs

(the resource part is abstracted)
"""
import os
import nfv
import random
import string
import logging
from config import RABBITMQ_SERVER
class nfvo():
    def __init__(self):
        logging.info("NFVO started")


