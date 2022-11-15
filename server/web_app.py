from flask import Flask, render_template
import json

#cfg stuff
JSON_FILE = 'clients.json'
#end cfg stuff


app = Flask(__name__)

@app.route('/')
def index():
    return 'This is a web app'

@app.route('/sensors')
def list_sensors():
    json_clients = list()
    with open(JSON_FILE, "r") as f:
        json_clients = json.load(f)
    
    return render_template('sensors.html', sensors=json_clients["clients"])

@app.route('/sensors/<path:sensorid>')
def sensor(sensorid):
    return 'This is sensor ' + sensorid


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)