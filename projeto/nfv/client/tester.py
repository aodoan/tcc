import pika as pk
import json
import time
from config import RABBITMQ_SERVER, IDS_EXCHANGE
connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
channel = connection.channel()
result = channel.queue_declare(queue="", exclusive = True)
queue = result.method.queue


def wait_for_message(timeout=None):
    start_time = time.time()
    while True:
        method_frame, header_frame, body = channel.basic_get(queue=queue, auto_ack=True)
        if method_frame:
            return body.decode()
        if timeout is not None and (time.time() - start_time) >= timeout:

            return None
        time.sleep(0.1)

# Send message to train 
def train_msg(method, arguments, dataset="kd99"):
    msg = {
        "action": "train",
        "dataset": "kdd99",
        "method": method,
        "arguments": arguments
    }
    
    channel.basic_publish(exchange=IDS_EXCHANGE, routing_key="", body=json.dumps(msg))

def summary():
    msg = {
        "action": "fetch_summary",
        "rqueue" : queue
    }
    
    channel.basic_publish(exchange=IDS_EXCHANGE, routing_key="", body=json.dumps(msg))

train_msg(method="iforest", arguments={})