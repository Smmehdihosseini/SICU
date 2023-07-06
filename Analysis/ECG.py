import os
import time
import json
import threading
import requests
import numpy as np
import paho.mqtt.client as PahoMQTT
import neurokit2 as nk
from colorama import Fore, Style
from utils.ErrorHandler import BrokerError, SettError, ConfError, CatError

class ECGAnalysis:
        
        def __init__(self):
            
            # ECG Analysis Service Settings
            self.base_path = 'Analysis'

            # Loading Setting
            self.settings = self.init_sett()

            # Loading Configurations, Service Catalog and Service Info
            self.conf = self.init_conf()
            self.serv_cat = self.conf['service_catalog']
            self.serv_info = self.conf['service_info']

            # MQTT Endpoint URL, Port, Topics and QoS
            self.mqtt_broker = self.serv_info['connections']['MQTT']['url'] 
            self.mqtt_broker_port = self.serv_info['connections']['MQTT']['port'] 
            self.topic_cat = self.serv_info['connections']['MQTT']['topics']['category']
            self.topic_measurement = self.serv_info['connections']['MQTT']['topics']['subscriber']
            self.topic_report = self.serv_info['connections']['MQTT']['topics']['publisher']['reports']
            self.topic_warning = self.serv_info['connections']['MQTT']['topics']['publisher']['warnings']
            self.QoS = self.serv_info['connections']['MQTT']['qos']

            # Instance of MQTT Client
            self.paho_mqtt = PahoMQTT.Client(self.serv_info['id'], True) 
            
            # Register the MQTT Client Callback
            self.paho_mqtt.on_connect = self.on_connect
            self.paho_mqtt.on_message = self.on_message

            # ECG Data
            self.ecg_data = {}

            # Show Messages Body in Terminal Output
            self.show_msg = False

        # Intializing Settings
        def init_sett(self):

            self.path_settings = "/ecg_settings.json"
            if os.path.exists(self.base_path+self.path_settings):
                try:
                    with open(self.base_path+self.path_settings, 'r') as file:
                        self.settings = json.load(file)

                    # ECG Analysis Service Settings
                    self.path_conf = self.settings['service_settings']['path_conf']

                    # ECG Conditions Values
                    self.analysis_window = self.settings['service_settings']['analysis_window']
                    self.hr_mean_threshold = self.settings['service_settings']['hr_mean_threshold']
                    self.r_r_std_threshold = self.settings['service_settings']['r_r_std_threshold']
                    self.sampling_rate = self.settings['service_settings']['sampling_rate']

                    # Configuration Load Timeout and Max Retry
                    self.conf_timeout = self.settings['timesout_settings']['conf_timeout']
                    self.conf_maxretry = self.settings['timesout_settings']['conf_maxretry']

                    # Service Registery Timeout
                    self.serv_timeout = self.settings['timesout_settings']['serv_timeout']
                    self.update_thresh = self.settings['timesout_settings']['update_threshold']

                except Exception as e:
                    raise SettError(f"Failed to Setup Settings: {e}")
                    
            else:
                raise SettError(f"Failed to Load Settings File ({self.base_path}/{self.path_settings}): No Such File")

            return self.settings

        # Intializing Configuration
        def init_conf(self):

            conf_retries = 0
            conf_loaded = False
            if os.path.exists(self.base_path+'/'+self.path_conf):
                with open(self.base_path+'/'+self.path_conf, 'r') as file:
                    self.conf = json.load(file)
            else:
                # Retry to Load Configuration File - If Reaches to Max Retry, Raise an Error
                while not conf_loaded:
                    if conf_retries==self.conf_maxretry:
                        raise ConfError(f"Failed to Load Configuration File ({self.base_path}/{self.path_conf}): Max Retries Reached ({self.conf_maxretry})")
                    print(f"{Fore.RED}[CNF] Failed to Load Configuration File, Retrying in {self.conf_timeout} Seconds ({conf_retries}/{self.conf_maxretry}) {Fore.RESET}")
                    time.sleep(self.conf_timeout)
                    try:
                        with open(self.base_path+'/'+self.path_conf, 'r') as file:
                            self.conf = json.load(file)
                        conf_loaded = True
                    except:
                        conf_retries += 1
            return self.conf
        
        def update_service_status(self):

            while True:
                
                try:
                    json_resp = requests.post(f"{self.serv_cat['address']}/reg_service",
                                                json=json.dumps(self.serv_info)).json()
                    if json_resp['status']=="Registered":
                        print(f"{Fore.LIGHTYELLOW_EX}+ [SRV=OK] Re-registered to 'Service Catalog'{Fore.RESET}")
                    elif json_resp['status']=='Updated':
                        print(f"{Fore.LIGHTYELLOW_EX}+ [SRV=OK] Updated in 'Service Catalog'{Fore.RESET}")

                except:
                    print(f"{Fore.RED}[SRV] Failed to Update to Service Catalog! {Fore.RESET}")

                time.sleep(self.update_thresh)

        def start(self):
            
            try: 
                # Connect MQTT Broker Connection
                self.paho_mqtt.connect(self.mqtt_broker, self.mqtt_broker_port)
                self.paho_mqtt.loop_start()
                self.paho_mqtt.subscribe(f"+/{self.topic_cat}/{self.topic_measurement}", self.QoS)

            except:
                raise BrokerError("Error Occured with Connecting MQTT Broker")
            
            service_registered = False
            while not service_registered:        
                try:
                    json_resp = requests.post(f"{self.serv_cat['address']}/reg_service",
                                                json=json.dumps(self.serv_info)).json()
                    if json_resp['status']=="Registered":
                        service_registered = True
                        print(f"{Fore.LIGHTYELLOW_EX}+ [SRV=OK] Registered to 'Service Catalog'{Fore.RESET}")
                    elif json_resp['status']=='Updated':
                        service_registered = True
                        print(f"{Fore.LIGHTYELLOW_EX}+ [SRV=OK] Updated in 'Service Catalog'{Fore.RESET}")
                    elif json_resp['status']=="Failed":
                        raise CatError(f"Error Occured with Registering in Catalog: {json_resp['log']}")
                except:
                    print(f"{Fore.RED}[SRV] Failed to Connect to Service Catalog, Retrying in {self.serv_timeout} Seconds ... {Fore.RESET}")
                    time.sleep(self.serv_timeout)                                     
                    
            print(f"{Fore.LIGHTYELLOW_EX}\n+ [MQTT=OK][SRV=OK] {self.serv_info['name']} Service: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

        def stop(self):
            
            self.paho_mqtt.unsubscribe(f"+/{self.topic_cat}/{self.topic_measurement}")

            self.paho_mqtt.loop_stop()
            self.paho_mqtt.disconnect()

            print(f"----------------------------------------------------------------------------------\n+ {self.serv_info['name']} Service: [MQTT=OFFLINE]")

        def on_connect(self, paho_mqtt, userdata, flags, rc):
            print(f"\n{Fore.LIGHTYELLOW_EX}+ [MQTT=OK] Connected to '{self.mqtt_broker}' [code={rc}]{Fore.RESET}")

        def on_message(self, paho_mqtt , userdata, msg):

            dev_id, _sens_cat, _sens_type = msg.topic.split('/')
            msg_body = json.loads(msg.payload.decode('utf-8'))

            print (f"{Fore.GREEN}{Style.BRIGHT}[SUB]{Style.NORMAL} {str(_sens_type).capitalize()} Recieved [{msg_body['bt']}]: Topic: '{msg.topic}' - QoS: '{str(msg.qos)}' - Message: {Fore.RESET}'{str(msg_body if self.show_msg else 'Hidden')}")

            # Current ECG Value
            ecg_segment = next((e for e in msg_body['e'] if e.get("n")=="ecg_seg"), None)['v']

            if dev_id not in self.ecg_data.keys():
                self.ecg_data[dev_id] = np.array([])

            # Array of ECG in Defined Window Size
            self.ecg_data[dev_id] = np.append(self.ecg_data[dev_id], ecg_segment)

        def publish_warnings(self, msg, dev_id):
                        
            timestamp = int(time.time())

            # Message Publish SenML Format
            msg_form = {
                        "bn":f"{self.mqtt_broker}:{self.mqtt_broker_port}/{dev_id}/{self.topic_cat}/{self.topic_warning}",
                        "id":dev_id,
                        "bt":timestamp,
                        "u":"BPM",
                        "e": msg
                        }
            
            self.paho_mqtt.publish(f"{dev_id}/{self.topic_cat}/{self.topic_warning}", json.dumps(msg_form), self.QoS)

            print(f"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}[PUB]{Style.NORMAL} - Warning Sent:{Fore.RESET}{str(msg_form if self.show_msg else 'Hidden')}")	

        def publish_report(self, msg, dev_id):

            timestamp = int(time.time())

            # Message Publish SenML Format
            msg_form = {
                        "bn":f"{self.mqtt_broker}:{self.mqtt_broker_port}/{dev_id}/{self.topic_cat}/{self.topic_report}",
                        "id":dev_id,
                        "bt":timestamp,
                        "u":"BPM",
                        "e": msg
                        }
            
            self.paho_mqtt.publish(f"{dev_id}/{self.topic_cat}/{self.topic_report}", json.dumps(msg_form), self.QoS)

            print(f"{Fore.BLUE}{Style.BRIGHT}[PUB]{Style.NORMAL} - Report Sent: {Fore.RESET}{str(msg_form if self.show_msg else 'Hidden')}")
                
        def gen_report(self):

            # Generate Reports with Certain Amount of Data - Prev Version Caused 'list index out of range'

            for _, dev_id in enumerate(self.ecg_data):

                if len(self.ecg_data[dev_id])!=0:

                    # Process ECG Data
                    processed_ecg = nk.ecg_process(np.array(self.ecg_data[dev_id]), sampling_rate=self.sampling_rate)

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
                                    {"n":"warning", "v":"Tachycardia"},
                                    {"n":"value",
                                    "v":{
                                        "mean_freq":self.heartrate_mean,
                                        "min_freq":self.heartrate_min,
                                        "max_freq":self.heartrate_max,
                                        "mean_rr":self.R_R_mean,
                                        "min_rr":self.R_R_min,
                                        "max_rr":self.R_R_max,
                                        "std_rr":self.R_R_std,
                                        "envelope":processed_ecg[0]["ECG_Clean"].tolist(),
                                    }}
                                ]
                        
                        self.publish_warnings(warn_msg, dev_id)                

                    elif self.heartrate_mean < self.hr_mean_threshold['lower_bound']:

                        warn_msg = [
                                    {"n":"warning", "v":"Bradycardia"},
                                    {"n":"value",
                                    "v":{
                                        "mean_freq":self.heartrate_mean,
                                        "min_freq":self.heartrate_min,
                                        "max_freq":self.heartrate_max,
                                        "mean_rr":self.R_R_mean,
                                        "min_rr":self.R_R_min,
                                        "max_rr":self.R_R_max,
                                        "std_rr":self.R_R_std,
                                        "envelope":processed_ecg[0]["ECG_Clean"].tolist(),
                                    }}
                                ]
                        
                        self.publish_warnings(warn_msg, dev_id)

                    if self.R_R_std > self.r_r_std_threshold:

                        warn_msg = [
                                    {"n":"warning", "v":"Arrhythmia"},
                                    {"n":"value",
                                    "v":{
                                        "mean_freq":self.heartrate_mean,
                                        "min_freq":self.heartrate_min,
                                        "max_freq":self.heartrate_max,
                                        "mean_rr":self.R_R_mean,
                                        "min_rr":self.R_R_min,
                                        "max_rr":self.R_R_max,
                                        "std_rr":self.R_R_std,
                                        "envelope":processed_ecg[0]["ECG_Clean"].tolist(),
                                    }}
                                ]
                        
                        self.publish_warnings(warn_msg, dev_id)

                    rep_msg = [
                            {"n":'mean_freq', "v":self.heartrate_mean}, 
                            {"n":'min_freq', "v":self.heartrate_min},
                            {"n":'max_freq', "v":self.heartrate_max},
                            {"n":'mean_rr', "v":self.R_R_mean},
                            {"n":'min_rr', "v":self.R_R_min},
                            {"n":'max_rr', "v":self.R_R_max},
                            {"n":'std_rr', "v":self.R_R_std}
                            ]
                    
                    self.publish_report(rep_msg, dev_id)

                    # Delete Cached ECG Data for Next Report
                    self.ecg_data[dev_id] = np.array([])

        def temp_window(self):
            return self.analysis_window

if __name__ == "__main__":
    
    ecg_analysis = ECGAnalysis()
    ecg_analysis.start()
    ecg_analysis_thread = threading.Thread(target=ecg_analysis.update_service_status)
    ecg_analysis_thread.daemon = True
    ecg_analysis_thread.start()

    try:
        while True:
            time.sleep(ecg_analysis.temp_window())
            ecg_analysis.gen_report()
    except KeyboardInterrupt:
        ecg_analysis.stop()
        ecg_analysis_thread.terminate()
