"""
SFC (Service Function Chain) is composed by multiple VNFs
This class has the methods to
    - Instantiate multiple VNFs, according to a internal VNF Catalog
        Support the connection between them
    - Terminate SFCs 
"""
import string
import random
from nfv.vnf import vnf

class sfc():
    def __init__(self, instances : dict):
        # Start VNFs pointed by instances
        print(instances)
        self.vnfs = []
        for i in instances:
            self.vnfs.append(self.start_vnf(i.vnf_id, i.queue_in, i.queue_out))


    def start_vnf(self, vnf_id, queue_in, queue_out):
        """ Starts a single VNF
            @param vnf_id: A random five letter id given by NFVO
            @param queue_in: A queue used to send communication to VNF
            @param queue_out: A queue used to send communication out form VNF
            @returns VNF descriptor, None 
        """
        return vnf(vnf_id, queue_in, queue_out)


