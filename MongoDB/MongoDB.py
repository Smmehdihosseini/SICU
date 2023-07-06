import os
import time
import json
import threading
import requests
import cherrypy
from colorama import Fore, Style
import paho.mqtt.client as PahoMQTT
from pymongo import MongoClient, DESCENDING
from utils.ErrorHandler import DatabaseError, BrokerError, ConfError, SettError, CatError

class MongoDB:	
        
        exposed = True

        def __init__(self):
    
            # MongoDB Service Settings
            self.base_path = 'MongoDB'
    
            # Loading Setting
            self.settings = self.init_sett()

            # Loading Configurations, Service Catalog and Service Info
            self.conf = self.init_conf()
            self.serv_cat = self.conf['service_catalog']
            self.serv_info = self.conf['service_info']

            # MQTT Endpoint URL, Port, Topics and QoS
            self.mqtt_broker = self.serv_info['connections']['MQTT']['url'] 
            self.mqtt_broker_port = self.serv_info['connections']['MQTT']['port'] 
            self.topic_list = self.serv_info['connections']['MQTT']['topics']
            self.QoS = self.serv_info['connections']['MQTT']['qos']

            # Instance of MQTT Client
            self.paho_mqtt = PahoMQTT.Client(self.serv_info['id'], True) 
            
            # Register the MQTT Client Callback
            self.paho_mqtt.on_connect = self.on_connect
            self.paho_mqtt.on_message = self.on_message

            # Database URL, Port and DB Name - db
            self.mongo_url = self.serv_info['endpoints']['DB']['url']
            self.mongo_port = self.serv_info['endpoints']['DB']['port']
            self.db_name = self.serv_info['endpoints']['DB']['database_name']
            self.db_collections = self.serv_info['endpoints']['DB']['database_collections']

            # REST API
            self.url = self.serv_info['endpoints']['REST']['url']
            self.port = self.serv_info['endpoints']['REST']['port']

            # Show Messages Body in Terminal Output
            self.show_msg = False

        # Intializing Settings
        def init_sett(self):

            self.path_settings = "/settings.json"
            if os.path.exists(self.base_path+self.path_settings):
                try:
                    with open(self.base_path+self.path_settings, 'r') as file:
                        self.settings = json.load(file)

                    # MongoDB Service Settings
                    self.path_conf = self.settings['service_settings']['path_conf']

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

        # Start MongoDB Service
        def start(self):
            try: 
                # Connect  MQTT Broker Connection
                self.paho_mqtt.connect(self.mqtt_broker, self.mqtt_broker_port)
                self.paho_mqtt.loop_start()

                ## Subscribe to All Topics in System
                for topic in self.topic_list:
                    self.paho_mqtt.subscribe(f"{topic}", self.QoS)
            except:
                raise BrokerError("Error Occured with Connecting MQTT Broker")
            
            try:
                # Manage DB Connection - 'localhost', 27017
                mongo_client = MongoClient(self.mongo_url, self.mongo_port)
                self.db = mongo_client[self.db_name]
                for collection in self.db_collections:
                    if collection not in self.db.list_collection_names():
                        create_collection = self.db[collection]
                print(f"{Fore.LIGHTYELLOW_EX}+ [DB=OK] Connected to '{self.db_name}'{Fore.RESET}")                            
            except Exception as e:
                raise DatabaseError("Error Occured with Starting MongoDB Database")
            
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
            
            print(f"{Fore.LIGHTYELLOW_EX}\n+ [MQTT=OK][DB=OK][SRV=OK] {self.serv_info['name']} Service: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")
            
        def stop(self):

            # Unsubscribe From All Topic Lists
            for topic in self.topic_list:
                self.paho_mqtt.unsubscribe(f"{topic}")

            self.paho_mqtt.loop_stop()
            self.paho_mqtt.disconnect()

            print(f"----------------------------------------------------------------------------------\n+ {self.serv_info['name']} Service: [MQTT=OFFLINE]")

        def on_connect(self, paho_mqtt, userdata, flags, rc):
            print(f"\n{Fore.LIGHTYELLOW_EX}+ [MQTT=OK] Connected to '{self.mqtt_broker}' [code={rc}]{Fore.RESET}")

        def on_message(self, paho_mqtt , userdata, msg):

            # On Getting New Message
            # 'P300/oxygen/measurements
            _id, _sens_cat, _sens_type = msg.topic.split('/')
            msg_body = json.loads(msg.payload.decode('utf-8'))

            print (f"{Fore.GREEN}{Style.BRIGHT}[SUB]{Style.NORMAL} {str(_sens_type).capitalize()} Recieved [{msg_body['bt']}]: Topic: '{msg.topic}' - QoS: '{str(msg.qos)}'{Fore.RESET}")

            doc = {"timestamp":msg_body['bt'],
                    "device_id": _id,
                    "sens_cat": _sens_cat,
                    "sens_type": _sens_type,
                    "unit": msg_body['u']}
            
            for field in msg_body['e']:
                doc[field['n']] = field['v']
            
            # Insert Measurements in Database
            result = self.db[_sens_type].insert_one(doc)

            if result.acknowledged:
                print(f"{Fore.CYAN}[INS] Successfully Inserted Document in Database{Fore.RESET}")
            else:
                print(f"{Fore.RED}[INS] Failed to Insert Document in Database{Fore.RESET}")

        def webservice_url(self):
            return self.url
        
        def webservice_port(self):
            return self.port
        
        def webservice_conf(self):
            return {
                        '/': {
                            'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                            'tools.sessions.on': True
                        }
                    }
        
        def GET(self, *uri, **params):
            if len(uri)>0:

                if str(uri[0])=="live_data":
                    live_data = {}
                    for topic in self.topic_list:
                        live_topic = topic.split('/')[1]
                        live_data[live_topic] = {}
                        live_data[live_topic][self.db_collections[0]] = list(self.db[self.db_collections[0]].find({"sens_cat": live_topic,
                                                                                                "device_id": params["dev_id"]},
                                                                                                {"_id": 0},
                                                                                                sort=[("_id", DESCENDING)],
                                                                                                limit=1))

                        if live_topic=="ecg":
                            live_data[live_topic][self.db_collections[2]] = list(self.db[self.db_collections[2]].find({"sens_cat": live_topic,
                                                                                             "device_id": params["dev_id"]},
                                                                                                {"_id": 0},
                                                                                                sort=[("_id", DESCENDING)],
                                                                                                limit=1)) 
                    return json.dumps(live_data)                      

                elif str(uri[0])=="get_report":
                    report_data = {}
                    report_data[params['report_type']] = {}
                    report_data[params['report_type']][self.db_collections[2]] = list(self.db[self.db_collections[2]].find({"sens_cat": params['report_type'],
                                                                                "device_id": params["dev_id"]},
                                                                                {"_id": 0},
                                                                                sort=[("_id", DESCENDING)]))
                    return json.dumps(report_data)
                
                elif str(uri[0])=="get_warning":
                    warning_data = {}
                    warning_data[params['warning_type']] = {}
                    warning_data[params['warning_type']][self.db_collections[1]] = list(self.db[self.db_collections[1]].find({"sens_cat": params['warning_type'],
                                                                                "device_id": params["dev_id"]},
                                                                                {"_id": 0},
                                                                                sort=[("_id", DESCENDING)]))
                    return json.dumps(warning_data)

if __name__ == "__main__":

    mongo_db = MongoDB()
    mongo_db.start()
    cherrypy.tree.mount(mongo_db, '/', mongo_db.webservice_conf())
    cherrypy.config.update({'server.socket_host': mongo_db.webservice_url()})
    cherrypy.config.update({'server.socket_port': mongo_db.webservice_port()})
    cherrypy.engine.start()
    mongo_db_thread = threading.Thread(target=mongo_db.update_service_status)
    mongo_db_thread.daemon = True
    mongo_db_thread.start()
    cherrypy.engine.block()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        mongo_db.stop()
        cherrypy.engine.stop()
        mongo_db_thread.terminate()