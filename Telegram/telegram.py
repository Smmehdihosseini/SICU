import os
import json
import time
import datetime
import threading
import requests
import telepot
from colorama import Fore, Style
import paho.mqtt.client as PahoMQTT
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from utils.ErrorHandler import BrokerError, MessageLoopError, CatError, SettError, ConfError

class TelegramBot:

    def __init__(self):

        # Telegram Bot Service Settings
        self.base_path = 'Telegram'

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

        # Init Local Variables
        self.users = {}
        self.devices = {}
        self.temp_users = {}
        self.temp_device = {}
        self.last_command = None

    # Intializing Settings
    def init_sett(self):

        self.path_settings = "/settings.json"
        if os.path.exists(self.base_path+self.path_settings):
            try:
                with open(self.base_path+self.path_settings, 'r') as file:
                    self.settings = json.load(file)

                # Telegram Service Settings
                self.path_conf = self.settings['service_settings']['path_conf']
                self.telegram_token = self.settings['service_settings']['telegram_token']

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
            # Connect  MQTT Broker Connection
            self.paho_mqtt.connect(self.mqtt_broker, self.mqtt_broker_port)
            self.paho_mqtt.loop_start()

            ## Subscribe to All Topics in System
            for topic in self.topic_list:
                self.paho_mqtt.subscribe(f"{topic}", self.QoS)

        except:
            raise BrokerError("Error Occured with Connecting MQTT Broker")
        
        try:
            self.bot = telepot.Bot(self.telegram_token)
            self.bot.message_loop(self.bot_chat_handler)
        except:
            raise MessageLoopError("Error Occured with Starting Telegram Message Loop")
        
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
                
        print(f"{Fore.LIGHTYELLOW_EX}\n+ [MQTT=OK][TG=OK][SRV=OK] {self.serv_info['name']} Service: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")
    
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

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📟 My Devices", callback_data="/get_devices"),
            InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device"),
            InlineKeyboardButton(text="❓ Help", callback_data="/help"),
            InlineKeyboardButton(text="🔴↩️Sign-out", callback_data="/signout")]
        ])
        
        if _id in self.devices.keys():

            chat_user = self.devices[_id]

            # Pressure
            if _sens_cat=="pressure":

                if _sens_type=="reports":
                                                
                    message = f"<b> 🆕🩸📊 [Blood Pressure Report] for {_id}:</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n"
                    message += f"🔺 <b>Maximum Diastolic:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='max_diastolic'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Minimum Diastolic:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='min_diastolic'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Mean Diastolic:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='mean_diastolic'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Maximum Systolic:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='max_systolic'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Minimum Systolic:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='min_systolic'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Mean Systolic: </b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='mean_systolic'), None)['v'])} {msg_body['u']}</i>\n"

                    self.bot.sendMessage(chat_user, message, parse_mode='HTML', reply_markup=keyboard)
                
                elif _sens_type=="warnings":

                    pressure_type_name = msg_body['e'][0]['v'].split()[0]
                    message = f"<b> ⚠️🩸⚠️ [Blood Pressure Warning], {msg_body['e'][0]['v']}! for {_id} :</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n" 
                    message += f"🔺 <b>{pressure_type_name}:</b> <i>{msg_body['e'][1]['v']} {msg_body['u']}</i>\n"

                    self.bot.sendMessage(chat_user, message, parse_mode='HTML', reply_markup=keyboard)
                        
            elif _sens_cat=="oxygen":
                
                # Oxygen Saturation Measurement Microservice
                if _sens_type=="reports":
                    
                    message = f"<b>🆕🫁📊 [Oxygen Saturation Report] for '{_id}':</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n"
                    message += f"🔺 <b>Maximum SpO2:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='max_spo2'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Minimum SpO2:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='min_spo2'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Mean SpO2:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='mean_spo2'), None)['v'])} {msg_body['u']}</i>\n"

                    self.bot.sendMessage(chat_user, message, parse_mode='HTML', reply_markup=keyboard)
                
                elif _sens_type=="warnings":
                    
                    message = f"<b>⚠️🫁⚠️ [Oxygen Stauration Warning], {msg_body['e'][0]['v']}! for '{_id}':</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n" 
                    message += f"🔺 <b>SpO2:</b> <i>{msg_body['e'][1]['v']} {msg_body['u']}</i>\n"

                    self.bot.sendMessage(chat_user, message, parse_mode='HTML', reply_markup=keyboard)
                    
            elif _sens_cat=="ecg":
                    
                if _sens_type=="reports":
                    
                    message = f"<b>🆕🫀📊 [ECG Report] for '{_id}':</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n"
                    message += f"🔺 <b>Maximum Heartrate:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='max_freq'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Minimum Heartrate:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='min_freq'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Mean Heartrate:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='mean_freq'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Maximum R-R:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='max_rr'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Minimum R-R:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='min_rr'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Mean R-R:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='mean_rr'), None)['v'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>STD R-R:</b> <i>{str(next((e for e in msg_body['e'] if e.get('n')=='mean_rr'), None)['v'])} {msg_body['u']}</i>\n"

                    self.bot.sendMessage(chat_user, message, parse_mode='HTML', reply_markup=keyboard)
                
                elif _sens_type=="warnings":
                    
                    message = f"<b>⚠️🫀⚠️ [ECG Warning], {msg_body['e'][0]['v']}! for '{_id}':</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n"
                    message += f"🔺 <b>Maximum Heartrate:</b> <i>{str(msg_body['e'][1]['v']['max_freq'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Minimum Heartrate:</b> <i>{str(msg_body['e'][1]['v']['min_freq'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Mean Heartrate:</b> <i>{str(msg_body['e'][1]['v']['mean_freq'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Maximum R-R:</b> <i>{str(msg_body['e'][1]['v']['max_rr'])}</i>\n"
                    message += f"🔺 <b>Minimum R-R:</b> <i>{str(msg_body['e'][1]['v']['min_rr'])}</i>\n"
                    message += f"🔺 <b>Mean R-R:</b> <i>{str(msg_body['e'][1]['v']['mean_rr'])}</i>\n"
                    message += f"🔺 <b>STD R-R:</b> <i>{str(msg_body['e'][1]['v']['std_rr'])}</i>\n"
                    message += f"\n\n ‼️ <b>Note :</b> Please Visit SICU Web Application to See Full ECG Envelope"

                    self.bot.sendMessage(chat_user, message, parse_mode='HTML', reply_markup=keyboard)

    def bot_chat_handler(self, msg):

        if 'data' in msg.keys(): 
            chat_id = msg['message']['chat']['id']
            chat_id = str(chat_id)
            command = msg['data']

        else:
            content_type, chat_type, chat_id = telepot.glance(msg)
            chat_id = str(chat_id)
            command = msg.get('text')

        if command=='/start':

            self.temp_users[chat_id] = {}
            self.users[chat_id] = {}

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin")],
                 [InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup")],
                 [InlineKeyboardButton(text="❓ Help", callback_data="/help")], 
                 [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
            ])

            self.bot.sendMessage(chat_id, '<b>Welcome to SICU Telegram Bot! How can I Help You?</b>', parse_mode='HTML', reply_markup=keyboard)

        if command=='/signin':
            self.last_command = '/signin'
            self.temp_users[chat_id] = {}
            self.users[chat_id] = {}
            message = "<b>🟢↪️Let's Sign-in to SICU!</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')
            message = "<b>🔸[Step 1] Please Enter Your Username:</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')
            
        elif self.last_command=='/signin' and "username" not in self.temp_users[chat_id].keys():
            self.temp_users[chat_id]["username"] = command
            message = '<b>🔸[Step 2] Please Enter Your Password:</b>'
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

        elif self.last_command=='/signin' and "password" not in self.temp_users[chat_id].keys():
            self.temp_users[chat_id]["password"] = command

            message = "<b>🔄 Please Wait ...</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

            try:
                json_req = {"username":self.temp_users[chat_id]["username"], "password":self.temp_users[chat_id]["password"]}
                json_resp = requests.get(f"{self.serv_cat['address']}/auth_user", params=json_req).json()                

                if json_resp['authenticated']==True: 
                    self.users[chat_id]["username"]=self.temp_users[chat_id]["username"]
                    self.users[chat_id]["password"]=self.temp_users[chat_id]["password"]
                    self.users[chat_id]["devices"]=json_resp["devices"]

                    # Add Corresponding Chat ID to Each Device for Later Message Parsing
                    for dev in json_resp["devices"]:
                        self.devices[dev] = chat_id

                    self.temp_users[chat_id] = {}
                    self.last_command = None
                    message = "<b>🟢↪️ You're Signed-In Succesfully!</b>"
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML')

                    if self.users[chat_id]["devices"]:
                        message = "<b>📟 List of Registered Devices:</b>\n\n"
                        message += '\n'.join(f"▪️ <b>{device}</b>" for device in self.users[chat_id]['devices'])
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device")],
                            [InlineKeyboardButton(text="❓ Help", callback_data="/help")],
                            [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")],
                            [InlineKeyboardButton(text="🔴↩️Sign-out", callback_data="/signout")]
                        ])
                        self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
                    
                    else:
                        message = "<b>⚠️ [WARNING] No Devices Found! Do You Want to Add a New Device?</b>"
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="➕ Yes, Add Device", callback_data="/add_device")],
                            [InlineKeyboardButton(text="❓ Help", callback_data="/help")],
                            [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")],
                            [InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                        ])
                        self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

                else:
                    self.temp_users[chat_id] = {}
                    self.last_command = None
                    message = "<b>❌ Username/Password Wrong or User Doesn't Exist!</b>\n\n"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔂 Try Again", callback_data="/signin")]
                    ])
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

            except:
                self.temp_users[chat_id] = {}
                message = "<b>❌ [ERR 500] Problem with Connecting to Server, Please Try Again!</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin")],
                        [InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup")]
                    ])
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

        if command=='/signout':
            self.temp_users[chat_id] = {}
            self.users[chat_id] = {}

            # Remove All Chat ID Devices for MQTT Messaging
            self.devices = {key: val for key, val in self.devices.items() if val!=chat_id}

            message = "<b>🔴↩️ You're Signed-Out!</b>"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin")],
                 [InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup")],
                 [InlineKeyboardButton(text="❓ Help", callback_data="/help")], 
                 [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
            ])
            self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

        if command == '/signup':
            self.last_command = '/signup'
            self.temp_users[chat_id] = {}
            self.users[chat_id] = {}
            message = "<b>🔹So Happy to Have You in SICU Community!</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')
            message = "<b>🔸[Step 1] First, Please Provide Us your organization name:</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

        elif self.last_command=='/signup' and "organization" not in self.temp_users[chat_id].keys():
            self.temp_users[chat_id]["organization"] = command
            message = '<b>🔸[Step 2] Now, Please Enter Your Account Password:</b>\n\n ❗️<i>Note: Try to Choose a Secure Password Which Contains Uppercase and Lowercase Letters, Special Characters (?!*&%$#@) and Numbers.</i>'
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

        elif self.last_command=='/signup' and "password" not in self.temp_users[chat_id].keys():
            self.temp_users[chat_id]["password"] = command
            message = "<b>🔄 Please Wait ...</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

            try:
                json_req = {"organization":self.temp_users[chat_id]["organization"],
                            "password":self.temp_users[chat_id]["password"]}
                json_resp = requests.post(f"{self.serv_cat['address']}/reg_user", json=json.dumps(json_req)).json()

                if json_resp['registered']:
                    self.users[chat_id]["username"] = json_resp['username']
                    self.users[chat_id]["password"] = self.temp_users[chat_id]["password"]
                    self.users[chat_id]["devices"] = []
                    self.last_command = None

                    message = "<b>✅ Your Information Has Been Successfully Registered. Here Are Your Credentials: \n\n</b>"
                    message += f"▪️ <b>Username:</b> <i>{json_resp['username']}</i>\n"
                    message += f"▪️ <b>Password:</b> <i>{self.temp_users[chat_id]['password']}</i>\n"
                    message += f"▪️ <b>Organization:</b> <i>{self.temp_users[chat_id]['organization']}</i>\n\n"
                    message += f"❗️<b>Note:</b> <i>DO NOT SHARE THIS CREDENTIALS WITH ANYONE</i>\n"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin")],
                            [InlineKeyboardButton(text="❓ Help", callback_data="/help")],
                            [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
                        ])
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
                    self.temp_users[chat_id] = {}

            except:
                self.temp_users[chat_id] = {}
                message = "<b>❌ [ERR 500] Problem with Connecting to Server, Please Try Again!</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin")],
                        [InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup")]
                    ])
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

        if command == '/add_device' and self.users[chat_id]["username"]:
            self.temp_device[chat_id] = {}
            self.last_command = '/add_device'
            message = "<b>🔹Please Make Ready Your SICU Device Receipt (You Could Find It In Your Purchase Box)</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')
            message = "<b>🔸[Step 1] Please Enter the 'Device ID' Code Carefully:</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

        elif command == '/add_device' and not self.users[chat_id]["username"]:
            self.last_command = None
            message = "<b>❌ [Error] Please First Sign-in or Sign-up to Add Device</b>"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin"),]
                 [InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup")],
                 [InlineKeyboardButton(text="❓ Help", callback_data="/help")], 
                 [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
            ])
            self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

        elif self.last_command=='/add_device' and "dev_id" not in self.temp_device[chat_id].keys():
            self.temp_device[chat_id]["dev_id"] = command
            message = "<b>🔸[Step 2] Then, Please Enter 'Device Password' Carefully:</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

        elif self.last_command=='/add_device' and "dev_password" not in self.temp_device[chat_id].keys():
            self.temp_device[chat_id]["dev_password"] = command

            message = "<b>🔄 Please wait ...</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

            try:
                json_req = {"dev_id":str(self.temp_device[chat_id]["dev_id"]),
                            "dev_password":str(self.temp_device[chat_id]["dev_password"]),
                            "username":str(self.users[chat_id]["username"])
                            }
                json_resp = requests.post(f"{self.serv_cat['address']}/add_device", json=json.dumps(json_req)).json()

                if json_resp['status']=='Device Registered Previously':
                    message = "<b>❌ [Error] This Device Has Been Previously Registered by Other Users.</b>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device")],
                        [InlineKeyboardButton(text="📟 My Devices", callback_data="/get_devices")],
                        [InlineKeyboardButton(text="❓ Help", callback_data="/help")], 
                        [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")],
                        [InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                    ])
                    self.temp_device[chat_id] = {}
                    self.last_command = None
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

                elif json_resp['status']=='Device Duplicate':
                    message = "<b>❌ [Error] You've Previously Registered This Device.</b>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Add New Device", callback_data="/add_device")],
                        [InlineKeyboardButton(text="My Devices", callback_data="/get_devices")]
                    ])
                    self.temp_device[chat_id] = {}
                    self.last_command = None
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

                elif json_resp['status']=='Device Not Found':
                    message = "<b>❌ [Error] Couldn't Find Any Device With This Information. Please Check Again The Device ID and Password.</b>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔂 Try Again", callback_data="/add_device")],
                        [InlineKeyboardButton(text="📟 My Devices", callback_data="/get_devices")],
                        [InlineKeyboardButton(text="❓ Help", callback_data="/help")], 
                        [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")],
                        [InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                    ])
                    self.temp_device[chat_id] = {}
                    self.last_command = None
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

                elif json_resp['status']=='Device Registered':
                    message = "<b>✅ Device Added Succesfully!</b>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Add New Device", callback_data="/add_device")],
                        [InlineKeyboardButton(text="My Devices", callback_data="/get_devices")]
                    ])

                    self.users[chat_id]['devices'].append(self.temp_device[chat_id]["dev_id"])
                    # Assign Chat ID to Device
                    self.devices[self.temp_device[chat_id]["dev_id"]] = chat_id
                    self.temp_device[chat_id] = {}
                    self.last_command = None
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

            except:
                self.temp_device[chat_id] = {}
                message = "<b>❌ [ERR 500] Problem with Connecting to Server, Please Try Again!</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔂 Try Again", callback_data="/add_device")],
                        [InlineKeyboardButton(text="📟 My Devices", callback_data="/get_devices")],
                        [InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                    ])
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

        if command == '/get_devices' and "username" in self.users[chat_id].keys():

            message = "<b>🔄 Please wait ...</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

            try:
                json_req = {"username":self.users[chat_id]["username"]}
                get_dev_resp = requests.get(f"{self.serv_cat['address']}/get_user_devices", params=json_req).json()
                self.users[chat_id]["devices"] = get_dev_resp["devices"]

                if self.users[chat_id]["devices"]:
                    message = "<b>📟 List of Registered Devices:</b>\n\n"
                    message += '\n'.join(f"▪️ <b>{device}</b>" for device in self.users[chat_id]['devices'])
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device")],
                        [InlineKeyboardButton(text="❓ Help", callback_data="/help")], 
                        [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")],
                        [InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                    ])
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
                
                else:
                    message = "<b>⚠️ [WARNING] No Devices Found! Do You Want to Add a New Device?</b>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device")],
                        [InlineKeyboardButton(text="❓ Help", callback_data="/help")], 
                        [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")],
                        [InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                    ])

                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
            except:
                message = "<b>❌ [ERR 500] Problem with Connecting to Server, Please Try Again!</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔂 Try Again", callback_data="/get_devices")],
                        [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device")],
                        [InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                    ])
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

if __name__ == "__main__":

    telegram_bot = TelegramBot()
    telegram_bot.start()
    telegram_bot_thread = threading.Thread(target=telegram_bot.update_service_status)
    telegram_bot_thread.daemon = True
    telegram_bot_thread.start()

    while True:
        pass