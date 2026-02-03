import json
import time
import random
import paho.mqtt.client as mqtt

BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC = "IC.embedded/Zenith/bed_sensor"

client = mqtt.Client()
client.connect(BROKER, PORT)

print("Fake sensor publishing...")

while True:
    # Simulate accelerometer Z-axis
    accel_z = random.uniform(0.5, 9.8)

    data = {
        "accel_z": accel_z
    }

    payload = json.dumps(data)
    client.publish(TOPIC, payload)

    print("Published:", payload)
    time.sleep(2)
