from lib.umqttsimple import MQTTClient
import ubinascii
import machine
import utime
import os

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
        self.broker_acknowledged = False
        self.sensor_configured = False
    
    def connect(self):
        self.mqtt = MQTTClient(self.client_id, self.server_ip, user=self.user, password=self.password)
        try:
            self.mqtt.connect()
        except:
            print('Could not connect to MQTT broker')
            utime.sleep(1)
            print('Trying to connect again. Reseting the device...')
            machine.reset()
        print('Connected to MQTT broker ' + self.server_ip)
    
    def publish(self, topic, message):
        self.mqtt.publish(topic, message)
        print('Published to topic ' + topic + ': ' + message)

    def subscribe(self, topic):
        self.mqtt.subscribe(topic)
        print('Subscribed to topic ' + topic)
        
    def check_msg(self):
        self.mqtt.check_msg()

    def publish_clientID(self):
        self.subscribe('ack/' + self.client_id.decode("utf-8"))
        while self.broker_acknowledged == False:
            self.mqtt.check_msg()
            self.publish('clientID/broker', self.client_id.decode("utf-8"))
            utime.sleep(1)
    
    def is_broker_acknowledged(self,):
        for file in os.listdir():
            if file == 'broker_acknowledged.cfg':
                with open('broker_acknowledged.cfg', 'r') as file:
                    return file.read() == 'True'
        return False

    def set_broker_acknowledged(self, value):
        with open('broker_acknowledged.cfg', 'w') as file:
            file.write(str(value))

    def get_sensor_config_from_broker(self):
        """
        This function is called when the sensor is not configured yet.
        It subscribes to the topic 'sensor_config' and waits for a message
        from the server. If the message is 'AC', the sensor is configured
        as AC. If the message is 'DC', the sensor is configured as DC.
        """
        while self.sensor_configured == False:
            self.mqtt.check_msg()
            utime.sleep(1)
        #send ack to sensor_config_ack + id topic for 5 seconds
        start = utime.time()
        while utime.time() - start < 5:
            print('Sending ack to sensor_config_ack/' + self.client_id.decode("utf-8"))
            self.mqtt.publish('sensor_config_ack/' + self.client_id.decode("utf-8"), 'ack')
            utime.sleep(0.5)
        
