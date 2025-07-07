import pika as pk
import json
import os
import time
import sys
from tabulate import tabulate #type: ignore
from config import RABBITMQ_SERVER, NFVO_EXCHANGE, VNFM_EXCHANGE, VIM_EXCHANGE, IDS_EXCHANGE

connection = pk.BlockingConnection(pk.ConnectionParameters(RABBITMQ_SERVER))
channel = connection.channel()
result = channel.queue_declare(queue="", exclusive = True)
queue = result.method.queue


# ASCII color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

def wait_for_message(timeout=None):
    start_time = time.time()
    while True:
        method_frame, header_frame, body = channel.basic_get(queue=queue, auto_ack=True)
        if method_frame:
            return body.decode()
        if timeout is not None and (time.time() - start_time) >= timeout:

            return None
        time.sleep(0.1)

def get_status():
    """Get the status of each NFV module + IDS"""
    modules = {
        "NFVO": NFVO_EXCHANGE,
        "VNFM": VNFM_EXCHANGE,
        "VIM": VIM_EXCHANGE,
        "IDS": IDS_EXCHANGE
    }
    
    msg = json.dumps({
        "action": "heartbeat",
        "rqueue": queue
    })

    table = []
    for module, exchange in modules.items():
        status = "OFF"
        try:
            channel.basic_publish(exchange=exchange, routing_key="", body=msg)
            response = wait_for_message(timeout=2)
            if response == "ok":
                status = "OK"
        except Exception as e:
            pass
        color_status = f"{GREEN}{status}{RESET}" if status == "OK" else f"{RED}{status}{RESET}"
        table.append([module, color_status])

    print(tabulate(table, headers=["Module", "Status"], tablefmt="grid"))            
    
def show_commands():
    commands = {
        "list" : "List all commands",
        "status": "Show the status of each NFV component",
        "create_sfc" : "Creates a SFC",
        "purge_sfc" : "Purges a SFC",
        "list_sfc" : "List all SFCs",
        "endpoints" : "Get endpoints of a specific SFC",
        "clear" : "Clears terminal",
        "exit" : "Exit client"
    }
    table = [(cmd, desc) for cmd, desc in commands.items()]
    print(tabulate(table, headers=["Command", "Description"], tablefmt="pretty"))

def get_sfc_list():
    msg = json.dumps({
        "action": "list_sfc",
        "return_queue" : queue
    })
    channel.basic_publish(exchange=NFVO_EXCHANGE,
                            routing_key="", body=msg)
    body = wait_for_message()
    try:
        msg = json.loads(body)
    except:
        print("Error decoding response from NFVO")
        return
    return msg

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
        print(msg)
        channel.basic_publish(exchange=NFVO_EXCHANGE,
                              routing_key="", body=msg)
        print(f"{sfc_id} created.")
    elif command == "status":
        get_status()
    elif command == "purge_sfc":
        msg = get_sfc_list()
        sfcs = list(msg.keys())
        if len(command.split()) == 1:
            sfc_id = input("SFC ID: ")
        else:
            sfc_id = command.split()[1]

        if sfc_id not in sfcs:
            print("SFC not in the list of SFC's.")
            print(sfcs)
        else:
            delete_msg = json.dumps({
                "action": "delete_sfc",
                "sfc_id" : sfc_id
            })
            channel.basic_publish(exchange=NFVO_EXCHANGE,
                                    routing_key="", body=delete_msg)
            print(f"{sfc_id} purged.")

    elif command == "list_sfc":
        msg = get_sfc_list()
        table = []
        sfcs = list(msg.keys())
        counter = 0
        for sfc_data in msg.values():
            for vnf_id, queues in sfc_data['sfc'].items():
                table.append([
                    vnf_id
                    #queues['queue_in'],
                    #queues['queue_out']
                ])
            sfc_id = sfcs[counter]
            counter += 1
            print(f"{'=' * len(sfc_id)}{'\n'}{sfc_id}{'\n'}{'=' * len(sfc_id)}") # sorry for that line
            #print(tabulate(table, headers=["VNF-ID", "Queue In", "Queue Out"], tablefmt="pretty"))
            print(tabulate(table, headers=["VNF-ID"], tablefmt="pretty"))


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
