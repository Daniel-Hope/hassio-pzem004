
print("Initialising")

import serial
import ssl
import time
import json
import sys
import os
import signal
import paho.mqtt.client as mqtt

POLL_INTERVAL = 60
SENSOR_PREFIX = "PZEM-004 "
MQTT_QOS = 0
AVAILIBILITY_TOPIC_POSTFIX = "/bridge/state"


class GracefulKiller:
  kill_now = False

  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)

  def exit_gracefully(self,signum, frame):
    self.kill_now = True


def readConfig():
  print(os.environ)
  f = open("/data/options.json", "r")
  config = f.read()
  f.close()
  print("Loading config: " + config)
  return json.loads(config)


## PZEM util


def createByteData(hexString):
  data = bytearray.fromhex(hexString)
  checkSum = 0
  for byte in data:
    checkSum += byte
  data.append(checkSum & 0x000000FF)
  return data


def writeData(pzem, data):
  print("Writing data: " + data.hex())
  bytesWritten = pzem.write(data)
  print("Bytes written: " + str(bytesWritten))


def readData(pzem):
  print("Reading data")
  data = pzem.read(7)
  print("Response: " + str(data))
  return data


## PZEM Commands

def setAddr(pzem, ip):
  print("Set address: " + ip)
  data = createByteData('B4' + ip)
  writeData(pzem, data)


# Return voltage like 230.2V
def readVoltage(pzem):
  print("Read Voltage")
  data = createByteData('B0' + ip)
  writeData(pzem, data)
  data = readData(pzem)
  voltage = 0.0
  voltage += data[1] * 255
  voltage += data[2]
  voltage += data[3] / 10
  return voltage


# Return current like 17.32A
def readCurrent(pzem):
  print("Read Current")
  data = createByteData('B1' + ip)
  writeData(pzem, data)
  data = readData(pzem)
  current = 0.0
  current += data[2]
  current += data[3] / 100
  return current


# Return power in 2200W
def readPower(pzem):
  print("Read Power")
  data = createByteData('B2' + ip)
  writeData(pzem, data)
  data = readData(pzem)
  power = 0
  power += data[1] * 255
  power += data[2]
  return power


# Return energy in 999999Wh
def readEnergy(pzem):
  print("Read Energy")
  data = createByteData('B3' + ip)
  writeData(pzem, data)
  data = readData(pzem)
  energy = 0
  energy += data[1] * 255 * 255
  energy += data[2] * 255
  energy += data[3]
  return energy
  


## MQTT 
# https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php

def onPublish(client, userdata, mid):
  print("Message published", flush=True)

def onConnect(client, userdata, flags, rc):
  print("Connected to mqtt broker", flush=True)

def onMessage(client, userdata, message):
  print("Why am I receiving messages", flush=True)

def onDisconnect(client, userdata, flags, rc):
  print("mqtt client disconnected", flush=True)

def onLog(client, userdata, level, buf):
  print(str(level) + ": " + str(buf), flush=True)



def createMqttClient(brokerURL, username, password):
  print("Connecting to mqtt broker: " + brokerURL, flush=True)
  urlParts = brokerURL.split(":")

  client = mqtt.Client("pzem-addon")
  client.username_pw_set(username, password=password)
  client.on_connect = onConnect
  client.on_message = onMessage
  client.on_publish = onPublish
  client.on_disconnect = onDisconnect
  client.on_log = onLog
  client.connect_async(urlParts[0], int(urlParts[1]), POLL_INTERVAL*5)
  client.loop_start()
  return client


def createDiscoveryPayload(baseTopic, sensorName, sensorIndex, deviceClass, unitOfMeasurement):
  return {
    "availability": [{"topic": baseTopic + AVAILIBILITY_TOPIC_POSTFIX}],
    "device": {
      "identifiers": [
        baseTopic + "_" + sensorIndex
      ],
      "manufacturer": "Peacefair",
      "model": "PZEM-004",
      "name": "PZEM-004 1",
      "sw_version": "pzem-004 to mqtt 0.0.11"
    },
    "device_class": deviceClass,
    "json_attributes_topic": baseTopic + "/" + sensorName, 
    "name": sensorName + " " + deviceClass,
    "state_topic": baseTopic + "/" + sensorName,
    "unique_id": baseTopic + "_" + sensorIndex + "_" + deviceClass,
    "unit_of_measurement": unitOfMeasurement,
    "value_template": "{{ value_json." + deviceClass + " }}"
  }


def sendDiscoveryMessages(mqttClient, baseTopic, sensorName, sensorIndex):
  configTopic = "homeassistant/sensor/" + sensorName + sensorIndex +"/battery/config"

  mqttClient.publish(
    baseTopic + "/" + sensorName,
    payload = json.dumps(createDiscoveryPayload(configTopic, sensorName, sensorIndex, "voltage", "V")),
    qos = MQTT_QOS
  )
  mqttClient.publish(
    baseTopic + "/" + sensorName,
    payload = json.dumps(createDiscoveryPayload(configTopic, sensorName, sensorIndex, "current", "A")),
    qos = MQTT_QOS
  )
  mqttClient.publish(
    baseTopic + "/" + sensorName,
    payload = json.dumps(createDiscoveryPayload(configTopic, sensorName, sensorIndex, "power", "W")),
    qos = MQTT_QOS
  )
  mqttClient.publish(
    baseTopic + "/" + sensorName,
    payload = json.dumps(createDiscoveryPayload(configTopic, sensorName, sensorIndex, "energy", "Wh")),
    qos = MQTT_QOS
  )



def sendStateMessage(mqttClient, baseTopic, state):
  print("Sending state messte: " + state, flush=True)
  mqttClient.publish(baseTopic + AVAILIBILITY_TOPIC_POSTFIX, payload = state, qos = 0)



if __name__ == '__main__':
  config = readConfig()
  print("Initializing pzem", flush=True)
  
  pzem = serial.Serial(config['serial'], 9600, timeout=5)
  ip = 'C0A8010100'
  setAddr(pzem, ip)

  mqttClient = createMqttClient(config["mqtt"]["broker"], config["mqtt"]["username"], config["mqtt"]["password"])
  baseTopic = config["mqtt"]["baseTopic"]

  sensorIndex = "1"
  sensorName = SENSOR_PREFIX + sensorIndex

  # Do a read from PZEM for the first time and discount it. Sometimes we get a 0 back instead of the actual reading.
  voltage = readVoltage(pzem)
  current = readCurrent(pzem)
  power = readPower(pzem)
  energy = readEnergy(pzem)

  # Send discovery messages
  sendDiscoveryMessages(mqttClient, baseTopic, sensorName, sensorIndex)

  # Send enabled state
  sendStateMessage(mqttClient, baseTopic, "online")

  killer = GracefulKiller()

  loopCounter = 1
  while True:
    print("Starting read loop " + str(loopCounter), flush=True)

    # Get data from pzem
    voltage = readVoltage(pzem)
    current = readCurrent(pzem)
    power = readPower(pzem)
    energy = readEnergy(pzem)
    
    print("---- Power Stats -----")
    print("Voltage: " + str(voltage) + "V")
    print("Current: " + str(current) + "A")
    print("Power: " + str(power) + "W")
    print("Energy: " + str(energy) + "Wh")
    print("----------------------")

    data = {}
    data["voltage"] = voltage
    data["current"] = current
    data["power"] = power
    data["energy"] = energy

    print("Sending data to mqtt", flush=True)

    mqttClient.publish(baseTopic + "/" + sensorName, payload=json.dumps(data), qos=MQTT_QOS)

    print("Waiting " + str(POLL_INTERVAL) + " seconds before next loop\n", flush=True)

    loopCounter += 1
    time.sleep(POLL_INTERVAL)

    if killer.kill_now:
      break
  
  print("Quitting gracefully", flush=True)
  sendStateMessage(mqttClient, baseTopic, "offline")


