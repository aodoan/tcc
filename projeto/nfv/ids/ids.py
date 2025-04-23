"""
This file contain the implementantion of a IDS (Intrusion Detection System)

"""
import logging
import os
import sys
import json
import pika as pk
from config import RABBITMQ_SERVER, NFVIN_EXCHANGE, IDS_EXCHANGE

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
    def __init__(self):
        """Initialize necessary structures and setup RabbitMQ communication"""
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # 1 - Set up sniffer
        self.channel.exchange_declare(exchange=NFVIN_EXCHANGE,
                                      exchange_type='fanout')
        result = self.channel.queue_declare(queue="", exclusive=True)
        sniff_queue = result.method.queue
        self.channel.queue_bind(queue=sniff_queue, exchange=NFVIN_EXCHANGE)
        self.channel.basic_consume(queue=sniff_queue,
                                   on_message_callback=self.__sniff,
                                   auto_ack=True)

        # 2 - Set up OAD (IDS interface)
        self.channel.exchange_declare(exchange=IDS_EXCHANGE,
                                      exchange_type='fanout')
        result = self.channel.queue_declare(queue="", exclusive=True)
        oad_queue = result.method.queue
        self.channel.queue_bind(queue=oad_queue, exchange=IDS_EXCHANGE)
        self.channel.basic_consume(queue=oad_queue,
                                   on_message_callback=self.__sniff,
                                   auto_ack=True)


    def __sniff(self, ch, method, properties, body):
        logging.info("Sniffed: %s", body.decode())
        # Upon sniffing a message, tries to convert to json
        self.oad_sniff(body.decode())

        # Store information
        # Call process_data

    def start_monitoring(self):
        pass

    def oad_sniff(self, packet):

        pass

    def store_data(self):
        """ Store a data obtained from the OAD for future referecing
        """
        pass

    def alarm(self):
        """ Notify OAD that an Intrusion ocurred
        """
        pass

    def process(self, package):
        """ Process a package and determine wheter or not is an intrusion
        """
        pass

    def configuration(self):
        """Handle internal configuration"""
        pass


ids = IDS()
ids.start_monitoring()
