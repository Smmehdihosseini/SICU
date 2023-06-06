import telepot
import paho.mqtt.client as PahoMQTT
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from colorama import Fore, Style
from utils.ErrorHandler import BrokerError, MessageLoopError
import datetime
import requests
import random
import json
import time

class TelegramBot:

    def __init__(self,
                 token,
                 clientID='Telegram Bot',
                 msg_broker='localhost',
                 msg_broker_port=1883):

        self.bot = telepot.Bot(token)
        self.users = {}
        self.devices = {}
        self.temp_users = {}
        self.temp_device = {}
        self.last_command = None

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

    def start(self):

        try: 
            # Connect  MQTT Broker Connection
            self.paho_mqtt.connect(self.msg_broker, self.msg_broker_port)
            self.paho_mqtt.loop_start()

            ## Subscribe to All Topics in System
            for topic in self.topic_list:
                self.paho_mqtt.subscribe(f"+/{topic}/reports", self.QoS)
                self.paho_mqtt.subscribe(f"+/{topic}/warnings", self.QoS)

        except:
            raise BrokerError("Error Occured with Connecting MQTT Broker")
        
        try:
            self.bot.message_loop(self.bot_chat_handler)
        except:
            raise MessageLoopError("Error Occured with Starting Telegram Message Loop")
        
        print(f"{Fore.YELLOW}\n+ Telegram Bot: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")
        

    def on_connect(self, paho_mqtt, userdata, flags, rc):

        print(f"\n{Fore.YELLOW}+ Connected to MQTT Broker '{self.msg_broker}' [code={rc}]{Fore.RESET}")

    def on_message(self, paho_mqtt , userdata, msg):

        # On Getting New Message
        # 'P300/oxygen/measurements
        _id, _sens_cat, _sens_type = msg.topic.split('/')
        msg_body = json.loads(msg.payload.decode('utf-8'))

        print (f"{Fore.GREEN}{Style.BRIGHT}[SUB]{Style.NORMAL} {str(_sens_type).capitalize()} Recieved [{msg_body['bt']}]: Topic: '{msg.topic}' - QoS: '{str(msg.qos)}' - Message: {Fore.RESET}'{str(msg_body)}")

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

                    if "Diastolic" in msg_body['e'][0]['n']:
                        pressure_type_name = 'Diastolic'
                    else:
                        pressure_type_name = 'Systolic'
                    
                    message = f"<b> ⚠️🩸⚠️ [Blood Pressure Warning], {msg_body['e'][0]['n']}! for {_id} :</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n" 
                    message += f"🔺 <b>{pressure_type_name}:</b>: <i>{msg_body['e'][0]['v']} {msg_body['u']}</i>\n"

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
                    
                    message = f"<b>⚠️🫁⚠️ [Oxygen Stauration Warning], {msg_body['e'][0]['n']}! for '{_id}':</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n" 
                    message += f"🔺 <b>SpO2:</b>: <i>{msg_body['e'][0]['v']} {msg_body['u']}</i>\n"

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
                    
                    warning = {"⏳ Date and Time:":datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'),
                        "🏷 Maximum Heartrate :": f"{msg_body['e'][0]['v']['max_freq']} {msg_body['u']}",
                        "🏷 Minimum Heartrate :": f"{msg_body['e'][0]['v']['min_freq']} {msg_body['u']}",
                        "🏷 Mean Heartrate :": f"{msg_body['e'][0]['v']['mean_freq']} {msg_body['u']}",
                        "🏷 Maximum R-R :": f"{msg_body['e'][0]['v']['max_rr']}",
                        "🏷 Minimum R-R :": f"{msg_body['e'][0]['v']['min_rr']}",
                        "🏷 Mean R-R :": f"{msg_body['e'][0]['v']['mean_rr']}",
                        "🏷 STD R-R :": f"{msg_body['e'][0]['v']['std_rr']}"                        
                        }
                    
                    message = f"<b>⚠️🫀⚠️ [ECG Warning], {msg_body['e'][0]['n']}! for '{_id}':</b>\n\n"
                    message += f"⏳ <b>Date and Time:</b> <i>{str(datetime.datetime.fromtimestamp(msg_body['bt']).strftime('%Y-%m-%d %H:%M:%S'))}</i>\n"
                    message += f"🔺 <b>Maximum Heartrate:</b> <i>{str(msg_body['e'][0]['v']['max_freq'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Minimum Heartrate:</b> <i>{str(msg_body['e'][0]['v']['min_freq'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Mean Heartrate:</b> <i>{str(msg_body['e'][0]['v']['mean_freq'])} {msg_body['u']}</i>\n"
                    message += f"🔺 <b>Maximum R-R:</b> <i>{str(msg_body['e'][0]['v']['max_rr'])}</i>\n"
                    message += f"🔺 <b>Minimum R-R:</b> <i>{str(msg_body['e'][0]['v']['min_rr'])}</i>\n"
                    message += f"🔺 <b>Mean R-R:</b> <i>{str(msg_body['e'][0]['v']['mean_rr'])}</i>\n"
                    message += f"🔺 <b>STD R-R:</b> <i>{str(msg_body['e'][0]['v']['std_rr'])}</i>\n"
                    message += f"\n\n ‼️ <b>Note :</b> Please Visit SICU Web Application to See ECG Envelope"

                    self.bot.sendMessage(chat_user, message, parse_mode='HTML', reply_markup=keyboard)


    def gen_username(self, org_name):
        initials = ''.join(word[0].upper() for word in org_name.split(' '))
        num = str(random.randint(1, 99999))
        username = 'U' + initials + num
        return username

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

            json_req = {"username":self.temp_users[chat_id]["username"], "password":self.temp_users[chat_id]["password"]}
            signin_resp = requests.post("http://localhost:8080/authenticate", json=json_req)
            json_resp = signin_resp.json()

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
            self.temp_users[chat_id]["username"] = self.gen_username(self.temp_users[chat_id]["organization"])
            message = "<b>🔄 Please Wait ...</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

            json_req = {"username":self.temp_users[chat_id]["username"],
                        "password":self.temp_users[chat_id]["password"],
                        "organization":self.temp_users[chat_id]["organization"]
                        }
            signup_resp = requests.post("http://localhost:8080/register", json=json_req)
            json_resp = signup_resp.json()

            if json_resp['register']:
                self.users[chat_id]["username"] = self.temp_users[chat_id]["username"]
                self.users[chat_id]["password"] = self.temp_users[chat_id]["password"]
                self.users[chat_id]["devices"] = []
                self.last_command = None

                message = "<b>✅ Your Information Has Been Successfully Registered. Here Are Your Credentials: \n\n</b>"
                message += f"▪️ <b>Username:</b> <i>{self.temp_users[chat_id]['username']}</i>\n"
                message += f"▪️ <b>Password:</b> <i>{self.temp_users[chat_id]['password']}</i>\n"
                message += f"▪️ <b>Organization:</b> <i>{self.temp_users[chat_id]['organization']}</i>\n\n"
                message += f"❗️<b>Note:</b> <i>DO NOT SHARE THIS CREDENTIALS WITH ANYONE</i>\n"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/add_device")],
                         [InlineKeyboardButton(text="❓ Help", callback_data="/help")],
                         [InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
                    ])
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
                self.temp_users[chat_id] = {}

            else:
                self.temp_users[chat_id] = {}
                self.last_command = None
                message = "<b>❌ [Error] Username is Taken, Try Again!</b>\n\n"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔂 Try Again", callback_data="/signup")]
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

            json_req = {"dev_id":str(self.temp_device[chat_id]["dev_id"]),
                        "dev_password":str(self.temp_device[chat_id]["dev_password"]),
                        "username":str(self.users[chat_id]["username"])
                        }
            add_dev_resp = requests.post("http://localhost:8080/add_device", json=json_req)
            json_resp = add_dev_resp.json()

            if json_resp['status']=='Dev Pre-Reg':
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

            elif json_resp['status']=='Dev Duplicate':
                message = "<b>❌ [Error] You've Previously Registered This Device.</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Add New Device", callback_data="/add_device")],
                      [InlineKeyboardButton(text="My Devices", callback_data="/get_devices")]
                ])
                self.temp_device[chat_id] = {}
                self.last_command = None
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

            elif json_resp['status']=='Dev Not Exist':
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

            elif json_resp['status']=='Dev Added':
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

        if command == '/get_devices' and "username" in self.users[chat_id].keys():

            message = "<b>🔄 Please wait ...</b>"
            self.bot.sendMessage(chat_id, message, parse_mode='HTML')

            json_req = {"username":self.users[chat_id]["username"]}
            get_dev_resp = requests.get("http://localhost:8080/get_devices", json=json_req)
            json_resp = get_dev_resp.json()
            self.users[chat_id]["devices"] = json_resp["devices"]

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

if __name__ == "__main__":

    TOKEN = '<TOKEN>' 
    tel_bot = TelegramBot(TOKEN)
    tel_bot.start()

    while True:
        pass