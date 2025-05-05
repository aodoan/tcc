"""
NFVO is responsible for:
1 - Resource orchestration to multiple VIMs
2 - Lifecycle management of SFCs

1 - The orchestration of NFVI resources across multiple VIMs, 
fulfilling the Resource Orchestration functions 
(Not considered in this project)

2 - The lifecycle management of Network Services
"""
import os
import random
import string
import json
import pika as pk
import logging
from config import RABBITMQ_SERVER, NFVO_EXCHANGE, VIM_EXCHANGE, VNFM_EXCHANGE
from config import GATEWAY_EXCHANGE, FORWARDER_EXCHANGE
from mano.vnfm import VNFDescriptor
from sfc.sfc import SFC

class NFVO():
    def __init__(self):
        """Init NFVO 
            @param channel: RabbitMQ channel connection"""
        logging.info("Starting module.")
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()
        # Start to listen to exchange
        self.channel.exchange_declare(exchange=NFVO_EXCHANGE,
                                      exchange_type='fanout', durable=True)
        
        # declare queue to bind to own exchange
        result = self.channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(queue=queue_name, exchange=NFVO_EXCHANGE)
        self.channel.basic_consume(queue=queue_name,
                                   on_message_callback=self.treat_nfvo,
                                   auto_ack=True)
        
        logging.debug("NFVO listening in queue: %s", queue_name)
        self.sfc_list = []
        self.__vnf_id = [] # Store all the current instantiated VNFs identifier
        logging.info("Module started.")
        self.channel.start_consuming()

    def create_sfc(self, sfc_id, types, n):
        """ Creates a SFC
            @param sfc_id: Unique SFC identifier
            @param types: Specify each VNF type
            @param n: Number of VNFs"""
        # TODO: check if types are ok etc
        vnfs = []
        queues = []

        # First, generate n+1 queues
        for i in range(n + 1):
            # for each VNF, generate two queues
            result = self.channel.queue_declare("")
            queues.append(result.method.queue)

        # With all the queues generated, create the VNF descriptors
        for i in range(n):
            id = self.generate_id()
            vnfs.append(VNFDescriptor(id,
                                      queue_in=queues[i],
                                      queue_out=queues[i+1]))

        _sfc = SFC(vnfs, queues, channel=self.channel)
        self.sfc_list.append((sfc_id, _sfc))
        # Now, instantiate each VNF
        for vnf in vnfs:
            message = {
                "action" : "create_vnf",
                "vnf_id" : vnf.vnf_id,
                "sfc_id" : sfc_id,
                "qin" : vnf.queue_in,
                "qout": vnf.queue_out
            }
            self.channel.basic_publish(exchange=VNFM_EXCHANGE, body=json.dumps(message), routing_key="")
        
        # Upon creating a SFC, send message to Gateway
        msg = {
            "action" : "sfc-creation",
            "sfc_id" : sfc_id,
            "sfc" : {
                "queue_in" : queues[0],
                "queue_out": queues[-1]
            }
        }
        self.channel.basic_publish(exchange=GATEWAY_EXCHANGE,
                                   body=json.dumps(msg),
                                   routing_key="")

        self.channel.basic_publish(exchange=FORWARDER_EXCHANGE,
                                   body=json.dumps(msg),
                                   routing_key="")

        logging.info("SFC (%s) created by NFVO. Endpoints %s %s",
                     sfc_id, queues[0], queues[-1])

        return _sfc

    def cleanup_sfc(self, sfc_id):
        """ Clean all the structure of a SFC"""
        for idx, (stored_id, sfc) in enumerate(self.sfc_list):
            if stored_id == sfc_id:
                # Stop the containers
                for vnf in sfc.vnfs:
                    msg = json.dumps({
                        "action" : "delete_vnf",
                        "vnf_id": vnf.vnf_id
                    })
                    self.channel.basic_publish(
                        exchange=VNFM_EXCHANGE,
                        body=msg,
                        routing_key="")
                    logging.info("Stopping %s", vnf.vnf_id)
                # Clean RabbitMQ queues
                for queue in sfc.queues:
                    self.channel.queue_delete(queue)
                del self.sfc_list[idx]
                break
        msg = {
            "action" : "sfc-delete",
            "sfc_id" : sfc_id,
        }
        self.channel.basic_publish(exchange=GATEWAY_EXCHANGE,
                                   body=json.dumps(msg),
                                   routing_key="")
        self.channel.basic_publish(exchange=FORWARDER_EXCHANGE,
                                   body=json.dumps(msg),
                                   routing_key="")
    
    def treat_nfvo(self, ch, method, properties, body):
        logging.debug("NFVO received command %s", body.decode())

        # parse msg to json
        msg = None
        try:
            msg = json.loads(body.decode())
        except:
            logging.error("Could not parse message.")
            return

        action = msg["action"]
        if action == "create_sfc":
            self.create_sfc(sfc_id=msg["sfc_id"],
                                 types=[],
                                 n=msg["sfc_size"])
        elif action == "delete_sfc":
            self.cleanup_sfc(sfc_id=msg["sfc_id"])
        elif action == "list_sfc":
            self.list_sfc(msg["return_queue"])
        elif action == "heartbeat":
            self.channel.basic_publish(exchange="", routing_key=msg["rqueue"],
                                       body="ok")
        else:
            logging.info("Unknown message type: %s.", msg["action"])

    def list_sfc(self, ret_queue):
        """List all sfc"""
        sfcs = {}
        for (sfc_id, sfc) in self.sfc_list:
            vnf_dict = {}
            for vnf in sfc.vnfs:
                vnf_dict[vnf.vnf_id] = {
                    "queue_in": vnf.queue_in,
                    "queue_out": vnf.queue_out
                }
            sfcs[sfc_id] = {"sfc": vnf_dict}

        print(json.dumps(sfcs, indent=4))
        self.channel.basic_publish(exchange="", routing_key=ret_queue,
                                   body=json.dumps(sfcs, indent=4))
        return sfcs
    
    def generate_id(self, prefix="vnf-", length=6, max_attempts=20):
        """ Generate a random id and add to vnf_id list
            @param prefix: Constant string to be added before all generate Ids
            @param length: Number of random letters generated
            @param max_attempts: Number of attempts to create a unique id"""
        for i in range(max_attempts):
            id = prefix + ''.join(random.choices(string.ascii_letters, k=length))
            if id not in self.__vnf_id:
                self.__vnf_id.append(id)
                return id
        logging.error("Could not generate a unique ID")
        return None

if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/nfvo.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | NFVO | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    nfvo = NFVO()


