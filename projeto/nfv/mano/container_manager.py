"""
Handles the managament with the containers
"""
import docker # type: ignore
import logging
from config import DOCKERFILE_DIR, IMAGE_NAME
from config import net


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class ContainerManager:
    def __init__(self):
        self.client = docker.from_env()
        self.network_name = net.network_name
        self.subnet = net.subnet
        self.ip_address = net.network_ip
        self.image = IMAGE_NAME
        self._create_network()
        image, build_logs = self.client.images.build(
            path=DOCKERFILE_DIR, # Assumes Dockerfile is in current directory
            tag=IMAGE_NAME,    # Image name
            rm=True
        )

    def _create_network(self):
        try:
            self.client.networks.get(self.network_name)
            logging.info(f"Network '{self.network_name}' already exists.")
        except docker.errors.NotFound:
            logging.info(f"Creating network '{self.network_name}'...")
            self.client.networks.create(
                self.network_name,
                driver="bridge",
                ipam=docker.types.IPAMConfig(pool_configs=[
                    docker.types.IPAMPool(subnet=self.subnet)
                ])
            )
    

    def start_container(self, cmd):
        """
        """
        cmd = cmd.split(" ")

        try:
            container = self.client.containers.run(
                self.image,
                command=cmd,
                detach=True,
                network=self.network_name,
                hostname="container_host",
                tty=True,
                stdin_open=True,
                mac_address="02:42:c0:a8:64:0a",
                network_mode=None,
                networking_config=self.client.api.create_networking_config({
                    self.network_name: self.client.api.create_endpoint_config(ipv4_address=self.ip_address)
                })
            )

            return container
        except docker.errors.APIError as e:
            logging.error(f"Failed to start container: {e}")
            return None

    def start_container(self, args_list):
        logging.info("Starting container with args: %s", args_list)
        # transform arg_list to a real list
        args_list = args_list.split(" ")
        try:
            container = self.client.containers.run(
                self.image,
                command=args_list,
                detach=True,
                network=self.network_name,
                hostname="container_host",
                tty=True,
                stdin_open=True,
                mac_address="02:42:c0:a8:64:0a",
                network_mode=None,
                networking_config=self.client.api.create_networking_config({
                    self.network_name: self.client.api.create_endpoint_config(ipv4_address=self.ip_address)
                })
            )
            return container
        except docker.errors.APIError as e:
            logging.error(f"Failed to start container: {e}")
            return None

    def monitor_container(self, container):
        logging.info("Waiting for container to finish...")
        container.wait()
        logs = container.logs().decode('utf-8')
        logging.info("Container output:\n%s", logs)

    def cleanup_container(self, container):
        try:
            container.remove()
            logging.info("Container removed.")
        except Exception as e:
            logging.warning(f"Could not remove container: {e}")


a = ContainerManager()
cont = a.start_container("python ./instance.py vnf-12 sfc-10 qin qout")
a.monitor_container(cont)
