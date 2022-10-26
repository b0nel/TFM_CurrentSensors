from paho.mqtt import client as mqtt_client
import random


broker = '192.168.1.200'
port = 1883
discover_client_topic = 'clientID/broker'
# generate client ID with pub prefix randomly
client_id = f'python-mqtt-{random.randint(0, 100)}'
username = 'pi'
password = 'nairda'

list_of_clients = []

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

def discover_sensors_subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        print(f"Received `{msg.payload.decode()}` from `{msg.topic}` topic")
        if msg.topic in discover_client_topic:
            if msg.payload.decode() not in list_of_clients:
                print(f"New client discovered: {msg.payload.decode()}")
                list_of_clients.append(msg.payload.decode())
                client.publish(f"{msg.payload.decode()}/ack", "ack")
                client.subscribe(msg.payload.decode() + '/currentSensor')
                print(list_of_clients)
        else:
            for client in list_of_clients:
                if msg.topic is client + '/currentSensor':
                    print(f"New sensor data from {client}: {msg.payload.decode()}")

    client.subscribe(discover_client_topic)
    client.on_message = on_message


def main():
    client = connect_mqtt()
    discover_sensors_subscribe(client)
    client.loop_forever()
    



if __name__ == '__main__':
    main()
