from paho.mqtt import client as mqtt_client
import random
import json
import os
import datetime
import logging, sys
from CostElectricity import CostElectricity


broker = '192.168.1.200'
port = 1883
discover_client_topic = 'clientID/broker'
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 100)}'
username = 'pi'
password = 'nairda'

list_of_clients = set()
JSON_FILE = 'clients.json'

PRICES = CostElectricity()

#logging settings
logging.basicConfig(stream=sys.stderr, level=logging.INFO)

def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logging.info("Connected to MQTT Broker!")
        else:
            logging.error("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def discover_sensors_and_subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        logging.debug(f"[{datetime.datetime.now().time()}]Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if msg.topic in discover_client_topic:
            if msg.payload.decode() not in list_of_clients:
                logging.info(f"[{datetime.datetime.now().time()}]New client discovered: {msg.payload.decode()}")
                list_of_clients.add(msg.payload.decode())
                new_client(msg.payload.decode())
                client.subscribe(msg.payload.decode() + '/amps')
            client.publish(f"{msg.payload.decode()}/ack", "ack")
        else:
            for client in list_of_clients:
                if msg.topic == client + '/amps':
                    logging.info(f"[{datetime.datetime.now().time()}]New current data from {client}: {msg.payload.decode()}")
                if msg.topic == client + '/watts':
                    logging.info(f"[{datetime.datetime.now().time()}]New watts data from {client}: {msg.payload.decode()}")

    client.subscribe(discover_client_topic)
    [client.subscribe(cl + '/amps') for cl in list_of_clients]
    [client.subscribe(cl + '/watts') for cl in list_of_clients]
    client.on_message = on_message

def new_client(client):
    with open(JSON_FILE, "r") as f:
        json_clients = json.load(f)

    if client not in json_clients["clients"]:
        json_clients["clients"].append(client)
        list_of_clients.append(client)
        with open(JSON_FILE, "w", encoding='utf-8') as f:
            json.dump(json_clients, f, ensure_ascii=False, indent=4)

def read_clients():
    if os.path.isfile(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            json_clients = json.load(f)
            if len(json_clients["clients"]) > 0:
                [list_of_clients.add(client) for client in json_clients["clients"]]
                logging.debug("List of clients: ", list_of_clients)
            else:
                logging.debug("No clients found")
    else:
        with open(JSON_FILE, "w", encoding='utf-8') as f:
            json.dump({"clients": []}, f, ensure_ascii=False, indent=4)
        logging.debug("No clients found")

def main():
    read_clients()
    client = connect_mqtt()
    discover_sensors_and_subscribe(client)
    client.loop_forever()
    



if __name__ == '__main__':
    main()
