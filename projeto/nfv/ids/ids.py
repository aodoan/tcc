"""
This file contain the implementantion of a IDS (Intrusion Detection System)

"""
import logging
import os
import sys
import json
import threading
import time
import pika as pk
from config import RABBITMQ_SERVER, NFVIN_EXCHANGE, IDS_EXCHANGE
from ids.oad import OAD

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class IDS:
    """
        Description of elements:

        OAD: Is responsible for the comunication between the IDS and the NFV
        Also, is reponsible for packaging sniffer

        Store Data: Is responsible for store all the data into a database

        Configuration: Contain the internal configuration of the IDS 
            - Can be changed by the NFVO trough the OAD module

        Reference Data: Internal structure of expected behaviours of entities (or known attacks)

        Processing: Is responsible to process incoming packets and according to the
        Configuration module + Reference Data, it decides whether is an intrusion or not 


        Alarm: Is responsible of notify OAD of intrusions detected by Processing module
    """
    def __init__(self, driver):
        """Initialize necessary structures and setup RabbitMQ communication"""
        self.driver = driver

    def start_monitoring(self):
        # First, create a thread to receive messages
        get_packets_thread = threading.Thread(target=self.__get_packets)
        get_packets_thread.daemon = True
        get_packets_thread.start()
        
        # Call start_driver (blocking)
        self.driver.start_driver()

    def __get_packets(self):
        while True:
            packet = self.driver.get_packet()
            if packet:
                self.process(packet)
            else:
                time.sleep(0.01)


    def store_data(self):
        """ Store a data obtained from the OAD for future referecing
        """
        pass

    def alarm(self):
        """ Notify OAD that an Intrusion ocurred
        """
        self.driver.send_message("ATTACK!!!")
        pass

    def process(self, package):
        """ Process a package and determine wheter or not is an intrusion
        """
        logging.info("[IDS] -> GOT A PACKET! %s", package)
        pass

    def configuration(self):
        """Handle internal configuration"""
        pass

driver = OAD() 
ids = IDS(driver)
ids.start_monitoring()
