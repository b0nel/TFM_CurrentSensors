# importing the required libraries
import utime
from acs712_cfg import ACS712
import ssd1306
from machine import Pin, SoftI2C
from mqtt_cfg import MQTT
import network

DISPLAY = ssd1306.SSD1306_I2C(128, 32, SoftI2C(sda=Pin(4), scl=Pin(5)))
SSID = 'MOVISTAR_9670'
PASSWORD = 'LyBfb9Y6Jy9aLtozkPd3'

def connect_wifi(ssid, password):
    print('Connecting to WiFi...')
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while not wlan.isconnected():
        pass
    print('network config:', wlan.ifconfig())

def display_current(current):
    DISPLAY.clear()
    DISPLAY.text("Current is:", 0, 0)
    DISPLAY.text(str(current) + " Amps", 0, 10)
    DISPLAY.show()

def subscribe_callback(topic, message):
    print('Received message on topic ' + topic.decode("utf-8") + ': ' + message.decode("utf-8"))
    if message.decode("utf-8") == 'ack':
        MQTT_CLIENT.broker_acknowledged = True

def main():
    #TODO: receive wifi and mqtt settings from a cfg file
    current_sensor = ACS712(34, scale_factor=48)
    connect_wifi(SSID, PASSWORD)
    global MQTT_CLIENT
    MQTT_CLIENT = MQTT()
    MQTT_CLIENT.mqtt.set_callback(subscribe_callback)
    MQTT_CLIENT.publish_clientID()
    current_sensor.calibrateSensor()
    while True:
        current = current_sensor.readCurrent()
        display_current(current)
        MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/currentSensor', str(current))
        utime.sleep(1)

if __name__ == "__main__":
    main()
