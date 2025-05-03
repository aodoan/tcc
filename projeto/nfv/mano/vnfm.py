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
from config import RABBITMQ_SERVER, VNFM_EXCHANGE, VIM_EXCHANGE, GATEWAY_EXCHANGE
import json
import time

@dataclass
class VNFDescriptor:
    """Describe all the necessary information of a VNF"""
    vnf_id: str # VNF unique ID
    queue_in: str # VNF input queue
    queue_out: str # VNF output queue
    nf_type: Optional[str] = None # Name of the Network Function
    sw_image: Optional[str] = None # Path to the image

print("HERE!")
class VNFM():
    def __init__(self):
        """Init VNFM
            @param channel: RabbitMQ channel connection"""
        
        logging.info("Starting module.")
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # Start to listen to exchange
        self.channel.exchange_declare(exchange=VNFM_EXCHANGE,
                                      exchange_type='fanout', durable=True)

        result = self.channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(queue=queue_name, exchange=VNFM_EXCHANGE)
        self.channel.basic_consume(queue=queue_name,
                                   on_message_callback=self.treat_vnfm,
                                   auto_ack=True)

        logging.debug("VNFM listening in queue: %s", queue_name)

        self.__vnf_id = [] # Store all the current instantiated VNFs identifier
        self.sfc_list = []
        logging.info("Module started.")
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
        if action == "create_vnf":
            self.create_vnf(vnf_id=msg["vnf_id"],
                            qin=msg["qin"], qout=msg["qout"])
        elif action == "delete_vnf":
            self.delete_vnf(sfc_id=msg["sfc_id"])
        elif action == "heartbeat":
            self.channel.basic_publish(exchange="", routing_key=msg["rqueue"],
                                       body="ok")
        else:
            logging.info("Unknown message type!")

    def create_vnf(self, vnf_id, qin, qout):
        # first, check to see if the id is duplicated
        if vnf_id not in self.__vnf_id:
            message = {
                "action" : "create_vnf",
                "vnf_id" : vnf_id,
                "qin" : qin,
                "qout": qout
            }

            self.channel.basic_publish(exchange=VNFM_EXCHANGE,
                                       body=json.dumps(message), routing_key="")
            return

        logging.error("VNF ID duplicate found. There is an error in NFVO!")

    def delete_vnf(self, vnf_id):
        if vnf_id in self.__vnf_id:
            msg = json.dumps({
                "action":"stop",
                "vnf_id": vnf_id
            })
            self.channel.basic_publish(
                exchange=VIM_EXCHANGE,
                body=msg,
                routing_key="")
            logging.info("Stopping %s", vnf_id)
            return

if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/vnfm.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | [VNFM] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    vnfm = VNFM()


