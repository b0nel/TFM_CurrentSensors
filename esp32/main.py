# importing the required libraries
import utime
from acs712_cfg import ACS712
import ssd1306
from machine import Pin, SoftI2C, reset
from mqtt_cfg import MQTT
import network

DISPLAY = ssd1306.SSD1306_I2C(128, 32, SoftI2C(sda=Pin(4), scl=Pin(5)))
SSID = 'MOVISTAR_9670'
PASSWORD = 'LyBfb9Y6Jy9aLtozkPd3'

MQTT_CLIENT = MQTT()

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
    current_sensor = ACS712(34, scale_factor=48)
    internal_reset_btn = Pin(22, Pin.IN, Pin.PULL_UP)
    internal_reset_btn.irq(trigger=Pin.IRQ_RISING, handler=btn_handler)
    connect_wifi(SSID, PASSWORD)
    MQTT_CLIENT.connect()
    MQTT_CLIENT.mqtt.set_callback(subscribe_callback)
    if MQTT_CLIENT.is_broker_acknowledged() == False:
        MQTT_CLIENT.publish_clientID()
        MQTT_CLIENT.set_broker_acknowledged('True')
    current_sensor.calibrateSensorFast()
    while True:
        current = current_sensor.readCurrent()
        display_current(current)
        MQTT_CLIENT.publish(MQTT_CLIENT.client_id.decode("utf-8") + '/currentSensor', str(current))
        utime.sleep(1)

if __name__ == "__main__":
    main()
