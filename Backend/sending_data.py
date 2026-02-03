# ------------------------------------------ Raspberry Pi Code for sending data ------------------------------------------
import paho.mqtt.client as mqtt
import json
import time

# --- Configuration ---
BROKER = "test.mosquitto.org"
PORT = 1883
# Replace 'GROUP_NAME' with your actual group identifier
TOPIC = "Embedded/Zenith/bed_sensor" 

client = mqtt.Client()
# Establish connection to the MQTT broker
client.connect(BROKER, PORT)

print("Pi is sending data...")

try:
    while True:
        # 1. Capture your 9-DOF data (Placeholders for your sensor library)
        sensor_data = {
            "accel_x": 0.05,
            "accel_y": 0.1,
            "accel_z": -9.8, # Gravity
            "timestamp": time.time()
        }
        
        # 2. Convert dictionary to JSON string
        json_payload = json.dumps(sensor_data)
        
        # 3. Convert string to bytes and Publish
        # We use QoS 1 to ensure the message reaches the broker at least once
        client.publish(TOPIC, bytes(json_payload, 'utf-8'), qos=1)
        
        # Coursework rule: Do not send more than 1 message per second
        time.sleep(1) 

except KeyboardInterrupt:
    client.disconnect()
