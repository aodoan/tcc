"""
Code running inside a container

"""

import logging
from vnf.vnf import VNF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def nf(input):
    return f"{input}->vnf-32112"

vnf = VNF("vnf-32112", nf)
print("INPUT QUEUE: " + vnf.get_queue_in())
print("OUTPUT QUEUE: " + vnf.get_queue_out())
vnf.start_service()



