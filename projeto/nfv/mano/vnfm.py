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
from dataclasses import dataclass
from typing import Optional
from vnf.vnf import VNF
@dataclass
class VNFDescriptor:
    """Describe all the necessary information of a VNF"""
    vnf_id: str
    queue_in: str
    queue_out: str
    sw_image: Optional[str] = None # Path to the image
    instance: Optional[VNF] = None

class VNFM():
    def __init__(self):
        print("vnfm started")
        self.__vnf_id = [] # Store all the current instantiated VNFs identifier
        

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
    
