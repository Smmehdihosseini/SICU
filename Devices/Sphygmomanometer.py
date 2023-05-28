import paho.mqtt.client as PahoMQTT
import time
import random
import json
from colorama import Fore, Style
from utils.ErrorHandler import DatabaseError, BrokerError

class Sphygmomanometer:

    def __init__(self,
                 user_id,
                 topic_cat="pressure",
                 topic_measurement="measurements",
                 systolic_threshold=90,
                 diastolic_threshold=60,
                 prob=0.9,
                 sample_freq=5,
                 qos=2,
                 msg_broker="localhost",
                 msg_broker_port=1883):
            
        self.user_id = user_id

        self.clientID = str(self.user_id+"-SPD")        
        # Instance of PahoMQTT Client
        self.paho_mqtt = PahoMQTT.Client(self.clientID, True) 
        
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

        self.ss_threshold = systolic_threshold
        self.ds_threshold = diastolic_threshold
        self.prob = prob
        self.sample_freq = sample_freq

    def start(self):
            
        try: 
            # Connect  MQTT Broker Connection
            self.paho_mqtt.connect(self.msg_broker, self.msg_broker_port)
            self.paho_mqtt.loop_start()

        except:
            raise BrokerError("Error Occured with Connecting MQTT Broker")
        
        print(f"{Fore.YELLOW}\n+ Sphygmomanometer Sensor: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

    def stop(self):
            
        self.paho_mqtt.loop_stop()
        self.paho_mqtt.disconnect()

        print("----------------------------------------------------------------------------------\n+ Sphygmomanometer Sensor: [OFFLINE]")

    def publish_measurements(self, msg):

        # Message Publish SenML Format

        timestamp = int(time.time())

        msg_form = {
                    "bn":f"{self.msg_broker}:{self.msg_broker_port}/{self.user_id}/{self.topic_cat}/{self.topic_measurement}",
                    "bt":timestamp,
                    "u":"mmHg",
                    "e": msg
                    }
        
        self.paho_mqtt.publish(f"{self.user_id}/{self.topic_cat}/{self.topic_measurement}", json.dumps(msg_form), 2)

        print(f"{Fore.GREEN}{Style.BRIGHT}[PUB]{Style.NORMAL} - Measurement Sent:{Fore.RESET}{msg_form}")

    def on_connect(self, paho_mqtt, userdata, flags, rc):

        print(f"\n{Fore.YELLOW}+ Connected to '{self.msg_broker}' [code={rc}]{Fore.RESET}")

    def get_measurements(self):

        if random.random() < self.prob:
            ss = random.randint(self.ss_threshold, 140)

        else:

            if random.random()>=0.5:
                ss = random.randint(50, self.ss_threshold-1)

            else:
                ss = random.randint(141, 150)
        
        if random.random() < self.prob:
            ds = random.randint(self.ds_threshold, 90)

        else:

            if random.random()>=0.5:
                ds = random.randint(50, self.ds_threshold-1)
            else:
                ds = random.randint(91, 100)

        measurement = [
                        {"n":"systolic", "v":ss},
                        {"n":"diastolic", "v":ds}
                      ]       
        
        return measurement
    
    def sleep(self):
        return self.sample_freq


if __name__ == "__main__":

    sphy_dev = Sphygmomanometer(user_id="P300",
                 topic_cat="pressure",
                 topic_measurement="measurements",
                 systolic_threshold=90,
                 diastolic_threshold=60,
                 prob=0.9,
                 sample_freq=5,
                 qos=2,
                 msg_broker="localhost",
                 msg_broker_port=1883)

    sphy_dev.start()

    while True:
        measurement = sphy_dev.get_measurements()
        sphy_dev.publish_measurements(measurement)
        time.sleep(sphy_dev.sleep())

    sphy_dev.stop()
