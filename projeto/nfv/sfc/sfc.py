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
import logging
from config import VNF_CONTROL_EXCHANGE

class SFC():
    def __init__(self, instances: list, sfc_id="", channel = None):
        """Init a SFC"""
        self.sfc_id = sfc_id
        # Start VNFs pointed by instances
        self.vnfs = instances
        self.channel = channel
        if self.channel is not None:
            self.channel.exchange_declare(exchange=VNF_CONTROL_EXCHANGE,
                                          exchange_type="fanout")
    
    def clean_sfc(self):
        self.channel.basic_publish(exchange=VNF_CONTROL_EXCHANGE,
                                   routing_key="",
                                   body=f"delete_sfc,{self.sfc_id}")
    def get_instances(self):
        return self.vnfs
    
    def endpoints(self):
        """Return a tuple with the first and last queue"""
        return (self.queues[0], self.queues[-1])


# vnfm = VNFM()
# vnfs = [VNFDescriptor(vnfm.generate_id(), "teste_in2", "teste_out2")]
# sfc = SFC(vnfs)
# sfc.clean_sfc()




