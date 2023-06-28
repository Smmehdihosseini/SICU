import paho.mqtt.client as PahoMQTT
import time
import scipy.io
import numpy as np
import neurokit2 as nk
import json 
import random
import gzip
import base64
from colorama import Fore, Style
from utils.ErrorHandler import DatabaseError, BrokerError

class Electrocardiogram:

    def __init__(self,
                 user_id,
                 topic_cat="ecg",
                 topic_measurement="measurements",
                 sampling_rate=1000,
                 duration=60,
                 tachycardia_threshold=100,
                 bradycardia_threshold=60,
                 prob=0.9,
                 sample_freq=1,
                 qos=2,
                 msg_broker="localhost",
                 msg_broker_port=1883):
            
        

        self.user_id = user_id

        self.clientID = str(self.user_id+"-ECGD")
        
        # Instance of PahoMQTT Client with Max Payload Size
        self.paho_mqtt = PahoMQTT.Client(self.clientID, True)
        self.paho_mqtt.max_payload_size = 5000  # Set maximum payload size
        
        # Register the Callback
        self.paho_mqtt.on_connect = self.on_connect

        # MQTT Broker URL
        self.msg_broker = msg_broker 
        self.msg_broker_port = msg_broker_port

        # QoS
        self.QoS = qos

        # Topic
        self.topic_cat = topic_cat
        self.topic_measurement = topic_measurement

        # Measurement Value
        self.duration = duration
        self.sampling_rate = sampling_rate
        self.tachycardia_threshold = tachycardia_threshold
        self.bradycardia_threshold = bradycardia_threshold
        self.prob = prob
        self.sample_freq = sample_freq

    def start(self):

        try: 
            # MQTT Broker Connection
            self.paho_mqtt.connect(self.msg_broker, self.msg_broker_port)
            self.paho_mqtt.loop_start()

        except:
            raise BrokerError("Error Occured with Connecting MQTT Broker")
        
        print(f"{Fore.YELLOW}\n+ Electrocardiogram Sensor: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

    def stop(self):

        self.paho_mqtt.loop_stop()
        self.paho_mqtt.disconnect()

        print("----------------------------------------------------------------------------------\n+ Electrocardiogram Sensor: [OFFLINE]")

    def publish_measurements(self, msg):

        # Message Publish SenML Format

        timestamp = int(time.time())

        msg_form = {
                    "bn":f"{self.msg_broker}:{self.msg_broker_port}/{self.user_id}/{self.topic_cat}/{self.topic_measurement}",
                    "bt":timestamp,
                    "u":"mm",
                    "e": [
                          {"n":"ecg_seg", "v":msg.tolist()}
                        ]
                    }
        
        self.paho_mqtt.publish(f"{self.user_id}/{self.topic_cat}/{self.topic_measurement}", json.dumps(msg_form), self.QoS)

        print(f"{Fore.GREEN}{Style.BRIGHT}[PUB]{Style.NORMAL} - Measurement Sent:{Fore.RESET}{msg_form}")

    def on_connect(self, paho_mqtt, userdata, flags, rc):

        print(f"\n{Fore.YELLOW}+ Connected to '{self.msg_broker}' [code={rc}]{Fore.RESET}")

    def get_measurements(self):

        if random.random() < self.prob:
            heart_rate = random.randint(self.bradycardia_threshold , self.tachycardia_threshold)
        else:
            if random.random()>=0.5:
                heart_rate = random.randint(self.bradycardia_threshold-20, self.bradycardia_threshold-1)
            else:
                heart_rate = random.randint(self.tachycardia_threshold-1, self.tachycardia_threshold+20)
        
        # Generate ECG Signal
        ecg_sec = nk.ecg_simulate(duration=self.duration, sampling_rate=self.sampling_rate, heart_rate=heart_rate) 

        return ecg_sec
    
    def sleep(self):
        return self.sample_freq
    
if __name__ == "__main__":

    ECG = Electrocardiogram(user_id="P300",
                            topic_cat="ecg",
                            topic_measurement="measurements",
                            sampling_rate=1000,
                            duration=60,
                            tachycardia_threshold=100,
                            bradycardia_threshold=60,
                            sample_freq=1,
                            qos=2,
                            msg_broker="localhost",
                            msg_broker_port=1883)

    ECG.start()

    i = 0
    while True:
        i = 0
        measurement = ECG.get_measurements()
        while i < 60:
            ECG.publish_measurements(measurement[i*ECG.sampling_rate:(i+1)*ECG.sampling_rate])
            time.sleep(ECG.sleep())
            i += 1

    ECG.stop()