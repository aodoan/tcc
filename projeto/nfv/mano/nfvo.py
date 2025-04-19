"""
NFVO is responsible for:
1 - Resource orchestration to multiple VIMs
2 - Lifecycle management of SFCs

1 - The orchestration of NFVI resources across multiple VIMs, 
fulfilling the Resource Orchestration functions 
(Not considered in this project)

2 - The lifecycle management of Network Services
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


