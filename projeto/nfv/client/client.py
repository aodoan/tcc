import pika as pk
import json
import os
import time
import sys
from tabulate import tabulate #type: ignore
from config import RABBITMQ_SERVER, NFVO_EXCHANGE, VNFM_EXCHANGE, VIM_EXCHANGE

connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
channel = connection.channel()
result = channel.queue_declare(queue="", exclusive = True)
queue = result.method.queue

def wait_for_message():
    while True:
        method_frame, header_frame, body = channel.basic_get(queue=queue, auto_ack=True)
        if method_frame:
            return body.decode()
        time.sleep(0.1) 

def show_commands():
    commands = {
        "list" : "List all commands",
        "create_sfc" : "Creates a SFC",
        "purge_sfc" : "Purges a SFC",
        "list_sfc" : "List all SFCs",
        "endpoints" : "Get endpoints of a specific SFC",
        "clear" : "Clears terminal",
        "exit" : "Exit client"
    }
    table = [(cmd, desc) for cmd, desc in commands.items()]
    print(tabulate(table, headers=["Command", "Description"], tablefmt="pretty"))

def read_command():
    command = input("nfv-mano> ")
    if command == "list":
        show_commands()
    elif command == "create_sfc":
        sfc_id = input("SFC ID: ")
        vnf_num = int(input("Number of VNFs (1-8): "))
        if vnf_num > 8 or vnf_num < 1:
            print("Invalid value for vnf")
            return
        msg = json.dumps({
            "action": "create_sfc",
            "sfc_id": sfc_id,
            "sfc_size": vnf_num
        })
        channel.basic_publish(exchange=VNFM_EXCHANGE,
                              routing_key="", body=msg)
    elif command == "list_sfc":
        msg = json.dumps({
            "action": "list_sfc",
            "return_queue" : queue
        })
        channel.basic_publish(exchange=VNFM_EXCHANGE,
                              routing_key="", body=msg)
        body = wait_for_message()
        try:
            msg = json.loads(body)
        except:
            print("Error decoding response from VNFM")
            return
        table = []

        for sfc_data in msg.values():
            for vnf_id, queues in sfc_data['sfc'].items():
                table.append([
                    vnf_id,
                    queues['queue_in'],
                    queues['queue_out']
                ])
        print(tabulate(table, headers=["VNF-ID", "Queue In", "Queue Out"], tablefmt="pretty"))


    elif command == "clear":
        os.system("clear")
    elif command == "exit":
        print("Quitting")
        sys.exit(1)

def main():
    print("NFV-MANO commands")
    try:
        while True:
            read_command()
    except KeyboardInterrupt:
        print("Quitting")
    
if __name__ == "__main__":
    main()