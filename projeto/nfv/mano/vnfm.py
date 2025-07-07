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

def wait_for_message(channel, queue, timeout=None):
    start_time = time.time()
    while True:
        method_frame, header_frame, body = channel.basic_get(queue=queue, auto_ack=True)
        if method_frame:
            return json.loads(body.decode())
        if timeout is not None and (time.time() - start_time) >= timeout:

            return None
        time.sleep(0.1)

@dataclass
class VNFDescriptor:
    """Describe all the necessary information of a VNF"""
    vnf_id: str # VNF unique ID
    #tcp_port_in: str 
    #tcp_address_out: str 
    #tcp_pot_out: str 
    nf_type: Optional[str] = None # Name of the Network Function
    sw_image: Optional[str] = None # Path to the image

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

        ret_queue = self.channel.queue_declare(queue="", exclusive=True)
        self.ret_queue = ret_queue.method.queue
        logging.info("VNFM listening in queue: %s.", queue_name)

        self.__vnf_id = [] # Store all the current instantiated VNFs identifier
        self.sfc_list = {}
        logging.info("Module started.")
        self.channel.start_consuming()
    
    def treat_vnfm(self, ch, method, properties, body):
        logging.info("Received command %s", body.decode())

        # parse msg to json
        msg = None
        try:
            msg = json.loads(body.decode())
        except:
            logging.error("Could not parse message.")
            return

        action = msg["action"]
        if action == "create_vnf":
            self.create_vnf(vnf_id=msg["vnf_id"], sfc_id=msg["sfc_id"])
            sfc_size = int(msg["sfc_size"])
            vnf_num = int(msg["vnf_num"])
            print(f"criando {vnf_num} de {sfc_size}")
            # if all VNFs were created, fetch all mesages
            if vnf_num >= sfc_size:
                sfc_forwarding = self.start_service(sfc_id=msg["sfc_id"]) 
                msg = {
                    "action" : "sfc-creation",
                    "sfc_id" : msg["sfc_id"],
                    "sfc" : sfc_forwarding
                }
                self.channel.basic_publish(exchange=GATEWAY_EXCHANGE, routing_key="",
                                        body=json.dumps(msg))

        elif action == "delete_vnf":
            self.delete_vnf(sfc_id=msg["sfc_id"])
        elif action == "heartbeat":
            self.channel.basic_publish(exchange="", routing_key=msg["rqueue"],
                                       body="ok")
        else:
            logging.info("Unknown message type!")

    def create_vnf(self, vnf_id, sfc_id=""):
        # first, check to see if the id is duplicated
        if vnf_id not in self.__vnf_id:
            message = {
                "action" : "start",
                "vnf_id" : vnf_id,
                "sfc_id" : sfc_id,
            }
            if sfc_id not in self.sfc_list:
                self.sfc_list[sfc_id] = []
            self.sfc_list[sfc_id].append(vnf_id)
            self.channel.basic_publish(exchange=VIM_EXCHANGE,
                                       body=json.dumps(message), routing_key="")
            return

        logging.error("VNF ID duplicate found. There is an error in NFVO!")

    def delete_vnf(self, vnf_id):
        """Deletes a vnf"""
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

    def start_service(self, sfc_id):
        """
        Start a SFC with the service sfc_id
        """
        vnf_ips = {}
        for vnf in self.sfc_list[sfc_id]:
            msg = {
                "action": "get_vnf_ip",
                "vnf_id": vnf,
                "rqueue": self.ret_queue
            }
            self.channel.basic_publish(exchange=VIM_EXCHANGE, routing_key="",
                                    body=json.dumps(msg))
            vnf_ip = wait_for_message(self.channel, self.ret_queue)
            vnf_ips[vnf] = vnf_ip["ip"]

        # Build the forward graph
        forward_graph = {}
        vnf_ids = self.sfc_list[sfc_id]
        for i, vnf in enumerate(vnf_ids):
            if i < len(vnf_ids) - 1:
                next_vnf = vnf_ids[i + 1]
                forward_graph[vnf] = vnf_ips[next_vnf]
            else:
                forward_graph[vnf] = "192.168.18.11"
                #forward_graph[vnf] = "0.0.0.0"
            # Once this is established, send message to VIM to start the VNF
            message = {
                "action": "run_vnf",
                "vnf_id" : vnf,
                "sfc_id" : sfc_id,
                "in" : vnf_ips[vnf],
                "out" : forward_graph[vnf]
            }
            self.channel.basic_publish(exchange=VIM_EXCHANGE, routing_key="",
                                    body=json.dumps(message))

        print("VNF IPs:", vnf_ips)
        print("Forward Graph:", forward_graph)

        return vnf_ips # optionally return if needed



if __name__ == "__main__":
    logging.basicConfig(
        filename="logs/vnfm.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | VNFM | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    vnfm = VNFM()


