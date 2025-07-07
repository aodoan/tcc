import sys
import json
import time
import os
import pika as pk  # type: ignore
import argparse
import pandas as pd
import socket
import threading
import queue
from sklearn.model_selection import train_test_split
from config import RABBITMQ_SERVER, IDS_EXCHANGE, GATEWAY_PORT
from datetime import datetime

class TCPClient:
    def __init__(self, address, port):
        self.address = address
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.address, self.port))

    def send(self, line):
        self.socket.sendall(line.encode('utf-8'))

    def close(self):
        self.socket.close()

class PikaManager:
    def __init__(self, server, exchange):
        self.recv_queue = queue.Queue()
        self.send_queue = queue.Queue()
        self.connection = pk.BlockingConnection(pk.ConnectionParameters(server))
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue="", exclusive=True)
        self.queue_name = result.method.queue
        self.exchange = exchange

        threading.Thread(target=self._pika_thread, daemon=True).start()

    def _callback(self, ch, method, properties, body):
        self.recv_queue.put(body.decode())

    def _pika_thread(self):
        self.channel.basic_consume(queue=self.queue_name, on_message_callback=self._callback, auto_ack=True)
        while True:
            self.connection.process_data_events(time_limit=1)
            try:
                msg = self.send_queue.get_nowait()
                self.channel.basic_publish(exchange=self.exchange, routing_key="", body=msg)
            except queue.Empty:
                pass

    def send(self, msg):
        self.send_queue.put(json.dumps(msg))

    def wait_for_message(self, timeout=None):
        try:
            return self.recv_queue.get(timeout=timeout)
        except queue.Empty:
            return None

methods = ["lof", "osvm", "iforest"]

argument_list = {
    "lof": {
        "n_neighbors": 10,
        "contamination": 0.5
    },
    "iforest": {
        "max_samples": 100,
        "random_state": 4
    },
    "osvm": {
        "gamma": "auto",
        "kernel": "rbf",
        "split_sample": 2
    }
}

def train_msg(pika_mgr, method, dataset):
    msg = {
        "action": "train",
        "dataset": dataset,
        "method": method,
        "rqueue": pika_mgr.queue_name,
        "argument": argument_list[method]
    }
    pika_mgr.send(msg)

def summary(pika_mgr):
    msg = {
        "action": "fetch_summary",
        "rqueue": pika_mgr.queue_name
    }
    pika_mgr.send(msg)

def clean_summary(pika_mgr):
    msg = {
        "action": "clean_summary",
        "rqueue": pika_mgr.queue_name
    }
    pika_mgr.send(msg)

def get_train_set(df, p=0.05, random_num=22):
    if 1.0 < p <= 100.0:
        p /= 100.0
    label_col = df.columns[-1]
    if df[label_col].nunique() <= 1:
        raise RuntimeError("Cannot stratify: label column has <= 1 class.")
    train_df, _ = train_test_split(df, train_size=p, random_state=random_num)
    return train_df

def main():
    parser = argparse.ArgumentParser(description='Make tests for all methods and ensemble the results')
    parser.add_argument('-d', '--dataset', dest='dataset', metavar='DATASET', required=True, action='store', help='Path to the dataset CSV file')
    parser.add_argument('-z', '--dataset_name', dest='dataset_name', metavar='DATASET', required=True, action='store', help='Dataset name (e.g. kdd99)')
    parser.add_argument('-o', '--output', dest='output', metavar='OUTPUT', required=True, action='store', help='Output folder to store results')
    parser.add_argument('-n', '--num-runs', dest='num_runs', metavar='N', type=int, default=1, action='store', help='Number of runs for each model (default: 1)')
    parser.add_argument('-p', '--percentage', dest='percentage', metavar='PERCENTAGE', type=float, default=0.05, action='store', help='Percentage of data to sample (default: 0.05)')
    parser.add_argument('-m', '--method', dest='method', required=True, metavar='METHOD', action='store', help='Choose a method to run (osvm, iforest, lof).')
    args = parser.parse_args()

    df = pd.read_csv(args.dataset)
    time_started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    gateway = TCPClient("192.168.18.11", GATEWAY_PORT)
    pika_mgr = PikaManager(RABBITMQ_SERVER, IDS_EXCHANGE)

    path = os.path.join(args.output, args.method)
    os.makedirs(path, exist_ok=True)
    i = 1
    while True:
        filename = f"output{i:02}.json"
        filepath = os.path.join(path, filename)
        if not os.path.exists(filepath):
            break
        i += 1

    results = []
    train_msg(pika_mgr, args.method, args.dataset_name)
    saida = pika_mgr.wait_for_message(timeout=30)
    print(saida)
    training_time = json.loads(saida)["runtime"]
    time.sleep(2)

    for i in range(1, args.num_runs + 1):
        partial_df = get_train_set(df, p=args.percentage, random_num=i + 2223)
        print(f"{args.method}: Run {i}")
        run_id = f"run_{i}"
        count = 0
        counter = 0
        for _, row in partial_df.iterrows():
            line = ",".join(map(str, row.values)) + "\n"
            gateway.send(line)
            count += 1
            counter += 1
            if counter > 2500:
                break
            if count > 1000:
                print("Getting summary (prevent lost connection)")
                summary(pika_mgr)
                pika_mgr.wait_for_message(timeout=10)
                print("Got summary back")
                count = 0
            time.sleep(0.1)

        print("Round finished. Getting summary back")
        summary(pika_mgr)
        saida = json.loads(pika_mgr.wait_for_message(timeout=30))
        results.append((run_id, saida))
        clean_summary(pika_mgr)
        pika_mgr.wait_for_message(timeout=10)

    time_finished_dt = datetime.now()
    time_finished = time_finished_dt.strftime("%Y-%m-%d %H:%M:%S")
    parsed_time_started = datetime.strptime(time_started, "%Y-%m-%d %H:%M:%S")

    data = {
        "start_at": time_started,
        "finish_at": time_finished,
        "runtime": str(time_finished_dt - parsed_time_started),
        "training_time": training_time,
        "runs": args.num_runs,
        "method": args.method,
        "arguments": argument_list[args.method],
        "info": {k: v for k, v in results}
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

    gateway.close()

if __name__ == '__main__':
    sys.exit(main())
