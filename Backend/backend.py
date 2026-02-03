
# ------------------------------------------ Backend Code for receiving data ------------------------------------------
import paho.mqtt.client as mqtt
import json

BROKER = "test.mosquitto.org"
PORT = 1883
TOPIC = "IC.embedded/Zenith/bed_sensor"

# This "callback" function triggers whenever a message arrives
# Not called directly by us as it is called by the MQTT client library automatically
def on_message(client, userdata, message):
    # 1. Decode the bytes back into a string
    payload = str(message.payload.decode("utf-8"))
    
    # 2. Parse the JSON string back into a Python dictionary
    data = json.loads(payload)
    
    # 3. Logic to determine fall risk
    if abs(data['accel_z']) < 2.0:
        print("ALERT: Possible Fall Detected!")
    else:
        print(f"Status Normal: {data['accel_z']}")

# Setup Subscriber
client = mqtt.Client()
client.on_message = on_message

# Connect to Broker and subscribe to topic
client.connect(BROKER, PORT)
client.subscribe(TOPIC)

print("Waiting for sensor data...")
client.loop_forever() # Keeps the script running to listen for messages