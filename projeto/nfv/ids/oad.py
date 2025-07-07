"""
This file contain implementation of a Orchestrator Abstraction Driver (OAD)

The OAD is a adapter between multiple different technologies of NFV
with the IDS. The OAD is responsible for all the communication and
the collection of packets to be analyzed by the System.
"""
import pika as pk
import logging
import json
import queue
import socket
import threading
from config import RABBITMQ_SERVER, IDS_EXCHANGE, VNFM_EXCHANGE
from config import IDS_IP, IDS_PORT

class OAD:
    """
    The OAD is responsible for creating an abastraction driver to allow the IDS to operate in multiple
    NFV-scenarios.

    In this implementation, connects to NFV using RabbitMQ and offer functions to
    the IDS to send and receive messages.
    """
    def __init__(self):
        """Init OAD internal structure"""
        logging.info("[OAD] Starting Module.")
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # 1 - Set up sniffer
        self.sniffing = False
        self.setup_sniffer(IDS_IP, IDS_PORT)

        # 2 - Set up OAD (IDS interface)
        self.channel.exchange_declare(exchange=IDS_EXCHANGE,
                                      exchange_type='fanout', durable=True)
        result = self.channel.queue_declare(queue="", exclusive=True)
        oad_queue = result.method.queue
        self.channel.queue_bind(queue=oad_queue, exchange=IDS_EXCHANGE)
        self.channel.basic_consume(queue=oad_queue,
                                   on_message_callback=self.treat_message_from_mano,
                                   auto_ack=True)
        
        # Set up queue
        self.packet_queue = queue.Queue()
        self.control_queue = queue.Queue()
        logging.info("Setup done.")

    def setup_sniffer(self, address, port):
        self.sniffing = True
        sniffer_thread = threading.Thread(target=self._sniffer_loop, args=(address, port), daemon=True)
        sniffer_thread.start()

    def _sniffer_loop(self, address, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.bind((address, port))
            server_socket.listen(1)
            print(f"[Sniffer] Listening for connection on {address}:{port}...")

            while self.sniffing:
                self.client_socket, client_address = server_socket.accept()
                print(f"[Sniffer] Connected to {client_address}")
                try:
                    self._handle_client(self.client_socket)
                except Exception as e:
                    print(f"[Sniffer] Error: {e}")
                finally:
                    self.client_socket.close()
                    self.client_socket = None

    def _handle_client(self, sock):
        while self.sniffing:
            data = sock.recv(1024)
            if not data:
                print("[Sniffer] Client disconnected.")
                break
            #message = data.decode('utf-8').strip()
            self.packet_queue.put(data)


    def __sniff(self, ch, method, properties, body):
        """Upon sniffing a packet, add to recv queue"""
        try:
            logging.debug("Sniffed: %s", body.decode())
            # Upon receiving a message, place in recv queue
            print("got message")
            self.packet_queue.put(body.decode())
        except:
            pass

    def get_packet(self):
        """Used by the IDS to get packets, if the recv queue is empty, None is returned"""
        try:
            return self.packet_queue.get_nowait()
        except queue.Empty:
            return None

    def get_control_packet(self):
        """Used by the IDS to get control packets, if the recv queue is empty, None is returned"""
        try:
            return self.control_queue.get_nowait()
        except queue.Empty:
            return None

    def start_driver(self):
        """Starts the driver (blocking)"""
        self.channel.start_consuming()

    def treat_message_from_mano(self, ch, method, properties, body):
        """Treats commands received from the operator"""
        logging.info("[OAD] Got from MANO: %s", body.decode())
        msg = None
        try:
            msg = json.loads(body.decode())
        except:
            return
        action = msg["action"]
        if action == "heartbeat":
            logging.info("Received heartbeat. Returning to queue: %s", msg["rqueue"])
            self.channel.basic_publish(exchange="", routing_key=msg["rqueue"],
                                       body="ok")
        elif action != "":
            logging.info("Received IDS config change.")
            self.control_queue.put(msg)
        else:
            logging.error("Unknow message")

        

    def __publish(self, message, control=False, queue=""):
        """Internal publish message function"""
        exchange = VNFM_EXCHANGE
        routing_key = queue
        if control is True:
            exchange = ""
        
        self.channel.basic_publish(exchange=exchange, routing_key=routing_key,
                                body=message)

    
    def send_message(self, message, control=False, queue=""):
        """Function to allow the IDS to send a message to the operator"""
        self.connection.add_callback_threadsafe(
            lambda: self.__publish(message, control=control, queue=queue)
        )


