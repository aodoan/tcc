"""
Implementation of NFV-GATEWAY
Listens to clients in a TCP port, and foward the packets to SFCs
"""
import sys
import socket
import threading
import logging
import json
import time
import random
import pika as pk
from queue import Queue
from config import RABBITMQ_SERVER, GATEWAY_PORT, GATEWAY_EXCHANGE, NFVIN_EXCHANGE
from config import DEFAULT_IN_PORT, IDS_IP, IDS_PORT

def rabbit_connect():
    connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
    return connection.channel()

class Gateway:
    def __init__(self, host='192.168.18.11', port=GATEWAY_PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.sniffing = False
        self.ids_socket = None
        self.connect_to_sniffer(address=IDS_IP, port=IDS_PORT)
        self.clients = {}
        self.connections = {}
        self.sfc_catalog = {} # Store all the current instantiated SFCs

    def start(self):
        # Start consuming RabbitMq queues
        threading.Thread(target=self.start_rabbitmq, args=(), daemon=True).start()

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.running = True
        logging.info("Gateway listening on %s:%s", self.host, self.port)

        while self.running:
            client_socket, addr = self.server_socket.accept()
            self.clients[addr] = client_socket
            logging.info("Client %s connected.", addr)
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
        msg = None
        try:
            msg = json.loads(body.decode())
        except:
            return
        
        action = msg["action"]
        if action == "sfc-creation":
            logging.info("SFC %s was created.", msg["sfc_id"])
            first_vnf = next(iter(msg["sfc"].items()))
            self.connect_to_vnf(vnf_id=first_vnf[0], addr=first_vnf[1])
            self.sfc_catalog[msg["sfc_id"]] = msg["sfc"]
        elif action == "sfc-delete":
            logging.info("SFC %s was deleted..", msg["sfc_id"])
            if self.sfc_catalog[msg["sfc_id"]]:
                del self.sfc_catalog[msg["sfc_id"]]
        elif action == "heartbeat":
            logging.debug("Heartbeat message received")
            self.channel.basic_publish(exchange="", routing_key=msg["rqueue"],
                                       body="ok")
        else:
            logging.info("Command unknown!")

    def connect_to_vnf(self, vnf_id, addr, max_attempts=60):
        """Connects to a VNF at the given address and stores the socket."""
        counter = 0
        while counter < max_attempts:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((addr, 2323))
                self.connections[vnf_id] = s
                logging.info("Connected to %s. Address: %s", vnf_id, addr)
                return
            except Exception as e:
                logging.error("Connection to %s at %s failed: %s. Trying again", vnf_id, addr, e)
            counter += 1
            time.sleep(1)
        logging.error("Max attempst at connect to %s", vnf_id)

    def send_to_vnf(self, vnf_id, msg):
        """Sends a message to the connected VNF."""
        if vnf_id not in self.connections:
            print(f"VNF {vnf_id} is not connected.")
            return
        try:
            self.connections[vnf_id].sendall(msg)
            print(f"Sent to {vnf_id}: {msg}")
        except Exception as e:
            print(f"Failed to send message to {vnf_id}: {e}")


    def handle_client(self, client_socket, addr):
        # RabbitMQ support one connection per thread
        # Create internal channel just for publishing messages
        with client_socket:
            while True:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    data.strip()
                    sfc_id = self.route_to_sfc(data, addr)
                    self.send_to_ids(data)
                    if sfc_id is not None:
                        logging.info("Sending data to vnf: %s", sfc_id)
                        self.send_to_vnf(sfc_id, data) 
                    else:
                        logging.warning("Got data, but no SFC is UP!")

                except ConnectionResetError:
                    logging.info("Client %s disconnected.", addr)
                    del self.clients[addr]
                    break

    def connect_to_sniffer(self, address, port):
        self.sniffing_thread = threading.Thread(target=self._connect_to_sniffer, args=(address, port), daemon=True)
        self.sniffing_thread.start()
    
    def _connect_to_sniffer(self, address, port):
        logging.info("Attempting to connected to IDS: %s", address)
        while not self.sniffing:
            try:
                self.ids_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.ids_socket.connect((address, port))
                self.sniffing = True
                logging.info("Connected to IDS: %s", address)
            except ConnectionRefusedError:
                time.sleep(1)


    def send_to_ids(self, message):
        if self.sniffing and self.ids_socket:
            try:
                self.ids_socket.sendall(message)
                logging.info("Sending message %s to IDS.", message)
            except Exception as e:
                logging.debug("An error ocurred while sending message to IDS. [%s]", e)
                self.connected = False
                self.ids_socket.close()
                self.ids_socket = None


    def route_to_sfc(self, data, addr):
        """Given a package and an address, route to the correct SFC
            @param data: Package received
            @param addr: Client address
            @returns a valid SFC ID, returns None if an error ocurred"""
        # TODO: add some logic here, by now, returning a random sfc_id
        try:
            sfc_id = random.choice(list(self.connections.keys()))
        except:
            return None
        return sfc_id
                    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        self.channel.stop_consuming()

# Example usage:
if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/gateway.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | BROKER | %(message)s",
        datefmt="%m-%d %H:%M:%S"
    )
    port = GATEWAY_PORT
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    ap = Gateway(port=port)
    import signal

    def shutdown(signum, frame):
        logging.info("Shutdown signal received (%s).", signum)
        print("QUITTING")
        ap.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        ap.start()
    except KeyboardInterrupt:
        ap.stop()
