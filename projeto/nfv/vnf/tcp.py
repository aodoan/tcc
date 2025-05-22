import logging
import socket
import threading
import time
import sys
import pika as pk
from config import RABBITMQ_SERVER, VNF_CONTROL_EXCHANGE
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | VNFM | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class VNF:
    def __init__(self, vnf_id, sfc_id, listen_host, listen_port, send_host, send_port, network_function):
        self.vnf_id = vnf_id
        self.sfc_id = sfc_id
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.send_host = send_host
        self.send_port = send_port
        self.network_function = network_function
        self.send_socket = None
        self.send_lock = threading.Lock()

        if not callable(network_function):
            logging.error("Invalid argument for network_function: Not callable.")
            raise TypeError("Invalid argument")

        # Setup RabbitMQ
        self.control_conn = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.control_channel = self.control_conn.channel()
        self.control_channel.exchange_declare(exchange=VNF_CONTROL_EXCHANGE, exchange_type='fanout')
        result = self.control_channel.queue_declare(queue=f"control-{vnf_id}", exclusive=True)
        queue_name = result.method.queue
        self.control_channel.queue_bind(exchange=VNF_CONTROL_EXCHANGE, queue=queue_name)
        self.control_channel.basic_consume(queue=queue_name,
                                           on_message_callback=self.treat_control_messages,
                                           auto_ack=True)

        # Setup TCP listener
        self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener_socket.bind((self.listen_host, self.listen_port))
        self.listener_socket.listen(5)

        self.running = True

        logging.info("Started VNF id:%s listening on %s:%s sending to %s:%s",
                     vnf_id, listen_host, listen_port, send_host, send_port)

        self.start_service()

    def start_service(self):
        threading.Thread(target=self.control_channel.start_consuming, daemon=True).start()
        threading.Thread(target=self.tcp_accept_loop, daemon=True).start()
        threading.Thread(target=self.maintain_send_socket, daemon=True).start()

    def tcp_accept_loop(self):
        logging.info("TCP listener started on %s:%s", self.listen_host, self.listen_port)
        while self.running:
            try:
                client_sock, addr = self.listener_socket.accept()
                logging.info("Accepted TCP connection from %s", addr)
                threading.Thread(target=self.handle_tcp_client, args=(client_sock,), daemon=True).start()
            except Exception as e:
                logging.error("TCP accept error: %s", e)

    def handle_tcp_client(self, client_sock):
        with client_sock:
            while self.running:
                try:
                    data = client_sock.recv(4096)
                    if not data:
                        break
                    self.treat_messages(data)
                except Exception as e:
                    logging.error("Error in TCP client handler: %s", e)
                    break

    def treat_messages(self, body):
        if not body:
            return
        try:
            return_val = self.network_function(body)
            if return_val:
                logging.info("Forwarding message: %s", return_val)
                self.send_message(return_val)
            else:
                logging.info("Network Function did not forward any message")
        except Exception as e:
            logging.error("NF internal error: %s", e)

    def maintain_send_socket(self):
        """Persistent socket handler to send messages."""
        while self.running:
            if self.send_socket is None:
                try:
                    logging.info("Trying to connect to %s:%s...", self.send_host, self.send_port)
                    sock = socket.create_connection((self.send_host, self.send_port), timeout=5)
                    self.send_socket = sock
                    logging.info("Connected to %s:%s", self.send_host, self.send_port)
                except Exception as e:
                    logging.warning("Send socket connection failed: %s. Retrying in 1 second...", e)
                    time.sleep(1)
            else:
                time.sleep(1)

    def send_message(self, payload):
        with self.send_lock:
            if self.send_socket:
                try:
                    self.send_socket.sendall(payload)
                except Exception as e:
                    logging.error("Error sending message: %s", e)
                    self.send_socket.close()
                    self.send_socket = None
            else:
                logging.warning("Send socket is not connected. Dropping message.")

    def treat_control_messages(self, ch, method, properties, body):
        logging.info("Received CONTROL MESSAGE: %s", body.decode())

    def stop_service(self):
        logging.info("Stopping VNF service...")
        self.running = False
        try:
            if self.send_socket:
                self.send_socket.close()
            self.listener_socket.close()
            self.control_channel.stop_consuming()
            self.control_conn.close()
        except Exception as e:
            logging.error("Error during cleanup: %s", e)

# Example NF
def my_network_function(data):
    return data

vnf_id = None
sfc_id = None
listen_host = None
listen_port = None
send_host = None
send_port = None

try:
    vnf_id = sys.argv[1]
    sfc_id = sys.argv[2]
    listen_host = sys.argv[3]
    listen_port = int(sys.argv[4])
    send_host = sys.argv[5]
    send_port = int(sys.argv[6])
except:
    print("Incorret usage")
    print(f"python3 {sys.argv[0]} vnf_id sfc_id listen_host listen_port send_host send_port")
    sys.exit(0)

# Instantiate
vnf = VNF(
    vnf_id=vnf_id,
    sfc_id=sfc_id,
    listen_host=listen_host,
    listen_port=listen_port,
    send_host=send_host,
    send_port=send_port,
    network_function=my_network_function
)

# Keep main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    vnf.stop_service()
    logging.info("VNF stopped gracefully.")
