from paho.mqtt import client as mqtt_client
import random
import json
import os


broker = '192.168.1.200'
port = 1883
discover_client_topic = 'clientID/broker'
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 100)}'
username = 'pi'
password = 'nairda'

list_of_clients = []
JSON_FILE = 'clients.json'

def connect_mqtt() -> mqtt_client:
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(client_id)
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client

def discover_sensors_and_subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if msg.topic in discover_client_topic:
            if msg.payload.decode() not in list_of_clients:
                print(f"New client discovered: {msg.payload.decode()}")
                list_of_clients.append(msg.payload.decode())
                new_client(msg.payload.decode())
                client.subscribe(msg.payload.decode() + '/currentSensor')
            client.publish(f"{msg.payload.decode()}/ack", "ack")
        else:
            for client in list_of_clients:
                if msg.topic is client + '/currentSensor':
                    print(f"New sensor data from {client}: {msg.payload.decode()}")

    client.subscribe(discover_client_topic)
    [client.subscribe(cl + '/currentSensor') for cl in list_of_clients]
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
                [list_of_clients.append(client) for client in json_clients["clients"]]
                print("List of clients: ", list_of_clients)
            else:
                print("No clients found")
    else:
        with open(JSON_FILE, "w", encoding='utf-8') as f:
            json.dump({"clients": []}, f, ensure_ascii=False, indent=4)
        print("No clients found")

def main():
    read_clients()
    client = connect_mqtt()
    discover_sensors_and_subscribe(client)
    client.loop_forever()
    



if __name__ == '__main__':
    main()
