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
from mano.container_manager import ContainerManager
from config import RABBITMQ_SERVER
import time
@dataclass
class VNFDescriptor:
    """Describe all the necessary information of a VNF"""
    vnf_id: str # VNF unique ID
    queue_in: str # VNF input queue
    queue_out: str # VNF output queue
    nf_type: Optional[str] = None # Name of the Network Function
    sw_image: Optional[str] = None # Path to the image

class VNFM():
    def __init__(self, channel):
        """Init VNFM
            @param channel: RabbitMQ channel connection"""
        print("vnfm started")
        self.__vnf_id = [] # Store all the current instantiated VNFs identifier
        self.sfc_list = []
        self.channel = channel
        self.container_manager = ContainerManager()
        
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
            cont = self.container_manager.start_container(f"python ./instance.py {vnf.vnf_id} {sfc_id} {vnf.queue_in} {vnf.queue_out}", vnf_id=vnf.vnf_id)
            cont.start()
        return _sfc

    
    def cleanup_sfc(self, sfc_id):
        for idx, (stored_id, sfc) in enumerate(self.sfc_list):
            if stored_id == sfc_id:
                sfc.clean_sfc()
                ids = sfc.get_instances()
                print(f"IDS deleted: {ids}")
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
    
# Example 
connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
channel = connection.channel()
vnfm = VNFM(channel=channel)

sfc = vnfm.instantiate_sfc("sfc-5", [], 3)
qin, qout = sfc.endpoints()
print(f"Queue in: {qin}, queue out: {qout}")
while True:
    inp = input("Digite q para sair")
    if inp == "q":
        break

vnfm.cleanup_sfc("sfc-5")

