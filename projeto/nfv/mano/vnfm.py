"""
The VNF Manager (VNFM) is responsible for the lifecycle management 
of VNF instances as described in clause 4.3. Each VNF
instance is assumed to have an associated VNF Manager

In this example, all VNFs istantiaded are handled by the vnfm
"""
import os
import random
import string
import logging
import pika as pk
from dataclasses import dataclass
from typing import Optional
from sfc.sfc import SFC
from vnf.vnf import VNF
from config import RABBITMQ_SERVER, VNFM_EXCHANGE, VIM_EXCHANGE
import json
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
@dataclass
class VNFDescriptor:
    """Describe all the necessary information of a VNF"""
    vnf_id: str # VNF unique ID
    queue_in: str # VNF input queue
    queue_out: str # VNF output queue
    nf_type: Optional[str] = None # Name of the Network Function
    sw_image: Optional[str] = None # Path to the image

class VNFM():
    def __init__(self):
        """Init VNFM
            @param channel: RabbitMQ channel connection"""
        
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # Start to listen to exchange
        self.channel.exchange_declare(exchange=VNFM_EXCHANGE,
                                      exchange_type='fanout')
        result = self.channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(queue=queue_name, exchange=VNFM_EXCHANGE)
        self.channel.basic_consume(queue=queue_name,
                                   on_message_callback=self.treat_vnfm,
                                   auto_ack=True)

        logging.info("Listening to controls in %s", queue_name)

        self.__vnf_id = [] # Store all the current instantiated VNFs identifier
        self.sfc_list = []
        self.channel.start_consuming()
    
    def treat_vnfm(self, ch, method, properties, body):
        logging.debug("VNFM received command %s", body.decode())

        # parse msg to json
        msg = None
        try:
            msg = json.loads(body.decode())
        except:
            logging.error("Could not parse message.")
            return

        action = msg["action"]
        if action == "create_node":
            self.instantiate_sfc(sfc_id=msg["sfc_id"],
                                 types=[],
                                 n=msg["sfc_size"])
        elif action == "delete_node":
            self.cleanup_sfc(sfc_id=msg["sfc_id"])
        else:
            logging.info("Unknown message type!")



    def instantiate_sfc(self, sfc_id, types, n):
        """ Creates a SFC
            @param sfc_id: Unique SFC identifier
            @param types: Specify each VNF
            @param n: Number of VNFs instantiate"""
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
                "action" : "start",
                "vnf_id" : vnf.vnf_id,
                "sfc_id" : sfc_id,
                "qin" : vnf.queue_in,
                "qout": vnf.queue_out
            }
            self.channel.basic_publish(exchange=VIM_EXCHANGE, body=json.dumps(message), routing_key="")

        logging.info("SFC created by VNFM. Endpoints %s %s",
                     queues[0], queues[-1])
        # for vnf in vnfs:
            # cont = self.vim.start_container(f"python ./instance.py {vnf.vnf_id} {sfc_id} {vnf.queue_in} {vnf.queue_out}", vnf_id=vnf.vnf_id)
            # cont.start()
        return _sfc

    def cleanup_sfc(self, sfc_id):
        for idx, (stored_id, sfc) in enumerate(self.sfc_list):
            if stored_id == sfc_id:
                # Stop the containers
                for vnf in sfc.vnfs:
                    msg = json.dumps({
                        "action":"stop",
                        "vnf_id": vnf.vnf_id
                    })
                    self.channel.basic_publish(
                        exchange=VIM_EXCHANGE,
                        body=msg,
                        routing_key="")
                    logging.info("Stopping %s", vnf.vnf_id)
                # Clean RabbitMQ queues
                for queue in sfc.queues:
                    self.channel.queue_delete(queue)
                del self.sfc_list[idx]
                break
    

    
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

a = VNFM()

# Example 
# connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
# channel = connection.channel()
# vnfm = VNFM(channel=channel)

# sfc = vnfm.instantiate_sfc("sfc-5", [], 3)
# qin, qout = sfc.endpoints()
# print(f"Queue in: {qin}, queue out: {qout}")
# while True:
    # inp = input("Digite q para sair")
    # if inp == "q":
        # break

# vnfm.cleanup_sfc("sfc-5")

