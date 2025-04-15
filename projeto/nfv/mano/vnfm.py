"""
VNFM is responsible for the lifecycle management of a VNFM

"""
import os
import nfv
import random
import string
import logging


class vnfm():
    def __init__(self):
        print("vnfm started")
        self.__vnf_id = [] # Store all the current instantiated VNFs identifier
        

    def generate_id(prefix="vnf-", length=6, max_attempts=20):
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
        return Non
