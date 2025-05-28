import sys
import json
import time
import os
import pika as pk # type: ignore
import argparse
import pandas as pd
import socket
from sklearn.model_selection import train_test_split
from config import RABBITMQ_SERVER, IDS_EXCHANGE
import socket

class TCPClient:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.address, self.port))

    def send(self, line):
        print(f"Sending: {line.strip()}")
        self.socket.sendall(line.encode('utf-8'))

    def close(self):
        self.socket.close()


methods = ["lof", "osvm", "iforest"]

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


def get_train_set(df, p=0.05):
    """ 
    Get a training dataset from the full data

    Args:
        df(dataframe): Full dataframe
        p(float): Percentage of the train set     
    """
    # if percetage was passed between 1.0 and 100.0
    if 1.0 < p <= 100.0:
        p /= 100.0 

    label_col = df.columns[-1]
    _, sampled_df = train_test_split(
        df,
        test_size=p,
        stratify=df[label_col],
        random_state=42
    )
    return sampled_df



def main():
    parser = argparse.ArgumentParser(
        description='Make tests for all methods and ensemble the results'
    )

    parser.add_argument(
        '-d', '--dataset',
        dest='dataset',
        metavar='DATASET',
        required=True,
        action='store',
        help='Path to the dataset CSV file'
    )

    parser.add_argument(
        '-o', '--output',
        dest='output',
        metavar='OUTPUT',
        required=True,
        action='store',
        help='Output folder to store results'
    )

    parser.add_argument(
        '-n', '--num-runs',
        dest='num_runs',
        metavar='N',
        type=int,
        default=1,
        action='store',
        help='Number of runs for each model (default: 1)'
    )

    parser.add_argument(
        '-p', '--percentage',
        dest='percentage',
        metavar='PERCENTAGE',
        type=float,
        default=0.05,
        action='store',
        help='Percentage of data to sample (default: 0.05)'
    )

    parser.add_argument(
        '-m', '--methods',
        dest='methods',
        metavar='METHOD',
        nargs='+',
        choices=methods,
        default=methods,
        help='Methods to run (choose one or more: osvm, iforest, lof). Default: all'
    )

    # Parse
    args = parser.parse_args()

    # Setup
    # Load Dataset (no need for labels)
    df = pd.read_csv(args.dataset)

    if args.methods == []:
        raise RuntimeError("No methods selected.")

    #Connect to gateway
    gateway = TCPClient("192.168.18.11", 34102)
    
    # Create sub-directories
    for method in args.methods:
        path = os.path.join(args.output, method)
        os.makedirs(path, exist_ok=True)
        results = []
        train_msg("iforest", {})
        input("Type to train")
        partial_df = get_train_set(df, p=0.001)
        for i in range(1, args.num_runs+1):
            print(f"{method}: Run {i}")
            count = 0 
            for _, row in partial_df.iterrows():
                line = ",".join(map(str, row.values)) + "\n"
                print(line)
                gateway.send(line)
                count += 1
                time.sleep(0.3)
            # send train message, and wait a few seconds
        summary()
        saida = wait_for_message()
        print(saida)
        sys.exit(1)

    gateway.close()




if __name__ == '__main__':
    sys.exit(main())