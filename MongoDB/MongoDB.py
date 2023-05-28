import paho.mqtt.client as PahoMQTT
import time
import numpy as np
import json
import cherrypy
from colorama import Fore, Style
from pymongo import MongoClient
from utils.ErrorHandler import DatabaseError, BrokerError

class MongoDB:	
        
        exposed = True

        def __init__(self,
                     clientID,
                     mongo_url='localhost',
                     mongo_port=27017,
                     msg_broker='localhost',
                     msg_broker_port=1883):

            self.clientID = clientID
            
            # Instance of PahoMQTT Client
            self.paho_mqtt = PahoMQTT.Client(clientID, True) 
            
            # Register the Callback
            self.paho_mqtt.on_connect = self.on_connect
            self.paho_mqtt.on_message = self.on_message

            # MQTT Broker URL
            self.msg_broker = msg_broker 
            self.msg_broker_port = msg_broker_port

            # List of Available Topics
            self.topic_list = ["oxygen", 'pressure', 'ecg']

            # QoS
            self.QoS = 2
            
            # MongoDB URL
            self.mongo_url = mongo_url
            self.mongo_port = mongo_port
            
            # MongoDB DB Init
            self.db = None
            self.db_name = 'sicu'
            
        def start(self):
            
            try: 
                # Connect  MQTT Broker Connection
                self.paho_mqtt.connect(self.msg_broker, self.msg_broker_port)
                self.paho_mqtt.loop_start()

                ## Subscribe to All Topics in System
                for topic in self.topic_list:
                    self.paho_mqtt.subscribe(f"+/{topic}/#", self.QoS)

            except:
                raise BrokerError("Error Occured with Connecting MQTT Broker")
            
            try:

                # Manage DB Connection - 'localhost', 27017
                mongo_client = MongoClient(self.mongo_url, self.mongo_port)
                
                self.db = mongo_client[self.db_name]

                for collection in ['measurements', 'reports', 'warnings']:
                    if collection not in self.db.list_collection_names():
                        create_collection = self.db['collection']
                                 
            except Exception as e:
                raise DatabaseError("Error Occured with Starting MongoDB Database")
            
            print(f"{Fore.YELLOW}\n+ MongoDB Database: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")
            
        def stop(self):

            for topic in self.topic_list:
                self.paho_mqtt.unsubscribe(f"+/{topic}/#")

            self.paho_mqtt.loop_stop()
            self.paho_mqtt.disconnect()

            print("----------------------------------------------------------------------------------\n+ MongoDB Database: [OFFLINE]")

        def on_connect(self, paho_mqtt, userdata, flags, rc):

            print(f"\n{Fore.YELLOW}+ Connected to '{self.msg_broker}' [code={rc}]{Fore.RESET}")

        def on_message(self, paho_mqtt , userdata, msg):

            # On Getting New Message

            _id, _sens_cat, _sens_type = msg.topic.split('/')
            msg_body = json.loads(msg.payload.decode('utf-8'))

            print (f"{Fore.GREEN}{Style.BRIGHT}[SUB]{Style.NORMAL} {str(_sens_type).capitalize()} Recieved [{msg_body['bt']}]: Topic: '{msg.topic}' - QoS: '{str(msg.qos)}' - Message: {Fore.RESET}'{str(msg_body)}")

            # Pressure
            if _sens_cat=="pressure":
                
                # Pressure Measurement Microservice
                if _sens_type=="measurements":

                    doc = {"timestamp":msg_body['bt'],
                            "user_id": _id,
                            "sens_cat": _sens_cat,
                            "sens_type": _sens_type,
                            "unit": msg_body['u'],
                            "diastolic":  next((e for e in msg_body['e'] if e.get("n")=="diastolic"), None)['v'],
                            "systolic": next((e for e in msg_body['e'] if e.get("n")=="systolic"), None)['v']}

                elif _sens_type=="reports":

                    doc = {"timestamp":msg_body['bt'],
                        "user_id": msg_body['id'],
                        "sens_cat": _sens_cat,
                        "sens_type": _sens_type,
                        "unit": msg_body['u'],
                        "max_diastolic": next((e for e in msg_body['e'] if e.get("n")=="max_diastolic"), None)['v'],
                        "min_diastolic": next((e for e in msg_body['e'] if e.get("n")=="min_diastolic"), None)['v'],
                        "mean_diastolic": next((e for e in msg_body['e'] if e.get("n")=="mean_diastolic"), None)['v'],
                        "max_systolic": next((e for e in msg_body['e'] if e.get("n")=="max_systolic"), None)['v'],
                        "min_systolic": next((e for e in msg_body['e'] if e.get("n")=="min_systolic"), None)['v'],
                        "mean_systolic": next((e for e in msg_body['e'] if e.get("n")=="mean_systolic"), None)['v']}
                
                elif _sens_type=="warnings":

                    doc = {"timestamp":msg_body['bt'],
                        "user_id": msg_body['id'],
                        "sens_cat": _sens_cat,
                        "sens_type": _sens_type,
                        "unit": msg_body['u'],
                        "warning": msg_body['e'][0]['n'],
                        "value": msg_body['e'][0]['v']}
                        
            elif _sens_cat=="oxygen":
                
                # Oxygen Saturation Measurement Microservice
                if _sens_type=="measurements":

                    doc = {"timestamp":msg_body['bt'],
                            "user_id": _id,
                            "sens_cat": _sens_cat,
                            "sens_type": _sens_type,
                            "unit": msg_body['u'],
                            "spo2":  next((e for e in msg_body['e'] if e.get("n")=="SpO2"), None)['v']
                            }
                    
            elif _sens_cat=="ecg":
                
                # ECG Measurement Microservice
                if _sens_type=="measurements":

                    doc = {"timestamp":msg_body['bt'],
                            "user_id": _id,
                            "sens_cat": _sens_cat,
                            "sens_type": _sens_type,
                            "unit": msg_body['u'],
                            "ecg_seg":  msg_body['e']
                            }

            # Insert Measurements in Database
            result = self.db[_sens_type].insert_one(doc)

            if result.acknowledged:
                print(f"{Fore.CYAN}[INS] Successfully Inserted Document in Database{Fore.RESET}")
            else:
                print(f"{Fore.RED}[INS] Failed to Insert Document in Database{Fore.RESET}")


if __name__ == "__main__":

    mongo_db = MongoDB(clientID="Admin",
                      mongo_url="localhost",
                      mongo_port=27017,
                      msg_broker='localhost',
                      msg_broker_port=1883)

    mongo_db.start()

    while True:
        pass

    sphy_dev.stop()