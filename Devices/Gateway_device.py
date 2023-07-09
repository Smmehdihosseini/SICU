import os
import time
import random
import json
import requests
import threading
import neurokit2 as nk
import paho.mqtt.client as PahoMQTT
from colorama import Fore, Style
from utils.ErrorHandler import BrokerError, SettError, ConfError, CatError

class GatewayDevice:

    def __init__(self):
        
        # Oxygen Analysis Device Settings
        self.base_path = 'Devices'

        # Loading Setting
        self.settings = self.init_sett()

        # Loading Configurations, Device Catalog and Device Info
        self.conf = self.init_conf()
        self.dev_cat = self.conf['device_catalog']
        self.dev_info = self.conf['device_info']

        # MQTT Endpoint URL, Port, Topics and QoS
        self.mqtt_broker = self.dev_info['connections']['MQTT']['url'] 
        self.mqtt_broker_port = self.dev_info['connections']['MQTT']['port'] 
        self.topic_cat = self.dev_info['connections']['MQTT']['topics']['publisher']['topic_cat']
        self.topic_oxygen = self.dev_info['connections']['MQTT']['topics']['publisher']['topic_oxygen']
        self.topic_pressure = self.dev_info['connections']['MQTT']['topics']['publisher']['topic_pressure']
        self.topic_ecg = self.dev_info['connections']['MQTT']['topics']['publisher']['topic_ecg']
        self.QoS = self.dev_info['connections']['MQTT']['qos']

        # Device Information
        self.dev_id = self.dev_info['dev_id']

        # Instance of MQTT Client
        self.paho_mqtt = PahoMQTT.Client(self.dev_info['dev_id'], True) 
        
        # Register the MQTT Client Callback
        self.paho_mqtt.on_connect = self.on_connect

        # Show Messages Body in Terminal Output
        self.show_msg = False

    # Intializing Settings
    def init_sett(self):

        self.path_settings = "/gateway_settings.json"
        if os.path.exists(self.base_path+self.path_settings):
            try:
                with open(self.base_path+self.path_settings, 'r') as file:
                    self.settings = json.load(file)

                # Gateway Device Settings
                self.path_conf = self.settings['device_settings']['path_conf']

                # Pulse Oximeter Conditions Values
                self.oxygen_sat_threshold = self.settings['device_settings']['oximeter']['oxygen_saturation_threshold']
                self.oxygen_prob = self.settings['device_settings']['oximeter']['prob']
                self.oxygen_sample_freq = self.settings['device_settings']['oximeter']['sample_frequency']

                # Sphygmomanometer Conditions Values
                self.systolic_threshold = self.settings['device_settings']['sphygmomanometer']['systolic_threshold']
                self.diastolic_threshold = self.settings['device_settings']['sphygmomanometer']['diastolic_threshold']
                self.pressure_prob = self.settings['device_settings']['sphygmomanometer']['prob']
                self.pressure_sample_freq = self.settings['device_settings']['sphygmomanometer']['sample_frequency']

                # Electrocardiogram Conditions Values
                self.ecg_duration = self.settings['device_settings']['electrocardiogram']['ecg_duration']
                self.ecg_sampling_rate = self.settings['device_settings']['electrocardiogram']['sampling_rate']
                self.tachycardia_threshold = self.settings['device_settings']['electrocardiogram']['tachycardia_threshold']
                self.bradycardia_threshold = self.settings['device_settings']['electrocardiogram']['bradycardia_threshold']
                self.ecg_prob = self.settings['device_settings']['electrocardiogram']['prob']
                self.ecg_sample_freq = self.settings['device_settings']['electrocardiogram']['sample_frequency']

                # Configuration Load Timeout and Max Retry
                self.conf_timeout = self.settings['timesout_settings']['conf_timeout']
                self.conf_maxretry = self.settings['timesout_settings']['conf_maxretry']

                # Device Registery Timeout
                self.dev_timeout = self.settings['timesout_settings']['dev_timeout']
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
    
    def update_device_status(self):

        while True:
            try:
                json_resp = requests.post(f"{self.dev_cat['address']}/reg_device",
                                            json=json.dumps(self.dev_info)).json()
                if json_resp['status']=="Registered":
                    print(f"{Fore.LIGHTYELLOW_EX}+ [DEV=OK] Re-registered to 'Device Catalog'{Fore.RESET}")
                elif json_resp['status']=='Updated':
                    print(f"{Fore.LIGHTYELLOW_EX}+ [DEV=OK] Updated in 'Device Catalog'{Fore.RESET}")

            except:
                print(f"{Fore.RED}[DEV] Failed to Update to Device Catalog! {Fore.RESET}")

            time.sleep(self.update_thresh)

    def start(self):
        
        try: 
            # Connect MQTT Broker Connection
            self.paho_mqtt.connect(self.mqtt_broker, self.mqtt_broker_port)
            self.paho_mqtt.loop_start()

        except:
            raise BrokerError("Error Occured with Connecting MQTT Broker")
        
        device_registered = False
        while not device_registered:        
            try:
                json_resp = requests.post(f"{self.dev_cat['address']}/reg_device",
                                            json=json.dumps(self.dev_info)).json()
                if json_resp['status']=="Registered":
                    device_registered = True
                    print(f"{Fore.LIGHTYELLOW_EX}+ [DEV=OK] Registered to 'Device Catalog'{Fore.RESET}")
                elif json_resp['status']=='Updated':
                    device_registered = True
                    print(f"{Fore.LIGHTYELLOW_EX}+ [DEV=OK] Updated in 'Device Catalog'{Fore.RESET}")
                elif json_resp['status']=="Failed":
                    raise CatError(f"Error Occured with Registering in Catalog: {json_resp['log']}")
            except:
                print(f"{Fore.RED}[DEV] Failed to Connect to Device Catalog, Retrying in {self.dev_timeout} Seconds ... {Fore.RESET}")
                time.sleep(self.dev_timeout)                                     
                
        print(f"{Fore.LIGHTYELLOW_EX}\n+ [MQTT=OK][DEV=OK] {self.dev_info['dev_id']} Device: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

    def stop(self):
        
        self.paho_mqtt.loop_stop()
        self.paho_mqtt.disconnect()

        print(f"----------------------------------------------------------------------------------\n+ {self.dev_info['name']} Device: [MQTT=OFFLINE]")

    def on_connect(self, paho_mqtt, userdata, flags, rc):
        print(f"\n{Fore.LIGHTYELLOW_EX}+ [MQTT=OK] Connected to '{self.mqtt_broker}' [code={rc}]{Fore.RESET}")

    def publish_measurements(self, msg, category):

        # Message Publish SenML Format

        timestamp = int(time.time())

        msg_form = {
                    "bn":f"{self.mqtt_broker}:{self.mqtt_broker_port}/{self.dev_id}/{category}/{self.topic_cat}",
                    "bt":timestamp,
                    "u":"%",
                    "e": msg
                    }
        
        self.paho_mqtt.publish(f"{self.dev_id}/{category}/{self.topic_cat}", json.dumps(msg_form), 2)
        print(f"{Fore.GREEN}{Style.BRIGHT}[PUB]{Style.NORMAL} - {category.capitalize()} {self.topic_cat.capitalize()} Sent:{Fore.RESET}{str(msg_form if self.show_msg else 'Hidden')}")

    def get_oxygen_measurements(self):

        while True:

            if random.random() < self.oxygen_prob:
                oxygen_sat = random.randint(self.oxygen_sat_threshold, 100)
            else:
                oxygen_sat = random.randint(70, self.oxygen_sat_threshold-1)

            measurement = [
                            {"n":"spo2", "v":oxygen_sat}
                        ] 
            
            self.publish_measurements(measurement, self.topic_oxygen)
            time.sleep(self.oxygen_sample_freq)

    def get_pressure_measurements(self):

        while True:

            if random.random() < self.pressure_prob:
                systolic = random.randint(self.systolic_threshold, 140)
            else:
                if random.random()>=0.5:
                    systolic = random.randint(80, self.systolic_threshold-1)

                else:
                    systolic = random.randint(141, 150)
            
            if random.random() < self.pressure_prob:
                diastolic = random.randint(self.diastolic_threshold, 90)
            else:
                if random.random()>=0.5:
                    diastolic = random.randint(50, self.diastolic_threshold-1)
                else:
                    diastolic = random.randint(91, 100)

            measurement = [
                            {"n":"systolic", "v":systolic},
                            {"n":"diastolic", "v":diastolic}
                        ]   
            
            self.publish_measurements(measurement, self.topic_pressure)
            time.sleep(self.pressure_sample_freq)

    def get_ecg_measurements(self):

        while True:

            counter = 0
            if random.random() < self.ecg_prob:
                heart_rate = random.randint(self.bradycardia_threshold , self.tachycardia_threshold)
            else:
                if random.random()>=0.5:
                    heart_rate = random.randint(self.bradycardia_threshold-20, self.bradycardia_threshold-1)
                else:
                    heart_rate = random.randint(self.tachycardia_threshold-1, self.tachycardia_threshold+20)
            
            ecg_signal = nk.ecg_simulate(duration=self.ecg_duration, sampling_rate=self.ecg_sampling_rate, heart_rate=heart_rate) 
            while counter<60:

                measurement = [
                            {"n":"ecg_seg", "v":ecg_signal[counter*self.ecg_sampling_rate:(counter+1)*self.ecg_sampling_rate].tolist()}
                        ]  

                self.publish_measurements(measurement, self.topic_ecg)
                time.sleep(self.ecg_sample_freq)
                counter += 1
        
    
if __name__ == "__main__":

    gateway_device = GatewayDevice()
    gateway_device.start()

    # Gateway Device Sphygmomanometer Measurements Thread
    sphygmomanometer_thread = threading.Thread(target=gateway_device.get_pressure_measurements)
    sphygmomanometer_thread.daemon = True
    sphygmomanometer_thread.start()

    # Gateway Device Pulse Oximeter Measurements Thread
    oximeter_thread = threading.Thread(target=gateway_device.get_oxygen_measurements)
    oximeter_thread.daemon = True
    oximeter_thread.start()

    # Gateway Device Electrocardiogram Measurements Thread
    electrocardiogram_thread = threading.Thread(target=gateway_device.get_ecg_measurements)
    electrocardiogram_thread.daemon = True
    electrocardiogram_thread.start()

    # Gateway Device Registery Update in Device Catalog Thread
    gateway_update_status_thread = threading.Thread(target=gateway_device.update_device_status)
    gateway_update_status_thread.daemon = True
    gateway_update_status_thread.start()


    try:
        while True:
            pass
    except KeyboardInterrupt:
       sphygmomanometer_thread.terminate()
       oximeter_thread.terminate()
       electrocardiogram_thread.terminate()
       gateway_update_status_thread.terminate()
       gateway_device.stop()