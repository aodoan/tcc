"""
VIM - Virtualized Infrastructure Manager is responsible for controlling 
and managing the NFVI compute, storage and network resources

- In this implementation is used containers
"""
import docker # type: ignore
import logging
import json
import pika as pk
from config import DOCKERFILE_DIR, IMAGE_NAME, VIM_EXCHANGE, RABBITMQ_SERVER
from config import net

logging.basicConfig(
    filename="logs/vim.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

class VIM:
    def __init__(self):
        """Start all services and internal structures"""
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
        self.channel = self.connection.channel()

        # Start to listen to exchange for commands 
        self.channel.exchange_declare(exchange=VIM_EXCHANGE,
                                      exchange_type='fanout', durable=True)
        result = self.channel.queue_declare(queue="", exclusive=True)
        queue_name = result.method.queue
        self.channel.queue_bind(queue=queue_name, exchange=VIM_EXCHANGE)
        self.channel.basic_consume(queue=queue_name,
                                   on_message_callback=self.treat_vim,
                                   auto_ack=True)

        logging.info("Listening to controls in %s", queue_name)
        self.client = docker.from_env()
        self.image = IMAGE_NAME
        self.running_containers = []
        self.start_service()

    def start_service(self):
        """Start consuming all incoming messages"""
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logging.info("Received Interruption, turning off all VNFs...")
            self.kill_all()

    def treat_vim(self, ch, method, properties, body):
        """Respond to commands receveid in VIM_EXCHANGE"""
        # Parse msg to json
        msg = None
        try:
            msg = json.loads(body.decode())
        except:
            logging.error("Could not parse message.")
            return

        action = msg["action"]
        if action == "start":
            cmd = f"python instance.py {msg["vnf_id"]} {msg["sfc_id"]} {msg["qin"]} {msg["qout"]}"
            print(msg["vnf_id"])
            self.start_container(cmd, vnf_id=msg["vnf_id"])
        elif action == "stop":
            self.stop_container(msg["vnf_id"])
        elif action == "heartbeat":
            print("got heartbeat")
            self.channel.basic_publish(exchange="", routing_key=msg["rqueue"],
                                       body="ok")

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
        
    def stop_container(self, vnf_id):
        for idx, (stored_id, container) in enumerate(self.running_containers):
            if stored_id == vnf_id:
                try:
                    #container.stop()  # Docker SDK: stop the container
                    # killing instead of stopping
                    container.kill()  # Docker SDK: stop the container
                    del self.running_containers[idx]
                    logging.info("Container for VNF %s stopped and removed from the list.", vnf_id)
                except Exception as e:
                    logging.error("Error stopping container for VNF %s: %s", vnf_id, e)
                break
        else:
            logging.error("No container found for VNF %s", vnf_id)


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
        for (vnf_id, container) in self.running_containers:
            logging.info("Stopping VNF: %s", vnf_id)
            container.kill()

a = VIM()
# a = VIM()
# cont = a.start_container("python ./instance.py vnf-16 sfc-10 qin qout")
# try:
    # time.sleep(3000)
# except KeyboardInterrupt:
    # a.kilL_all()
# a.monitor_container(cont)
