import paho.mqtt.client as PahoMQTT
import time
import numpy as np
import json
import cherrypy
from colorama import Fore, Style
from utils.ErrorHandler import BrokerError

class Oxygen_Analysis:
        
        exposed = True

        def __init__(self,
                 client_id,
                 topic_cat="oxygen",
                 topic_measurement='measurements',
                 topic_report="reports",
                 topic_warning="warnings",
                 ox_sat_threshold=90,
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
            
            # Oxygen Saturation Data
            self.ox_sat_level = np.array([])
            self.ox_sat_max = 0
            self.ox_sat_min = 0

            # Oxygen Conditions Values
            self.ox_sat_threshold = ox_sat_threshold
            self.analysis_window = analysis_window

        def start(self):
            
            try: 
                # Connect MQTT Broker Connection
                self.paho_mqtt.connect(self.msg_broker, self.msg_broker_port)
                self.paho_mqtt.loop_start()
                self.paho_mqtt.subscribe(f"+/{self.topic_cat}/{self.topic_measurement}", self.QoS)

            except:
                raise BrokerError("Error Occured with Connecting MQTT Broker")
            
            # Add Name of The Analysis to this Print
            print(f"{Fore.YELLOW}\n+ Oxygen Saturation Analysis : [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

        def stop(self):
            
            self.paho_mqtt.unsubscribe(f"+/{self.topic_cat}/{self.topic_measurement}")
            self.paho_mqtt.loop_stop()
            self.paho_mqtt.disconnect()

            print("----------------------------------------------------------------------------------\n+ Oxygen Saturation Analysis : [OFFLINE]")

        def on_connect(self, paho_mqtt, userdata, flags, rc):

            print(f"\n{Fore.YELLOW}+ Connected to '{self.msg_broker}' [code={rc}]{Fore.RESET}")

        def on_message(self, paho_mqtt , userdata, msg):

            self.user_id, _sens_cat, _sens_type = msg.topic.split('/')
            msg_body = json.loads(msg.payload.decode('utf-8'))

            print (f"{Fore.GREEN}{Style.BRIGHT}[SUB]{Style.NORMAL} {str(_sens_type).capitalize()} Recieved [{msg_body['bt']}]: Topic: '{msg.topic}' - QoS: '{str(msg.qos)}' - Message: {Fore.RESET}'{str(msg_body)}")

            # Current SpO2 Value
            ox_val = next((e for e in msg_body['e'] if e.get("n")=="spo2"), None)['v']

            # Array of SpO2 in Defined Window Size
            self.ox_sat_level = np.append(self.ox_sat_level,
                                     ox_val)
   
            # Low Oxygen Saturation
            if int(ox_val)<self.ox_sat_threshold:
                warn_msg = [
                                {"n":"warning", "v":"SpO2 Low"},
                                {"n":"value", "v":ox_val}
                            ]
                self.publish_warnings(warn_msg)	

        def publish_warnings(self, msg):
                        
            timestamp = int(time.time())

            # Message Publish SenML Format
            msg_form = {
                        "bn":f"{self.msg_broker}:{self.msg_broker_port}/{self.user_id}/{self.topic_cat}/{self.topic_warning}",
                        "id":self.user_id,
                        "bt":timestamp,
                        "u":"%",
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
                        "u":"%",
                        "e": msg
                        }
            
            self.paho_mqtt.publish(f"{self.user_id}/{self.topic_cat}/{self.topic_report}", json.dumps(msg_form), self.QoS)

            print(f"{Fore.BLUE}{Style.BRIGHT}[PUB]{Style.NORMAL} - Report Sent: {Fore.RESET}{msg_form}")
                
        def gen_report(self):

            # Generate Reports with Certain Amount of Data - Prev Version Caused 'list index out of range'
            if self.ox_sat_level.size>int(self.analysis_window/5):

                rep_msg = [
                           {"n":'max_spo2', "v":np.max(self.ox_sat_level[-int(self.analysis_window/5):])}, 
                           {"n":'min_spo2', "v":np.min(self.ox_sat_level[-int(self.analysis_window/5):])},
                           {"n":'mean_spo2', "v":np.mean(self.ox_sat_level[-int(self.analysis_window/5) :])}
                           ]
                
                self.publish_report(rep_msg)

                # Delete Cached Pressure Data for Next Report
                self.ox_sat_level = np.array([])

        def temp_window(self):
            return self.analysis_window

        # Function to Update Analysis Window
        def update_window(self, new_window_val):
            self.analysis_window = new_window_val 

        # REST API

        def GET(self,*uri, **params):

            return "Hello World"


if __name__ == "__main__":

        # Standard configuration to serve the url "localhost:8080"
    conf = {
        '/': {
            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
        }
    }
    
    os_analysis = Oxygen_Analysis(client_id="OS-ANALYSIS",
                                    topic_cat="oxygen",
                                    topic_measurement='measurements',
                                    topic_report="reports",
                                    topic_warning="warnings",
                                    ox_sat_threshold=90,
                                    analysis_window=20,
                                    qos=2,
                                    msg_broker="localhost",
                                    msg_broker_port=1883)

    cherrypy.tree.mount(os_analysis, '/', conf)
    os_analysis.start()
    cherrypy.engine.start()

    while True:
        os_analysis.gen_report()
        time.sleep(os_analysis.temp_window())

    bp_analysis.stop()
    cherrypy.engine.block()
