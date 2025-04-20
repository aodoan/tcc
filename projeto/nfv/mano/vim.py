"""
VIM - Virtualized Infrastructure Manager is responsible for controlling 
and managing the NFVI compute, storage and network resources

- In this implementation is used containers
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

class VIM:
    def __init__(self):
        self.client = docker.from_env()
        self.image = IMAGE_NAME
        self.running_containers = []
        # image, build_logs = self.client.images.build(
            # path=DOCKERFILE_DIR, # Assumes Dockerfile is in current directory
            # tag=IMAGE_NAME,    # Image name
            # rm=True
        # )

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
            self.running_containers.append((vnf_id, container))
            return container
        except docker.errors.APIError as e:
            logging.error(f"Failed to start container: {e}")
            return None

    def run_command(self, vnf_id):
        """Run a command in the VNF container"""
        print("TODO")
    
    def cleanup_container(self, container):
        try:
            container.remove()
            logging.info("Container removed.")
        except Exception as e:
            logging.warning(f"Could not remove container: {e}")
    
    def kill_all(self):
        for container in self.running_containers:
            container.stop()


# a = VIM()
# cont = a.start_container("python ./instance.py vnf-16 sfc-10 qin qout")
# try:
    # time.sleep(3000)
# except KeyboardInterrupt:
    # a.kilL_all()
# a.monitor_container(cont)
