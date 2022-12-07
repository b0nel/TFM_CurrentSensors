# importing the required libraries
import utime
from acs712_cfg import ACS712, SCALES_FACTOR
from lib.ssd1306 import SSD1306_I2C
from machine import Pin, SoftI2C, reset
from mqtt_cfg import MQTT
import network
import os
from zmpt101b import ZMPT101B


DISPLAY = SSD1306_I2C(128, 32, SoftI2C(sda=Pin(4), scl=Pin(5)))
SSID = 'MOVISTAR_9670'
PASSWORD = 'LyBfb9Y6Jy9aLtozkPd3'

MQTT_CLIENT = MQTT()

CURRENT_SENSOR = ACS712(34)
VOLTAGE_SENSOR = ZMPT101B(33)

RELAY = Pin(26, Pin.OUT)

SENSING = True

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

def check_sensor_type(sensor_type):
    modules = ['5A', '20A', '30A']
    for type in modules:
        if sensor_type == type:
            print("[set_sensor_config]Sensor type valid")
            return True
            
    return False

def process_received_config(config_str):
    try:
        sensor_type, sensor_voltage, load_type = config_str.split(',')
        print("[set_sensor_config]Sensor type: ", sensor_type, "Sensor voltage: ", sensor_voltage, "Load type: ", load_type)
        if check_sensor_type(sensor_type) and (float(sensor_voltage) > 0):
            #save sensor config in flash
            with open('sensor_configured.cfg', 'w') as file:
                file.write(str(config_str))
            CURRENT_SENSOR.set_sensor_config(sensor_type, load_type, sensor_voltage)
            VOLTAGE_SENSOR.set_sensor_config(sensor_voltage)
            print("[set_sensor_config]Sensor configured. Sensor type: ", sensor_type, "Sensor voltage: ", sensor_voltage)
            return True
                
        else:
            print("[set_sensor_config]Invalid sensor config received.")
            return False
    except ValueError:
        print("[set_sensor_config]Invalid sensor config format received.")
        return False

def subscribe_callback(topic, message):
    print('Received message on topic ' + topic.decode("utf-8") + ': ' + message.decode("utf-8"))
    if topic.decode("utf-8") == 'sensor_config/' + MQTT_CLIENT.client_id.decode("utf-8"):
        if process_received_config(message.decode("utf-8")):
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
        CURRENT_SENSOR.calibrateSensorAC(RELAY)
        VOLTAGE_SENSOR.calibration(RELAY)
    elif topic.decode("utf-8") == 'restart/' + MQTT_CLIENT.client_id.decode("utf-8"):
        reset()
    elif topic.decode("utf-8") == 'relay/' + MQTT_CLIENT.client_id.decode("utf-8"):
        global SENSING
        if message.decode("utf-8") == 'on':
            print("Turning on relay and enabling sensing")
            SENSING = True
            RELAY.value(1)
        elif message.decode("utf-8") == 'off':
            print("Turning off relay and disabling sensing")
            SENSING = False
            RELAY.value(0)
        else:
            print('Unknown command: ' + message.decode("utf-8") + ' on topic ' + topic.decode("utf-8"))

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

def init():
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
    
    #Init value for relay is always on, i.e, after a reset we want the relay to be on
    RELAY.value(1)
    SENSING = True
    
    #subscribe to reset topic
    MQTT_CLIENT.subscribe('reset/' + MQTT_CLIENT.client_id.decode("utf-8"))
    #subscribe to sensor_config topic to receive the sensor voltage
    MQTT_CLIENT.subscribe('sensor_config/' + MQTT_CLIENT.client_id.decode("utf-8"))
    #subscribe to relay topic to power on/off the devices
    MQTT_CLIENT.subscribe('relay/' + MQTT_CLIENT.client_id.decode("utf-8"))

    display_message('Configuring sensor...')
    if CURRENT_SENSOR.is_sensor_configured() == False or VOLTAGE_SENSOR.is_sensor_configured() == False:
        MQTT_CLIENT.get_sensor_config_from_broker()
    
    #subscribe to restart esp32 topic
    MQTT_CLIENT.subscribe('restart/' + MQTT_CLIENT.client_id.decode("utf-8"))

    display_message('Calibrating amp sensor...')
    CURRENT_SENSOR.calibrateSensorAC(RELAY)

    display_message('Calibrating voltage sensor...')
    VOLTAGE_SENSOR.calibration(RELAY)


    #subscribe to calibrate topic
    MQTT_CLIENT.subscribe('calibrate/' + MQTT_CLIENT.client_id.decode("utf-8"))

def main():
    init()

    while True:
        MQTT_CLIENT.check_msg()
        if SENSING == True:
            voltage = VOLTAGE_SENSOR.getVoltage()
            watts, amps = CURRENT_SENSOR.getACWatts(voltage_from_sensor=voltage, logging=False)
            display_watts(watts)
            MQTT_CLIENT.publish('voltage/' + MQTT_CLIENT.client_id.decode("utf-8"), str(voltage))
            MQTT_CLIENT.publish('amps/' + MQTT_CLIENT.client_id.decode("utf-8"), str(amps))
            MQTT_CLIENT.publish('watts/' + MQTT_CLIENT.client_id.decode("utf-8"), str(watts))
            print('-----------------------')
        else:
            print("Sensing is disabled")
            utime.sleep(1)

if __name__ == "__main__":
    main()
