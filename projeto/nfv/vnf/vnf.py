import logging
import pika as pk
from config import RABBITMQ_SERVER, VNF_CONTROL_EXCHANGE

class VNF():
    def __init__(self, vnf_id, sfc_id, queue_in, queue_out, network_function, create_queue = False):
        """Generic body of a VNF
            @param vnf_id: Given random identifier
            @param network_function: Implementation of a Network Function"""
        self.vnf_id = vnf_id
        self.sfc_id = sfc_id
        # The network function must have one argument and return the output
        # If the output is None, is assumed that no message needs to be forwarded
        self.network_function = network_function

        if hasattr(network_function, "__call__") is False:
            logging.error("Invalid argument for network_function: Not callable.")
            raise TypeError("Invalid argument")

        # Use RabbitMQ to communicate with VNFs
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        if create_queue is True:
            logging.warning("create_queue is active! This could lead to bugs.")
            self.channel.queue_declare(queue=queue_in)
            self.channel.queue_declare(queue=queue_out)

        self.queue_in = queue_in 
        self.queue_out = queue_out

        self.channel.basic_consume(queue=self.queue_in,
                                   auto_ack=True,
                                   on_message_callback=self.treat_messages)

        # Start control queue
        self.channel.exchange_declare(exchange=VNF_CONTROL_EXCHANGE,
                                      exchange_type='fanout')
        result = self.channel.queue_declare(queue=f"control-{vnf_id}", exclusive=True)  # Auto-delete queue
        queue_name = result.method.queue

        self.channel.queue_bind(exchange=VNF_CONTROL_EXCHANGE, queue=queue_name)

        self.channel.basic_consume(queue=queue_name,
                                   on_message_callback=self.treat_control_messages, 
                                   auto_ack=True)
        logging.info("Started VNF with the following attributes: id:%s  queues: in:%s out:%s",
                     vnf_id, self.queue_in, self.queue_out)
        self.start_service()

    def treat_messages(self, ch, method, properties, body):
        """Function used to receive messages"""
        if body is None:
            return
        try:
            return_val = self.network_function(body)

            if return_val is not None:
                logging.info("Sending message: %s", return_val)
                self.send_message(return_val)
            else:
                logging.info("Network Function did not forward any message")
        except Exception as e:
            logging.error("NF had an internal error: %s", {e})

        #self.send_message(f"{body.decode()}->{self.vnf_id}")

    def treat_control_messages(self, ch, method, properties, body):
        # TODO: treat VNF control messages
        print(f"received CONTROL MESSAGE! {body.decode()}")

    def send_message(self, payload):
        """Send a message in queue_out"""
        return self.channel.basic_publish(exchange="", routing_key=self.queue_out, body=payload)

    def cleanup_vnf(self):
        """Cleanup resources used from VNF"""
        self.channel.stop_consuming()
        self.channel.queue_delete(self.queue_in)
        self.channel.queue_delete(self.queue_out)
        self.connection.close()

    def get_queue_in(self):
        return self.queue_in
    
    def get_queue_out(self):
        return self.queue_out

    def start_service(self):
        try:
            logging.info("Starting service fr!")
            self.channel.start_consuming()
        except KeyboardInterrupt:
            # self.channel.stop_consuming()
            # self.cleanup_vnf()
            # logging.info("Finishing service")
            self.stop_service()
    
    def stop_service(self):
        self.channel.stop_consuming()
        self.cleanup_vnf()
        logging.info("Finishing service")

