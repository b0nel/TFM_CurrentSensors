# importing the required libraries
import utime
from acs712_cfg import ACS712
import ssd1306
from machine import Pin, SoftI2C, reset
from mqtt_cfg import MQTT
import network
import os

SCALE_FACTOR_30A = (66  * 3.3) / 5
SCALE_FACTOR_20A = (100 * 3.3) / 5
SCALE_FACTOR_5A  = (185 * 3.3) / 5


DISPLAY = ssd1306.SSD1306_I2C(128, 32, SoftI2C(sda=Pin(4), scl=Pin(5)))
SSID = 'MOVISTAR_9670'
PASSWORD = 'LyBfb9Y6Jy9aLtozkPd3'

MQTT_CLIENT = MQTT()

CURRENT_SENSOR = ACS712(34, scale_factor=SCALE_FACTOR_5A) #scale factor for 5A sensor is 185, fia 20A is 100, for 30A is 66

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
    if topic.decode("utf-8") == MQTT_CLIENT.client_id.decode("utf-8") + '/sensor_config':
        CURRENT_SENSOR.set_sensor_configured(message.decode("utf-8"))
        MQTT_CLIENT.sensor_configured = True
        print('Sensor configured as ' + message.decode("utf-8"))
    elif topic.decode("utf-8") == MQTT_CLIENT.client_id.decode("utf-8") + '/ack':
        if message.decode("utf-8") == 'ack':
            MQTT_CLIENT.set_broker_acknowledged('True')
            MQTT_CLIENT.broker_acknowledged = True
            print('Broker acknowledged')
    elif topic.decode("utf-8") == MQTT_CLIENT.client_id.decode("utf-8") + '/reset':
        print('Resetting the device...')
        #TODO: now we delete cfg files from the filesystem
        for file in os.listdir():
            if file.endswith(".cfg"):
                os.remove(file)
        utime.sleep(2)
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
    
    display_message('Connecting to MQTT broker...')
    MQTT_CLIENT.connect()
    MQTT_CLIENT.mqtt.set_callback(subscribe_callback)
    if MQTT_CLIENT.is_broker_acknowledged() == False:
        MQTT_CLIENT.publish_clientID()

    display_message('Configuting sensor as DC or AC...')
    if CURRENT_SENSOR.is_sensor_configured() == False:
        MQTT_CLIENT.get_sensor_config_from_broker()
    
    #subscribe to reset topic
    MQTT_CLIENT.subscribe(MQTT_CLIENT.client_id.decode("utf-8") + '/reset')
    
    display_message('Dummy readings...')
    #dummy reads for 5 seconds
    CURRENT_SENSOR.calibrateSensor(5)
    display_message('Calibrating...')
    
    #discard previous readings and calibrate again
    CURRENT_SENSOR.calibrateSensor(30)
    while True:
        MQTT_CLIENT.check_msg()
        if CURRENT_SENSOR.is_DC():
            voltage = CURRENT_SENSOR.readSensor()
            amps = CURRENT_SENSOR.calculateCurrent(voltage, calibration=0.1)
            watts = CURRENT_SENSOR.calculateWatts(amps, voltage=12)
            display_watts(watts)
            MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/amps', str(amps))
            MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/watts', str(watts))
            print('-----------------------')
        elif CURRENT_SENSOR.is_AC():
            watts, amps = CURRENT_SENSOR.getWatts()
            display_watts(watts)
            MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/amps', str(amps))
            MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/watts', str(watts))
            print('-----------------------')
        else:
            #this should never happen at this point
            display_message('Sensor not configured')
            print('Sensor not configured, resetting the device...')
            utime.sleep(2)
            reset()
        #display_current(current)
        #print('Current is: ' + str(current) + ' Amps')
        #MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/currentSensor', str(current))
        #MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/watts', str(CURRENT_SENSOR.getWatts()))
        #watts = CURRENT_SENSOR.getWatts()
        #display_watts(watts)
        #print('Watts is: ' + str(watts) + ' Watts')
        #CURRENT_SENSOR.timeToReadVoltage()

if __name__ == "__main__":
    main()
