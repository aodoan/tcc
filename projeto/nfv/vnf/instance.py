"""
Code running inside a container

python3 instance.py [VNF_ID] [SFC_ID] [QUEUE_IN] [QUEUE_OUT]
"""
import sys
import signal
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
    print("Incorrect usage!")
    print("python ./instance.py VNF_ID SFC_ID QUEUE_IN QUEUE_OUT")

logging.info("QUEUES: %s %s", q_in, q_out)

def nf(input):
    return input


vnf = VNF(vnf_id, sfc_id, q_in, q_out, nf, create_queue=False)
def handle_sigterm():
    logging.info("Received SIGTERM")
    vnf.stop_service()

# Register SIGTERM to end process
signal.signal(signal.SIGTERM, handle_sigterm)

print("INPUT QUEUE: " + vnf.get_queue_in())
print("OUTPUT QUEUE: " + vnf.get_queue_out())
vnf.start_service()



