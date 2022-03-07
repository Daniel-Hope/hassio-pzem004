
print("Initialising")

import serial
import ssl
import time
import json
import sys


def readConfig():
  f = open("/data/options.json", "r")
  config = f.read()
  f.close()
  print("Loading config: " + config)
  return json.loads(config)


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


## Commands

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
  


if __name__ == '__main__':
  config = readConfig()
  print("Initializing pzem", flush=True)
  
  pzem = serial.Serial(config['serial'], 9600, timeout=5)
  ip = 'C0A8010100'
  setAddr(pzem, ip)


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

    print("Waiting 60 seconds before next loop\n", flush=True)

    loopCounter += 1
    time.sleep(60)
