
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


if __name__ == '__main__':
  config = readConfig()

  loopCounter = 1
  while True:
    print("Starting read loop " + str(loopCounter))
    
    print("Waiting 60 seconds before next loop\n")
    sys.stdout.flush()
    loopCounter += 1
    time.sleep(60)
    

  
