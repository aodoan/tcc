# General config values used troughout the project

# RabbitMQ server IP
RABBITMQ_SERVER = "172.17.0.1"

# List of exchanges used to communicate
# Exchange used by all VNFs to receive commands from MANO, NFVO, etc
VNF_CONTROL_EXCHANGE = "vnf-control"

VIM_EXCHANGE = "vim-exchange"
NFVO_EXCHANGE = "nfvo-exchange"
VNFM_EXCHANGE = "vnfm-exchange"
GATEWAY_EXCHANGE = "nfv-gateway-exchange"
FORWARDER_EXCHANGE = "fwd-exchange"

NFVIN_EXCHANGE = "nfv-in-exchange"
IDS_EXCHANGE = "ids-exchange"

DOCKERFILE_PATH = "/home/hal/Desktop/tcc/projeto/nfv/vnf/dockerfile"
DOCKERFILE_DIR = "/".join([part for part
                           in DOCKERFILE_PATH.split("/")[:-1]])

IMAGE_NAME = "vnf-instance-tcp"
GATEWAY_PORT = 30000
ENDPOINT_PORT = 35012

DEFAULT_IN_PORT = 2323
DEFAULT_OUT_PORT = 3030

IDS_IP = "192.168.18.11"
IDS_PORT = 2538

class NetConfig:
    network_name = "nfv-comm-network"
    network_ip = "192.168.1.10"
    subnet = "192.168.1.0/24"

net = NetConfig()



