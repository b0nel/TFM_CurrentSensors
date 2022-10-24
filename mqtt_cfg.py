from umqttsimple import MQTTClient
import ubinascii
import machine

SERVER_IP = '192.168.1.200'
MOSQUITTO_USER = b'pi'
MOSQUITTO_PASS = b'nairda'

class MQTT:
    def __init__(self, server_ip=SERVER_IP, user=MOSQUITTO_USER, password=MOSQUITTO_PASS):
        self.server_ip = server_ip
        self.client_id = ubinascii.hexlify(machine.unique_id())
        self.user = user
        self.password = password
        self.mqtt = None
        self.connect()
    
    def connect(self):
        self.mqtt = MQTTClient(self.client_id, self.server_ip, user=self.user, password=self.password)
        try:
            self.mqtt.connect()
        except:
            print('Could not connect to MQTT broker')
            print('Trying to connect again. Reseting the device...')
            machine.reset()
        print('Connected to MQTT broker ' + self.server_ip)
    
    def publish(self, topic, message):
        self.mqtt.publish(topic, message)
        print('Published to topic ' + topic + ': ' + message)