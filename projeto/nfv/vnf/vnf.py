import logging
import pika as pk
from config import RABBITMQ_SERVER

class VNF():
    def __init__(self, vnf_id, network_function):
        """Generic body of a VNF
            @param vnf_id: Given random identifier
            @param network_function: Implementation of a Network Function"""
        self.vnf_id = vnf_id
        # The network function must have one argument and return the output
        # If the output is None, is assumed that no message needs to be forwarded
        self.network_function = network_function

        if hasattr(network_function, "__call__") is False:
            logging.error("Invalid argument for network_function: Not callable.")
            raise TypeError("Invalid argument")

        # Use RabbitMQ to communicate with VNFs
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # If queue values are blank, a random queue name will be created
        result_in = self.channel.queue_declare("")
        self.queue_in = result_in.method.queue

        result_out = self.channel.queue_declare("")
        self.queue_out = result_out.method.queue

        self.channel.basic_consume(queue=self.queue_in,
                                   auto_ack=True,
                                   on_message_callback=self.treat_messages)

        logging.info("Started VNF with the following attributes: id:%s  queues: in:%s out:%s",
                     vnf_id, self.queue_in, self.queue_out)

    def treat_messages(self, ch, method, properties, body):
        """Function used to receive messages"""
        if body is None:
            return
        logging.debug("Received %s", body.decode())

        try:
            return_val = self.network_function(body.decode())

            if return_val is not None:
                logging.info("Sending message: %s", return_val)
                self.send_message(return_val)
            else:
                logging.info("Network Function did not forward any message")
        except Exception as e:
            logging.error("NF had an internal error: %s", {e})

        #self.send_message(f"{body.decode()}->{self.vnf_id}")

    def send_message(self, payload):
        """Send a message in queue_out"""
        return self.channel.basic_publish(exchange="", routing_key=self.queue_out, body=payload)

    def cleanup_vnf(self):
        """Cleanup resources used from VNF"""
        self.channel.queue_delete(self.queue_in)
        self.channel.queue_delete(self.queue_out)
        self.connection.close()

    def get_queue_in(self):
        return self.queue_in
    
    def get_queue_out(self):
        return self.queue_out

    def start_service(self):
        try:
            logging.info("Starting service")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.cleanup_vnf()
            logging.info("Finishing service")

