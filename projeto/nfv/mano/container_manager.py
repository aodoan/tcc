"""
Handles the managament with the containers
"""
import docker # type: ignore
import logging
import time
import threading
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
        self.running_containers = []
        self._create_network()
        # image, build_logs = self.client.images.build(
            # path=DOCKERFILE_DIR, # Assumes Dockerfile is in current directory
            # tag=IMAGE_NAME,    # Image name
            # rm=True
        # )

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
    

    def start_container(self, cmd, vnf_id=""):
        """ Start the container
        """
        cmd = cmd.split(" ")
        logging.info("Starting container")
        try:
            container = self.client.containers.run(
                self.image,
                command=cmd,
                name=vnf_id,
                detach=True,
                hostname="container_host",
                cpu_count=4,
                mem_limit='512m',
                stdin_open=True,
                )
            self.running_containers.append(container)
            return container
        except docker.errors.APIError as e:
            logging.error(f"Failed to start container: {e}")
            return None
    """
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
    """
    def monitor_container(self, container):
        """
        logging.info("Waiting for container to finish...")
        #container.wait()
        time.sleep(10)
        logs = container.logs().decode('utf-8')
        logging.info("Container output:\n%s", logs)
        """
        print("Dont use that")

    def _collect_logs(self, container):
        print("Dont use that")
        """
        try:
            buffer = ""
            for chunk in container.logs(stream=True):
                text = chunk.decode("utf-8")
                buffer += text
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    print(f"[{container.name}] {line}")
        except Exception as e:
            logging.error(f"Error collecting logs from container {container.name}: {e}")
        """

    def cleanup_container(self, container):
        try:
            container.remove()
            logging.info("Container removed.")
        except Exception as e:
            logging.warning(f"Could not remove container: {e}")
    
    def kilL_all(self):
        for container in self.running_containers:
            container.stop()


# a = ContainerManager()
# cont = a.start_container("python ./instance.py vnf-16 sfc-10 qin qout")
# try:
    # time.sleep(3000)
# except KeyboardInterrupt:
    # a.kilL_all()
# a.monitor_container(cont)
