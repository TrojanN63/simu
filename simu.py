import uuid
import paho.mqtt.client as mqtt
import threading
import time
import os
import json
import math
import sys
import logging
import multiprocessing
import numpy as np
import pandas as pd

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="[SENSOR] %(asctime)s %(levelname)s - %(message)s",
)

suffix = 0
try:
    suffix = sys.argv[1]
except:
    pass

initial_value = 0
try:
    initial_value = int(sys.argv[2])
except:
    pass

number = f"984{suffix}"

cmdtopic = f"cmd2dev{number}"
devans = f"dev{number}ans"
devss = f"dev{number}ss"
deviceStatus = f"dev{number}status"
otaTopic = "OTAMQTT"
functions = {}

deviceFunctionModel = {
    "function": "IMU Sensor",
    "type": "sensor",
}

whoAmIResp = {
    "device": "DOIT Esp32 DevKit v1",
    "serviceType":"input",
    "deviceFunction": deviceFunctionModel,
    "deviceID": 110001373055524,
    "deviceIP": "192.168.1.4",
    "topics": [cmdtopic, devans, devss, deviceStatus],
    "implementedFunctionalities": {
        "updateFirmware": {
            "op": 25,
            "url": "hostName",
            "binLocation": "urlToFile",
            "md5": "hash",
        },
        "imuSendInit": {
            "op": 1,
            "simulationTime": "float",
            "frequence": "float",
            "sensorType": "",
        },
        "sensor_start": {
            "op": 3,
            "simulationTime": "float",
            "frequence": "float",
            "sensorType": "",
        },
        "imuSendStop": {"op": 22},
        "openLoopFesUpdate": {
            "op": 2,
            "m": "Channel String Vector",
            "t": "Ton Uint",
            "p": "Period Uint",
            "f": "fade time microsseconds",
        },
        "openLoopTonFreqUpdate": {"op": 18, "t": "Ton Uint", "p": "Period Uint"},
        "restart": {"op": 7},
        "stopOpenLoopFes": {"op": 8},
        "whoAmI": {"op": 9},
    },
}


def whoAmI():
    return json.dumps(whoAmIResp)

stopped = False
count = initial_value
def imuloop(args):
    global count
    global stopped
    data = pd.read_csv("IMU_hip_r.csv")
    for i in range(int(args[0]) * int(args[1])):
        angle = np.rad2deg(np.arctan2(data['ay'][count], data['ax'][count]))
        logging.info("[ANGLE] Cos for angle %s is %s", angle, data['ax'][count])
        logging.info("[ANGLE] Sin for angle %s is %s", angle, data['ay'][count])
        tosend = f"{data['ax'][count]},{data['ay'][count]},{data['az'][count]},{data['gx'][count]},{data['gy'][count]},{data['gz'][count]},{data['mx'][count]},{data['my'][count]},{data['mz'][count]}"        
        count += 1
        client.publish(devss, tosend)
        time.sleep(1 / int(args[1]))
        if count > 169:
            count = 0
        if stopped:
            break

def imuSendInit(doc):
    global stopped
    stopped = False
    threading.Thread(
        target=imuloop,
        args=((float(doc["simulationTime"]), float(doc["frequence"])),),
    ).start()    
    client.publish(devans, "Command Sucessful")

def sensor_start(doc):
    global stopped
    stopped = False
    threading.Thread(
        target=imuloop,
        args=((float(doc["simulationTime"]), float(doc["frequence"])),),
    ).start()    
    client.publish(devans, "Command Sucessful")

def imuSendStop(doc):
    global stopped
    stopped = True

def openLoopFesUpdate(doc):
    client.publish(devans, "Command Sucessful")


def on_connect(client, userdata, flags, rc):
    logging.info("Sensor %s connected with result code %s", devans, str(rc))
    client.subscribe(cmdtopic)
    client.subscribe("getServices")
    client.publish("newdev", whoAmI())
    client.publish(deviceStatus, "Online")


def on_message(client, userdata, msg):
    try:
        logging.info(f"Received message from {msg.topic} with payload {str(msg.payload)}")

        if "getServices" in msg.topic:
            client.publish("newdev", whoAmI())
        if cmdtopic in msg.topic:
            doc = json.loads(msg.payload)
            try:
                functions[doc["op"]](doc)
            except:
                pass
            # fazer uma lista de dispositivos lá em cima, preencher o dicionário e enviar para o unity (testsetUnityTopics(returndict))
    except:
        pass


client = mqtt.Client(client_id=f"sensor-{uuid.uuid4()}")
client.on_connect = on_connect
client.on_message = on_message
client.will_set(deviceStatus, "Offline")

functions[9] = whoAmI
functions[1] = imuSendInit
functions[2] = openLoopFesUpdate
functions[22] = imuSendStop
functions[3] = sensor_start

client.connect("127.0.0.1", 1883, 15)
# t1 = threading.Thread(target=client.loop_forever)
# t1.start()
# counter = 0
# time.sleep(1)

terminate_signal = multiprocessing.Value("b", False)

if __name__ == "__main__":
    while not terminate_signal.value:
        try:
            logging.info("Sensor running")
            client.loop_forever()
        except KeyboardInterrupt:
            client.disconnect()
            terminate_signal.value = True
    logging.info("Sensor terminated")
    sys.exit(0)