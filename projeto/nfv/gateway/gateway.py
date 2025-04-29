"""
Implementation of NFV-GATEWAY
Listens to clients in a TCP port, and foward the packets to SFCs
"""
import sys
import socket
import threading
import logging
import json
import random
import pika as pk
from config import RABBITMQ_SERVER, GATEWAY_PORT, GATEWAY_EXCHANGE, NFVIN_EXCHANGE

logging.basicConfig(
    filename="logs/gateway.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def rabbit_connect():
    connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
    return connection.channel()

class Gateway:
    def __init__(self, host='0.0.0.0', port=GATEWAY_PORT):
        # Start to listen to exchange
        # self.channel.exchange_declare(exchange=GATEWAY_EXCHANGE,
                                      # exchange_type='fanout')

        # result = self.channel.queue_declare(queue="", exclusive=True)
        # queue_name = result.method.queue
        # self.channel.queue_bind(queue=queue_name, exchange=GATEWAY_EXCHANGE)
        # self.channel.basic_consume(queue=queue_name,
                                   # on_message_callback=self.treat_gateway,
                                   # auto_ack=True)
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
        self.channel = rabbit_connect()
        self.channel.exchange_declare(exchange=GATEWAY_EXCHANGE,
                                      exchange_type='fanout')

        result = self.channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(queue=queue_name, exchange=GATEWAY_EXCHANGE)
        self.channel.basic_consume(queue=queue_name,
                                   on_message_callback=self.treat_gateway,
                                   auto_ack=True)
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
            if self.sfc_catalog[msg["sfc_id"]]:
                del self.sfc_catalog[msg["sfc_id"]]
        elif action == "heartbeat":
            print("got heartbeat")
            self.channel.basic_publish(exchange="", routing_key=msg["rqueue"],
                                       body="ok")
        else:
            logging.info("Command unknown!")



    def handle_client(self, client_socket, addr):
        # RabbitMQ support one connection per thread
        # Create internal channel just for publishing messages
        internal_channel = rabbit_connect() 
        with client_socket:
            while True:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    # 
                    print(f"{addr} {data.decode(errors='ignore')}")
                    sfc_id = self.route_to_sfc(data, addr)
                    if sfc_id is not None:
                        print(self.sfc_catalog[sfc_id])
                        queue_in = self.sfc_catalog[sfc_id]["queue_in"]

                        # Forward data to SFC
                        internal_channel.basic_publish(exchange="", routing_key=queue_in,
                                                       body=data)

                        # Forward data to Sniffer
                        internal_channel.basic_publish(exchange=NFVIN_EXCHANGE, routing_key="",
                                                   body=data)

                except ConnectionResetError:
                    logging.info("Client %s disconnected.", addr)
                    del self.clients[addr]
                    break
    
    def route_to_sfc(self, data, addr):
        """Given a package and an address, route to the correct SFC
            @param data: Package received
            @param addr: Client address
            @returns a valid SFC ID, returns None if an error ocurred"""
        # TODO: add some logic here, by now, returning a random sfc_id
        try:
            sfc_id = random.choice(list(self.sfc_catalog.keys()))
        except:
            return None
        return sfc_id
                    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.channel.stop_consuming()
        print("[INFO] Gateway stopped.")

# Example usage:
if __name__ == "__main__":
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    ap = Gateway(port=port)
    try:
        ap.start()
    except KeyboardInterrupt:
        ap.stop()
