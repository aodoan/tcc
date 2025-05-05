"""
This file contain the implementantion of a IDS (Intrusion Detection System)

"""
import logging
import threading
import time
import pika as pk
import ids.configuration as ids_config
from ids.oad import OAD

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

        self.db_file = open(ids_config.db_file, "a+")


    def start_monitoring(self):
        """Start monitoring with the driver"""
        # First, create a thread to receive messages
        get_packets_thread = threading.Thread(target=self.__get_packets)
        get_packets_thread.daemon = True
        get_packets_thread.start()
        
        # Call start_driver (blocking)
        self.driver.start_driver()

    def __get_packets(self):
        """Internal thread used to fetch packages from the driver recv queue"""
        while True:
            packet = self.driver.get_packet()
            if packet:
                self.process(packet)
            else:
                time.sleep(ids_config.sleep_time)

    def store_data(self, packet):
        """ Store a data obtained from the OAD for future referecing
        """
        self.db_file.write(packet)
        self.db_file.flush()
        pass

    def alarm(self):
        """ Notify OAD that an Intrusion ocurred
        """
        self.driver.send_message("ATTACK!!!")
        pass

    def process(self, package):
        """ Process a package and determine wheter or not is an intrusion
        """
        # First step, is to store data
        self.store_data(package)
        pass

    def configuration(self):
        """Handle internal configuration"""
        pass


if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/ids.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    driver = OAD() 
    ids = IDS(driver)
    ids.start_monitoring()
