import eventlet
eventlet.monkey_patch()
import logging, sys
import json, os
from flask import Flask, render_template
from flask_mqtt import Mqtt
from flask_socketio import SocketIO
from flask_bootstrap import Bootstrap
from CostElectricity import costElectricity



logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET'] = 'my secret key'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['MQTT_BROKER_URL'] = '192.168.1.200'
app.config['MQTT_BROKER_PORT'] = 1883
app.config['MQTT_CLIENT_ID'] = 'APP_SERVER'
app.config['MQTT_CLEAN_SESSION'] = True
app.config['MQTT_USERNAME'] = 'pi'
app.config['MQTT_PASSWORD'] = 'nairda'
app.config['MQTT_KEEPALIVE'] = 5
app.config['MQTT_TLS_ENABLED'] = False
app.config['MQTT_LAST_WILL_TOPIC'] = 'home/lastwill'
app.config['MQTT_LAST_WILL_MESSAGE'] = 'bye'
app.config['MQTT_LAST_WILL_QOS'] = 2

class backgroundTask():
    def __init__(self):
        self.sendConfigToSensor = False

    def stop_sendConfigToSensor(self):
        logging.debug('stop_sendConfigToSensor called')
        self.sendConfigToSensor = False

    def start_sendConfigToSensor(self, json_data):
        self.sendConfigToSensor = True
        data = json.loads(json_data)
        logging.info("Starting background thread to send config to sensor")
        while self.sendConfigToSensor:
            logging.info("Running loop to send config to sensor")
            logging.info('Sending config to sensor %s', data['sensor_type'] + ',' + data['voltage'])
            mqtt.publish('sensor_config/' + data['sensor_id'], data['sensor_type'] + ',' + data['voltage'])
            socketio.sleep(1)
    
    def update_cost_electricity(self):
        
        while True:
            costElectricity.load_current_data()
            logging.debug("Reloading cost electricity data :", costElectricity.current_data)
            #notify socket new data
            socketio.emit('cost_electricity', costElectricity.current_data)
            socketio.sleep(60)

class handleSensors():
    def __init__(self):
        self.JSON_FILE = 'sensors.json'
        self.list_of_sensors = set()
        self.sensors_data = None
    
    def read_saved_sensors(self):
        if os.path.isfile(self.JSON_FILE):
            with open(self.JSON_FILE, "r") as f:
                self.sensors_data = json.load(f)
                print(self.sensors_data)
        else:
            with open(self.JSON_FILE, "w", encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            logging.debug("No sensors found")

    def add_sensor(self, sensor):
        with open(self.JSON_FILE, "r") as f:
            json_sensors = json.load(f)
            sensorFound = False
            for sensor_id, sensor_data in json_sensors.items():
                print("sensor_id: ", sensor_id, "sensor_type: ", sensor_data["sensor_type"])

            if not sensorFound:
                logging.debug("New sensor added: %s", sensor["sensor_id"])
                json_sensors[sensor["sensor_id"]] = sensor
                self.sensors_data = json_sensors
                with open(self.JSON_FILE, "w", encoding='utf-8') as f:
                    json.dump(json_sensors, f, ensure_ascii=False, indent=4)
                #after adding, subscribe to watts topic
                mqtt.subscribe('watts/' + sensor["sensor_id"])
    
    def remove_sensor(self, sensor_id):
        with open(self.JSON_FILE, "r") as f:
            json_sensors = json.load(f)
            json_sensors.pop(sensor_id)
            self.sensors_data = json_sensors
            with open(self.JSON_FILE, "w", encoding='utf-8') as f:
                json.dump(json_sensors, f, ensure_ascii=False, indent=4)
            #after removing, unsubscribe to watts topic
            mqtt.unsubscribe('watts/' + sensor_id)

backgroundTask = backgroundTask()
handleSensors = handleSensors()
costElectricity = costElectricity()

mqtt = Mqtt(app)
socketio = SocketIO(app)
bootstrap = Bootstrap(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_sensor')
def add_sensor():
    return render_template('add_sensor.html')

@app.route('/sensors')
def sensors():
    print("sensors " + str(handleSensors.sensors_data))
    return render_template('sensors.html', sensors=handleSensors.sensors_data)

@app.route('/sensors/<path:sensor_id>')
def sensor(sensor_id):
    return render_template('display_sensor_data.html', data=handleSensors.sensors_data[sensor_id])


@socketio.on('publish')
def handle_publish(json_str):
    data = json.loads(json_str)
    mqtt.publish(data['topic'], data['message'], data['qos'])


@socketio.on('subscribe')
def handle_subscribe(json_str):
    data = json.loads(json_str)
    mqtt.subscribe(data['topic'], data['qos'])

@socketio.on('submit_sensor')
def handle_submit_sensor(json_str):
    data = json.loads(json_str)
    logging.info("New sensor added: %s", data['sensor_id'])
    mqtt.publish('ack/' + data['sensor_id'], "ack", 0)
    backgroundTask.start_sendConfigToSensor(json_str)
    handleSensors.add_sensor(data)

@socketio.on('stop_sending_config')
def handle_stop_sending_config():
    backgroundTask.stop_sendConfigToSensor()

@socketio.on('reset_sensor')
def handle_reset_sensor(str):
    logging.debug("Reset sensor: %s", str)
    mqtt.publish('restart/' + str, "restart", 0)

@socketio.on('calibrate_sensor')
def handle_calibrate_sensor(str):
    logging.debug("Recalibrating sensor: %s", str)
    mqtt.publish('calibrate/' + str, "reset", 0)

@socketio.on('delete_sensor')
def handle_delete_sensor(str):
    logging.debug("Deleting sensor: %s", str)
    handleSensors.remove_sensor(str)
    mqtt.publish('reset/' + str, "reset", 0)

@socketio.on('unsubscribe_all')
def handle_unsubscribe_all():
    mqtt.unsubscribe_all()

@socketio.on('unsubscribe_sensor_id')
def handle_unsubscribe_sensor_id():
    mqtt.unsubscribe('clientID/broker')

@socketio.on('connect')
def handle_connect():
    logging.info("Client connected")
    socketio.start_background_task(backgroundTask.update_cost_electricity)


@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    data = dict(
        topic=message.topic,
        payload=message.payload.decode(),
        qos=message.qos,
    )
    print("message received: ", data)
    socketio.emit('mqtt_message', data=data)

@mqtt.on_connect()
def handle_mqtt_connect(client, userdata, flags, rc):
    for sensor, data in handleSensors.sensors_data.items():
        logging.debug("Subscribing to sensor: %s", sensor)
        mqtt.subscribe('watts/' + sensor, 0)

@mqtt.on_log()
def handle_logging(client, userdata, level, buf):
    print(level, buf)
    pass

if __name__ == '__main__':
    handleSensors.read_saved_sensors()
    costElectricity.load_current_data()
    socketio.run(app, host='localhost', port=5000, use_reloader=False, debug=True)