"""
SFC (Service Function Chain) is composed by multiple VNFs
This class has the methods to
    - Instantiate multiple VNFs, according to a internal VNF Catalog
        Support the connection between them
    - Terminate SFCs 
"""
import string
import random
from vnf.vnf import VNF
from mano.vnfm import VNFDescriptor, VNFM
import logging

logging.basicConfig(
    level=logging.INFO,  # Can be DEBUG, INFO, WARNING, ERROR, CRITICAL
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'  # Optional: Time format
)

class SFC():
    def __init__(self, instances: list, sfc_id=""):
        self.sfc_id = sfc_id
        # Start VNFs pointed by instances
        print(instances)
        vnf_list = []
        for i in instances:
            ret = self.start_vnf(i.vnf_id, i.queue_in, i.queue_out)
            if ret is not None:
                i.instance = ret
                vnf_list.append((i.vnf_id, i))
        self.vnfs = dict(vnf_list)
        
    def start_vnf(self, vnf_id, queue_in, queue_out):
        """ Starts a single VNF
            @param vnf_id: A random five letter id given by NFVO
            @param queue_in: A queue used to send communication to VNF
            @param queue_out: A queue used to send communication out form VNF
            @returns VNF descriptor, None 
        """
        return VNF(vnf_id, queue_in, queue_out)

    def get_vnf(self, vnf_id):
        """Return the VNF descriptor given a vnf_id
            @param vnf_id: Unique identifier of VNFs
        """
        return self.vnfs.get(vnf_id)
    
    def clean_sfc(self):
        for vnf_id, vnf_instance in self.vnfs.items():
            vnf_instance.instance.cleanup_vnf()
            logging.info("Deleting VNF: %s", vnf_id)



vnfm = VNFM()
vnfs = [VNFDescriptor(vnfm.generate_id(), "teste_in2", "teste_out2")]
sfc = SFC(vnfs)
sfc.clean_sfc()




