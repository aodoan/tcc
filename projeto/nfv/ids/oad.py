"""
This file contain implementation of a Orchestrator Abstraction Driver (OAD)
"""
import pika as pk
import logging
import queue
from config import RABBITMQ_SERVER, NFVIN_EXCHANGE, IDS_EXCHANGE, VNFM_EXCHANGE

class OAD:
    """
    The OAD is responsible for creating an abastraction driver to allow the IDS to operate in multiple
    NFV-scenarios.

    In this implementation, connects to NFV using RabbitMQ and offer functions to
    the IDS to send and receive messages.
    """
    def __init__(self):
        """Init OAD internal structure"""
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
                                   on_message_callback=self.treat_message_from_mano,
                                   auto_ack=True)
        
        # Set up queue
        self.packet_queue = queue.Queue()


    def __sniff(self, ch, method, properties, body):
        """Upon sniffing a packet, add to recv queue"""
        logging.info("Sniffed: %s", body.decode())
        # Upon receiving a message, place in recv queue
        self.packet_queue.put(body.decode())

    def get_packet(self):
        """Used by the IDS to get packets, if the recv queue is empty, None is returned"""
        try:
            return self.packet_queue.get_nowait()
        except queue.Empty:
            return None

    def start_driver(self):
        """Starts the driver (blocking)"""
        self.channel.start_consuming()

    def treat_message_from_mano(self, ch, method, properties, body):
        """Treats commands received from the operator"""
        logging.info("Got from MANO: %s", body.decode())

    def __publish(self, message):
        """Internal publish message function"""
        self.channel.basic_publish(exchange=VNFM_EXCHANGE, routing_key="",
                                   body=message)
    
    def send_message(self, message):
        """Function to allow the IDS to send a message to the operator"""
        self.connection.add_callback_threadsafe(
            lambda: self.__publish(message)
        )


