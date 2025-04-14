import logging
import pika as pk
from config import RABBITMQ_SERVER

class vnf():
    def __init__(self, vnf_id, queue_in, queue_out):
        logging.info("Starting VNF, the following attributes: id:%s  queues: %s %s",
                     vnf_id, queue_in, queue_out)
        self.vnf_id = vnf_id
        self.queue_in = queue_in
        self.queue_out = queue_out

        # Use RabbitMQ to communicate with VNFs
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # Start queues
        self.channel.queue_declare(queue_in)
        self.channel.queue_declare(queue_out)

    def treat_messages(self, ch, method, properties, body):
        """Function used to receive messages"""
        if body is None:
            return
        print(f"Received {body.decode()}")

        self.send_message(f"{body.decode()}->{self.vnf_id}")

    def send_message(self, payload):
        """Send a message in queue_out"""
        return self.channel.basic_publish(exchange="", routing_key=self.queue_out, body=payload)

    def cleanup_vnf(self):
        """Cleanup resources used from VNF"""
        self.channel.queue_delete(self.queue_in)
        self.channel.queue_delete(self.queue_out)
        self.connection.close()
