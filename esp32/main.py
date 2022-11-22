# importing the required libraries
import utime
from acs712_cfg import ACS712
import ssd1306
from machine import Pin, SoftI2C, reset
from mqtt_cfg import MQTT
import network
import os


DISPLAY = ssd1306.SSD1306_I2C(128, 32, SoftI2C(sda=Pin(4), scl=Pin(5)))
SSID = 'MOVISTAR_9670'
PASSWORD = 'LyBfb9Y6Jy9aLtozkPd3'

MQTT_CLIENT = MQTT()

CURRENT_SENSOR = ACS712(34) #scale factor for 5A sensor is 185, fia 20A is 100, for 30A is 66

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

def display_watts(watts):
    DISPLAY.clear()
    DISPLAY.text("Watts is:", 0, 0)
    DISPLAY.text(str(watts) + " Watts", 0, 10)
    DISPLAY.show()

def display_message(message):
    DISPLAY.clear()
    for i in range(0, len(message), 16):
        DISPLAY.text(message[i:i+16], 0, i)
    DISPLAY.text(message, 0, 0)
    DISPLAY.show()

def subscribe_callback(topic, message):
    print('Received message on topic ' + topic.decode("utf-8") + ': ' + message.decode("utf-8"))
    if topic.decode("utf-8") == 'sensor_config/' + MQTT_CLIENT.client_id.decode("utf-8"):
        CURRENT_SENSOR.set_sensor_config(message.decode("utf-8"))
        if CURRENT_SENSOR.referenceVoltage != 0:
            MQTT_CLIENT.sensor_configured = True
    elif topic.decode("utf-8") == 'ack/' + MQTT_CLIENT.client_id.decode("utf-8"):
        if message.decode("utf-8") == 'ack':
            MQTT_CLIENT.set_broker_acknowledged('True')
            MQTT_CLIENT.broker_acknowledged = True
            print('Broker acknowledged')
    elif topic.decode("utf-8") == 'reset/' + MQTT_CLIENT.client_id.decode("utf-8"):
        print('Resetting the device...')
        #TODO: now we delete cfg files from the filesystem
        for file in os.listdir():
            if file.endswith(".cfg"):
                os.remove(file)
        utime.sleep(2)
        reset()
    elif topic.decode("utf-8") == 'calibrate/' + MQTT_CLIENT.client_id.decode("utf-8"):
        CURRENT_SENSOR.calibrateSensorAC()
    elif topic.decode("utf-8") == 'restart/' + MQTT_CLIENT.client_id.decode("utf-8"):
        reset()

def btn_handler(pin):
    """
    This function is called when the button is pressed.
    It will set broker_acknowledged to False.
    It will also reset the device.
    """
    MQTT_CLIENT.set_broker_acknowledged('False')
    print('Resetting the device...')
    utime.sleep(2)
    reset()

def main():
    #TODO: receive wifi and mqtt settings from a cfg file
    #internal_reset_btn = Pin(22, Pin.IN, Pin.PULL_UP)
    #internal_reset_btn.irq(trigger=Pin.IRQ_RISING, handler=btn_handler)
    display_message('Connecting to WiFi...')
    connect_wifi(SSID, PASSWORD)
    
    #display_message('Connecting to MQTT broker...')
    MQTT_CLIENT.connect()
    MQTT_CLIENT.mqtt.set_callback(subscribe_callback)
    if MQTT_CLIENT.is_broker_acknowledged() == False:
        MQTT_CLIENT.publish_clientID()
    
    #subscribe to reset topic
    MQTT_CLIENT.subscribe('reset/' + MQTT_CLIENT.client_id.decode("utf-8"))
    #subscribe to sensor_config topic to receive the sensor voltage
    MQTT_CLIENT.subscribe('sensor_config/' + MQTT_CLIENT.client_id.decode("utf-8"))

    display_message('Configuring sensor...')
    if CURRENT_SENSOR.is_sensor_configured() == False:
        MQTT_CLIENT.get_sensor_config_from_broker()
    
    #subscribe to restart esp32 topic
    MQTT_CLIENT.subscribe('restart/' + MQTT_CLIENT.client_id.decode("utf-8"))

    display_message('Calibrating...')
    CURRENT_SENSOR.calibrateSensorAC()

    #subscribe to calibrate topic
    MQTT_CLIENT.subscribe('calibrate/' + MQTT_CLIENT.client_id.decode("utf-8"))

    while True:
        MQTT_CLIENT.check_msg()
        watts, amps = CURRENT_SENSOR.getACWatts(logging=False)
        display_watts(watts)
        MQTT_CLIENT.publish('amps/' + MQTT_CLIENT.client_id.decode("utf-8"), str(amps))
        MQTT_CLIENT.publish('watts/' + MQTT_CLIENT.client_id.decode("utf-8"), str(watts))
        print('-----------------------')

if __name__ == "__main__":
    main()
