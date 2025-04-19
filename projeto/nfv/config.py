# General config values used troughout the project

# RabbitMQ server IP
RABBITMQ_SERVER = "172.17.0.1"

# Exchange used by all VNFs to receive commands from MANO, NFVO, etc
VNF_CONTROL_EXCHANGE = "vnf-control"

#
DOCKERFILE_PATH = "/home/hal/Desktop/tcc/projeto/nfv/vnf/dockerfile"
DOCKERFILE_DIR = "/".join([part for part
                           in DOCKERFILE_PATH.split("/")[:-1]])

IMAGE_NAME = "nfv-instance"

class NetConfig:
    network_name = "nfv-comm-network"
    network_ip = "192.168.1.10"
    subnet = "192.168.1.0/24"

net = NetConfig()



