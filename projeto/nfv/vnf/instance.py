"""
Code running inside a container

python3 instance.py [VNF_ID] [QUEUE_IN] [QUEUE_OUT]
"""
import sys
import logging
from vnf import VNF

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

vnf_id = ""
sfc_id = ""
q_in = ""
q_out = ""

try:
    vnf_id = sys.argv[1]
    sfc_id = sys.argv[2]
    q_in = sys.argv[3]
    q_out = sys.argv[4]
except:
    print("Incorrect usage")

def nf(input):
    return f"{input} -> {vnf_id}"

vnf = VNF(vnf_id, sfc_id, q_in, q_out, nf)
print("INPUT QUEUE: " + vnf.get_queue_in())
print("OUTPUT QUEUE: " + vnf.get_queue_out())
vnf.start_service()



