
print("Initialising")

import serial
import ssl
import time
import json
import sys
import os
import paho.mqtt.client as mqtt

POLL_INTERVAL = 60


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


if __name__ == '__main__':
  config = readConfig()
  print("Initializing pzem", flush=True)
  
  pzem = serial.Serial(config['serial'], 9600, timeout=5)
  ip = 'C0A8010100'
  setAddr(pzem, ip)

  mqttClient = createMqttClient(config["mqtt"]["broker"], config["mqtt"]["username"], config["mqtt"]["password"])

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

    mqttClient.publish("pzem", payload=json.dumps(data), qos=1)

    print("Waiting " + str(POLL_INTERVAL) + " seconds before next loop\n", flush=True)


    loopCounter += 1
    time.sleep(POLL_INTERVAL)
