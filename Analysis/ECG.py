import paho.mqtt.client as PahoMQTT
import time
import numpy as np
import json
import cherrypy
import neurokit2 as nk
from colorama import Fore, Style
from utils.ErrorHandler import BrokerError

class ECG_Analysis:
        
        exposed = True

        def __init__(self,
                 client_id,
                 topic_cat="ecg",
                 topic_measurement='measurements',
                 topic_report="reports",
                 topic_warning="warnings",
                 hr_mean_threshold={'upper_bound':100,'lower_bound':80},
                 r_r_std_threshold=0.025,
                 analysis_window=60,
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
            
            # ECG Data
            self.ecg_data = np.array([])
            self.sampling_rate=1000
            self.frequency = 0
            self.RR_max = 0
            self.RR_min = 0
            self.RR_mean = 0
            self.envelope = []

            # ECG Critical Values
            self.hr_mean_threshold = hr_mean_threshold
            self.r_r_std_threshold = r_r_std_threshold
            self.analysis_window = analysis_window

        def start(self):
            
            try: 
                # Connect MQTT Broker Connection
                self.paho_mqtt.connect(self.msg_broker, self.msg_broker_port)
                self.paho_mqtt.loop_start()
                self.paho_mqtt.subscribe(f"+/{self.topic_cat}/{self.topic_measurement}")

            except:
                raise BrokerError("Error Occured with Connecting MQTT Broker")
            
            # Add Name of The Analysis to this Print
            print(f"{Fore.YELLOW}\n+ Heartrate Analysis : [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

        def stop(self):
            
            self.paho_mqtt.unsubscribe(f"+/{self.topic_cat}/{self.topic_measurement}")
            self.paho_mqtt.loop_stop()
            self.paho_mqtt.disconnect()

            print("----------------------------------------------------------------------------------\n+ Heartrate Analysis : [OFFLINE]")

        def on_connect(self, paho_mqtt, userdata, flags, rc):

            print(f"\n{Fore.YELLOW}+ Connected to '{self.msg_broker}' [code={rc}]{Fore.RESET}")

        def on_message(self, paho_mqtt , userdata, msg):

            self.user_id, _sens_cat, _sens_type = msg.topic.split('/')
            msg_body = json.loads(msg.payload.decode('utf-8'))

            print (f"{Fore.GREEN}{Style.BRIGHT}[SUB]{Style.NORMAL} {str(_sens_type).capitalize()} Recieved [{msg_body['bt']}]: Topic: '{msg.topic}' - QoS: '{str(msg.qos)}' - Message: {Fore.RESET}'{str(msg_body)}")

            # Current ECG Value
            ecg_segment = next((e for e in msg_body['e'] if e.get("n")=="ECG Segment"), None)['v']

            # Array of ECG in Defined Window Size
            self.ecg_data = np.append(self.ecg_data,
                                     ecg_segment)
            
            if len(self.ecg_data)!=0:

                # Process ECG Data
                processed_ecg = nk.ecg_process(self.ecg_data, sampling_rate=self.sampling_rate)

                # Heart Rate Analysis
                self.heartrate_mean = round(np.mean(processed_ecg[0]['ECG_Rate']), 2)
                self.heartrate_max = round(np.max(processed_ecg[0]['ECG_Rate']), 2)
                self.heartrate_min = round(np.min(processed_ecg[0]['ECG_Rate']), 2)

                # R-R Peak Analysis
                R_peak = processed_ecg[0]['ECG_R_Peaks']

                RR_indices = np.where(R_peak != 0)[0]

                R_R = np.diff(RR_indices)
                    
                self.R_R_mean = round(np.mean(R_R)/1000,2)
                self.R_R_min = round(np.min(R_R)/1000, 2)
                self.R_R_max = round(np.max(R_R)/1000, 2)
                self.R_R_std = round(np.std(R_R)/1000,3)

                if self.heartrate_mean > self.hr_mean_threshold['upper_bound']:

                    warn_msg = [
                                {"n":"Tachycardia",
                                 "v":{
                                     "mean_freq":self.heartrate_mean,
                                     "min_freq":self.heartrate_min,
                                     "max_freq":self.heartrate_max,
                                     "mean_rr":self.R_R_mean,
                                     "min_rr":self.R_R_min,
                                     "max_rr":self.R_R_max,
                                     "std_rr":self.R_R_std,
                                     "envelope":processed_ecg[0]["ECG_Clean"],
                                }}
                            ]
                    
                    self.publish_warnings(warn_msg)                

                elif self.heartrate_mean > self.hr_mean_threshold['lower_bound']:

                    warn_msg = [
                                {"n":"Bradycardia",
                                 "v":{
                                     "mean_freq":self.heartrate_mean,
                                     "min_freq":self.heartrate_min,
                                     "max_freq":self.heartrate_max,
                                     "mean_rr":self.R_R_mean,
                                     "min_rr":self.R_R_min,
                                     "max_rr":self.R_R_max,
                                     "std_rr":self.R_R_std,
                                     "envelope":processed_ecg[0]["ECG_Clean"],
                                }}
                            ]
                    
                    self.publish_warnings(warn_msg)

                if self.R_R_std > self.r_r_std_threshold:

                    warn_msg = [
                                {"n":"Arrhythmia",
                                 "v":{
                                     "mean_freq":self.heartrate_mean,
                                     "min_freq":self.heartrate_min,
                                     "max_freq":self.heartrate_max,
                                     "mean_rr":self.R_R_mean,
                                     "min_rr":self.R_R_min,
                                     "max_rr":self.R_R_max,
                                     "std_rr":self.R_R_std,
                                     "envelope":processed_ecg[0]["ECG_Clean"],
                                }}
                            ]
                    
                    self.publish_warnings(warn_msg)

        def publish_warnings(self, msg):
                        
            timestamp = int(time.time())

            # Message Publish SenML Format
            msg_form = {
                        "bn":f"{self.msg_broker}:{self.msg_broker_port}/{self.user_id}/{self.topic_cat}/{self.topic_warning}",
                        "id":self.user_id,
                        "bt":timestamp,
                        "u":"Hz",
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
                        "u":"Hz",
                        "e": msg
                        }
            
            self.paho_mqtt.publish(f"{self.user_id}/{self.topic_cat}/{self.topic_report}", json.dumps(msg_form), self.QoS)

            print(f"{Fore.BLUE}{Style.BRIGHT}[PUB]{Style.NORMAL} - Report Sent: {Fore.RESET}{msg_form}")
                
        def gen_report(self):

            # Generate Reports with Certain Amount of Data - Prev Version Caused 'list index out of range'
            if len(self.ecg_data)!=0:

                rep_msg = [
                           {"n":'mean_freq', "v":self.heartrate_mean}, 
                           {"n":'min_freq', "v":self.heartrate_min},
                           {"n":'max_freq', "v":self.heartrate_max},
                           {"n":'mean_rr', "v":self.R_R_mean},
                           {"n":'min_rr', "v":self.R_R_min},
                           {"n":'max_rr', "v":self.R_R_max},
                           {"n":'std_rr', "v":self.R_R_std}
                           ]
                
                self.publish_report(rep_msg)

                # Delete Cached ECG Data for Next Report
                self.ecg_data = np.array([])

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
    
    ecg_analysis = ECG_Analysis(client_id="ECG-ANALYSIS",
                                topic_cat="ecg",
                                topic_measurement='measurements',
                                topic_report="reports",
                                topic_warning="warnings",
                                hr_mean_threshold={'upper_bound':100,'lower_bound':80},
                                r_r_std_threshold=0.025,
                                analysis_window=60,
                                qos=2,
                                msg_broker="localhost",
                                msg_broker_port=1883)

    cherrypy.tree.mount(ecg_analysis, '/', conf)
    ecg_analysis.start()
    cherrypy.engine.start()

    while True:
        time.sleep(ecg_analysis.temp_window())
        ecg_analysis.gen_report()

    bp_analysis.stop()
    cherrypy.engine.block()
