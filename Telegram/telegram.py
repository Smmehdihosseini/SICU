import telepot
from telepot.loop import MessageLoop
from telepot.namedtuple import ReplyKeyboardMarkup, KeyboardButton
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
import time
import requests
import random
from colorama import Fore, Style


class TelegramBot:

    def __init__(self, token):

        self.bot = telepot.Bot(token)
        self.users = {}
        self.temp_users = {}
        self.temp_device = {}
        self.last_command = None


    def genUsername(self, org_name):
        initials = ''.join(word[0].upper() for word in org_name.split(' '))
        num = str(random.randint(1, 99999))
        username = 'U' + initials + num
        return username

    def BotChatHandler(self, msg):

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
                [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin"),
                 InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup"),
                 InlineKeyboardButton(text="❓ Help", callback_data="/help"), 
                 InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
            ])

            self.bot.sendMessage(chat_id, '<b>Welcome to SICU Telegrambot! How can I Help You?</b>', reply_markup=keyboard)

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
                self.temp_users[chat_id] = {}
                self.last_command = None
                message = "<b>🟢↪️ You're Signed-In Succesfully!</b>"
                self.bot.sendMessage(chat_id, message, parse_mode='HTML')

                if self.users[chat_id]["devices"]:
                    message = "<b>📟 List of Registered Devices:</b>\n\n"
                    message += '\n'.join(f"▪️ <b>{device}</b>" for device in self.users[chat_id]['devices'])
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device"),
                         InlineKeyboardButton(text="❓ Help", callback_data="/help"),
                         InlineKeyboardButton(text="⚜️ About Us", callback_data="/about"),
                         InlineKeyboardButton(text="🔴↩️Sign-out", callback_data="/signout")]
                    ])
                    self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
                
                else:
                    message = "<b>⚠️ [WARNING] No Devices Found! Do You Want to Add a New Device?</b>"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="➕ Yes, Add Device", callback_data="/add_device"),
                         InlineKeyboardButton(text="❓ Help", callback_data="/help"),
                         InlineKeyboardButton(text="⚜️ About Us", callback_data="/about"),
                         InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
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
            message = "<b>🔴↩️ You're Signed-Out!</b>"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin"),
                 InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup"),
                 InlineKeyboardButton(text="❓ Help", callback_data="/help"), 
                 InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
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
            self.temp_users[chat_id]["username"] = self.genUsername(self.temp_users[chat_id]["organization"])
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
                        [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/add_device"),
                         InlineKeyboardButton(text="❓ Help", callback_data="/help"),
                         InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
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
                [InlineKeyboardButton(text="🟢↪️ Sign-in", callback_data="/signin"),
                 InlineKeyboardButton(text="🆕 Sign-up", callback_data="/signup"),
                 InlineKeyboardButton(text="❓ Help", callback_data="/help"), 
                 InlineKeyboardButton(text="⚜️ About Us", callback_data="/about")]
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
                    [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device"),
                    InlineKeyboardButton(text="📟 My Devices", callback_data="/get_devices"),
                    InlineKeyboardButton(text="❓ Help", callback_data="/help"), 
                    InlineKeyboardButton(text="⚜️ About Us", callback_data="/about"),
                    InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                ])
                self.temp_device[chat_id] = {}
                self.last_command = None
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

            elif json_resp['status']=='Dev Duplicate':
                message = "<b>❌ [Error] You've Previously Registered This Device.</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Add New Device", callback_data="/add_device"),
                      InlineKeyboardButton(text="My Devices", callback_data="/get_devices")]
                ])
                self.temp_device[chat_id] = {}
                self.last_command = None
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

            elif json_resp['status']=='Dev Not Exist':
                message = "<b>❌ [Error] Couldn't Find Any Device With This Information. Please Check Again The Device ID and Password.</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔂 Try Again", callback_data="/add_device"),
                     InlineKeyboardButton(text="📟 My Devices", callback_data="/get_devices"),
                     InlineKeyboardButton(text="❓ Help", callback_data="/help"), 
                     InlineKeyboardButton(text="⚜️ About Us", callback_data="/about"),
                     InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                ])
                self.temp_device[chat_id] = {}
                self.last_command = None
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

            elif json_resp['status']=='Dev Added':
                message = "<b>✅ Device Added Succesfully!</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Add New Device", callback_data="/add_device"),
                     InlineKeyboardButton(text="My Devices", callback_data="/get_devices")]
                ])

                self.users[chat_id]['devices'].append(self.temp_device[chat_id]["dev_id"])
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
                    [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device"),
                    InlineKeyboardButton(text="❓ Help", callback_data="/help"), 
                    InlineKeyboardButton(text="⚜️ About Us", callback_data="/about"),
                    InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                ])
                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)
            
            else:
                message = "<b>⚠️ [WARNING] No Devices Found! Do You Want to Add a New Device?</b>"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Add New Device", callback_data="/add_device"),
                    InlineKeyboardButton(text="❓ Help", callback_data="/help"), 
                    InlineKeyboardButton(text="⚜️ About Us", callback_data="/about"),
                    InlineKeyboardButton(text="🔴↩️ Sign-out", callback_data="/signout")]
                ])

                self.bot.sendMessage(chat_id, message, parse_mode='HTML', reply_markup=keyboard)

    def run(self):

        self.bot.message_loop(self.BotChatHandler)
        print(f"{Fore.YELLOW}\n+ Telegram Bot: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")


if __name__ == "__main__":

    TOKEN = '6202650288:AAFrwS5Q1OgrHg6HV8o9Mh5OBDqQHI5oSR4' 
    tel_bot = TelegramBot(TOKEN)
    tel_bot.run()

    while True:
        pass