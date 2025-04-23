"""
Implementation of NFV-GATEWAY
Listens to clients in a TCP port, and foward the packets to SFCs
"""

import socket
import threading
import logging
import json
import pika as pk
from config import RABBITMQ_SERVER, GATEWAY_PORT, GATEWAY_EXCHANGE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class Gateway:
    def __init__(self, host='0.0.0.0', port=GATEWAY_PORT):
        # Connect to RabbitMq
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # Start to listen to exchange
        self.channel.exchange_declare(exchange=GATEWAY_EXCHANGE,
                                      exchange_type='fanout')

        result = self.channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(queue=queue_name, exchange=GATEWAY_EXCHANGE)
        self.channel.basic_consume(queue=queue_name,
                                   on_message_callback=self.treat_gateway,
                                   auto_ack=True)
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = {}
        self.sfc_catalog = {} # Store all the current instantiated SFCs

    def start(self):
        # Start consuming RabbitMq queues
        threading.Thread(target=self.start_rabbitmq, args=(), daemon=True).start()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.running = True
        logging.info(f"[INFO] Gateway listening on {self.host}:{self.port}")

        while self.running:
            client_socket, addr = self.server_socket.accept()
            self.clients[addr] = client_socket
            logging.info(f"[INFO] Client {addr} connected")
            threading.Thread(target=self.handle_client, args=(client_socket, addr), daemon=True).start()

    def start_rabbitmq(self):
        logging.info("Started listening to RabbitMQ queues")
        self.channel.start_consuming()

    def treat_gateway(self, ch, method, properties, body):
        print(f"received message! {body.decode()}")
        msg = None
        try:
            msg = json.loads(body.decode())
        except:
            return
        
        action = msg["action"]
        if action == "sfc-creation":
            self.sfc_catalog[msg["sfc_id"]] = msg["sfc"]
        elif action == "sfc-delete":
            logging.info("SFC %s deleted.", )
            if self.sfc_catalog[msg[sfc_id"]]:
                del self.sfc_catalog[msg["sfc_id"]]
        else:
            logging.info("Command unknown!")



    def handle_client(self, client_socket, addr):
        print(self.clients)
        with client_socket:
            while True:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    print(f"{addr} {data.decode(errors='ignore')}")
                except ConnectionResetError:
                    logging.info("Client %s disconnected.", addr)
                    del self.clients[addr]
                    break
                    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.channel.stop_consuming()
        print("[INFO] Gateway stopped.")

# Example usage:
if __name__ == "__main__":
    ap = Gateway()
    try:
        ap.start()
    except KeyboardInterrupt:
        ap.stop()
