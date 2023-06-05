import paho.mqtt.client as PahoMQTT
import time
import numpy as np
import json
import cherrypy
from colorama import Fore, Style
from utils.ErrorHandler import BrokerError

class Blood_Pressure_Analysis:
        
        def __init__(self,
                 client_id,
                 topic_cat="pressure",
                 topic_measurement='measurements',
                 topic_report="reports",
                 topic_warning="warnings",
                 systolic_desc_bound={"lower_bound":90, "upper_bound":140},
                 diastolic_desc_bound={"lower_bound":60, "upper_bound":90},
                 analysis_window=20,
                 qos=2,
                 msg_broker="localhost",
                 msg_broker_port=1883):
            
            self.clientID = client_id        
            # Instance of PahoMQTT Client
            self.paho_mqtt = PahoMQTT.Client(self.clientID, True) 
            
            # Register the Callback
            self.paho_mqtt.on_connect = self.on_connect
            self.paho_mqtt.on_message = self.on_message

            # MQTT Broker URL
            self.msg_broker = msg_broker 
            self.msg_broker_port = msg_broker_port

            # QoS
            self.QoS = qos

            # Topics
            self.topic_cat = topic_cat
            self.topic_measurement = topic_measurement
            self.topic_report = topic_report
            self.topic_warning = topic_warning

            # Diastolic Data
            self.diastolic = np.array([])
            self.diastolic_max = 0
            self.diastolic_min = 0
            
            # Systolic Data
            self.systolic = np.array([])
            self.systolic_max = 0
            self.systolic_min = 0

            # Measurement Value

            self.systolic_desc_bound = systolic_desc_bound
            self.diastolic_desc_bound = diastolic_desc_bound
            self.analysis_window = analysis_window

        def start(self):
            
            try: 
                # Connect MQTT Broker Connection
                self.paho_mqtt.connect(self.msg_broker, self.msg_broker_port)
                self.paho_mqtt.loop_start()
                self.paho_mqtt.subscribe(f"+/{self.topic_cat}/{self.topic_measurement}", self.QoS)

            except:
                raise BrokerError("Error Occured with Connecting MQTT Broker")
            
            print(f"{Fore.YELLOW}\n+ Blood Pressure Analysis : [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

        def stop(self):
            
            self.paho_mqtt.unsubscribe(f"+/{self.topic_cat}/{self.topic_measurement}")
            self.paho_mqtt.loop_stop()
            self.paho_mqtt.disconnect()

            print("----------------------------------------------------------------------------------\n+ Blood Pressure Analysis : [OFFLINE]")

        def on_connect(self, paho_mqtt, userdata, flags, rc):

            print(f"\n{Fore.YELLOW}+ Connected to '{self.msg_broker}' [code={rc}]{Fore.RESET}")

        def on_message(self, paho_mqtt , userdata, msg):

            self.user_id, _sens_cat, _sens_type = msg.topic.split('/')
            msg_body = json.loads(msg.payload.decode('utf-8'))

            print (f"{Fore.GREEN}{Style.BRIGHT}[SUB]{Style.NORMAL} {str(_sens_type).capitalize()} Recieved [{msg_body['bt']}]: Topic: '{msg.topic}' - QoS: '{str(msg.qos)}' - Message: {Fore.RESET}'{str(msg_body)}")

            # Current Systolic and Diastolic Values
            systolic_val = next((e for e in msg_body['e'] if e.get("n")=="systolic"), None)['v']
            diastolic_val = next((e for e in msg_body['e'] if e.get("n")=="diastolic"), None)['v']

            # Array of Systolic and Diastolic in Defined Window Size
            self.systolic = np.append(self.systolic,
                                     systolic_val)
            
            self.diastolic = np.append(self.diastolic,
                                      diastolic_val)
                        
            # High Systolic
            if int(systolic_val)>self.systolic_desc_bound['upper_bound']:
                warn_msg = [
                                {"n":"Systolic High", "v":systolic_val}
                            ]
                self.publish_warnings(warn_msg)

            # Low Systolic
            elif int(systolic_val)<self.systolic_desc_bound['lower_bound']:
                warn_msg = [
                                {"n":"Systolic Low", "v":systolic_val}
                            ]
                self.publish_warnings(warn_msg)

            # High Diastolic
            if int(diastolic_val)>self.diastolic_desc_bound['upper_bound']:
                warn_msg = [
                                {"n":"Diastolic High", "v":diastolic_val}
                            ]
                self.publish_warnings(warn_msg)

            # Low Diastolic
            elif int(diastolic_val)<self.diastolic_desc_bound['lower_bound']:
                warn_msg = [
                                {"n":"Diastolic Low", "v":diastolic_val}
                            ]
                self.publish_warnings(warn_msg)		

        def publish_warnings(self, msg):
                        
            timestamp = int(time.time())

            # Message Publish SenML Format
            msg_form = {
                        "bn":f"{self.msg_broker}:{self.msg_broker_port}/{self.user_id}/{self.topic_cat}/{self.topic_warning}",
                        "id":self.user_id,
                        "bt":timestamp,
                        "u":"mmHg",
                        "e": msg
                        }
            
            self.paho_mqtt.publish(f"{self.user_id}/{self.topic_cat}/{self.topic_warning}", json.dumps(msg_form), self.QoS)

            print(f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}[PUB]{Style.NORMAL} - Warning Sent:{Fore.RESET}{msg_form}")	

        def publish_report(self, msg):

            timestamp = int(time.time())

            # Message Publish SenML Format
            msg_form = {
                        "bn":f"{self.msg_broker}:{self.msg_broker_port}/{self.user_id}/{self.topic_cat}/{self.topic_report}",
                        "id":self.user_id,
                        "bt":timestamp,
                        "u":"mmHg",
                        "e": msg
                        }
            
            self.paho_mqtt.publish(f"{self.user_id}/{self.topic_cat}/{self.topic_report}", json.dumps(msg_form), self.QoS)

            print(f"{Fore.BLUE}{Style.BRIGHT}[PUB]{Style.NORMAL} - Report Sent: {Fore.RESET}{msg_form}")
                
        def gen_report(self):

            # Generate Reports with Certain Amount of Data - Prev Version Caused 'list index out of range'
            if self.diastolic.size>int(self.analysis_window/5) and self.systolic.size>int(self.analysis_window/5):

                rep_msg = [
                           {"n":'max_diastolic', "v":np.max(self.diastolic[-int(self.analysis_window/5):])}, 
                           {"n":'min_diastolic', "v":np.min(self.diastolic[-int(self.analysis_window/5):])},
                           {"n":'mean_diastolic', "v":np.mean(self.diastolic[-int(self.analysis_window/5) :])},
                           {"n":'max_systolic', "v":np.max(self.systolic[-int(self.analysis_window/5) :])}, 
                           {"n":'min_systolic', "v":np.min(self.systolic[-int(self.analysis_window/5) :])},
                           {"n":'mean_systolic', "v":np.mean(self.systolic[-int(self.analysis_window/5) :])}
                           ]
                
                self.publish_report(rep_msg)

                # Delete Cached Pressure Data for Next Report
                self.diastolic = np.array([])
                self.systolic = np.array([])

        def temp_window(self):
            return self.analysis_window

        # Function to Update Analysis Window
        def update_window(self, new_window_val):
            self.analysis_window = new_window_val 

        # REST API

        def GET(self,*uri, **params):

            return "Hello World"


if __name__ == "__main__":
    
    bp_analysis = Blood_Pressure_Analysis(client_id="BP-ANALYSIS",
                                            topic_cat="pressure",
                                            topic_measurement='measurements',
                                            topic_report="reports",
                                            topic_warning="warnings",
                                            systolic_desc_bound={"lower_bound":90, "upper_bound":140},
                                            diastolic_desc_bound={"lower_bound":60, "upper_bound":90},
                                            analysis_window=20,
                                            qos=2,
                                            msg_broker="localhost",
                                            msg_broker_port=1883)

    bp_analysis.start()

    while True:
        bp_analysis.gen_report()
        time.sleep(bp_analysis.temp_window())

    bp_analysis.stop()