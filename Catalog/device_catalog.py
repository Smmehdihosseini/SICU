import os
import json
import time
from datetime import datetime
import cherrypy
from utils.ErrorHandler import SettError, ConfError
from utils.funcs import UserGen, TimeDiff
from colorama import Fore, Style
import threading


class DeviceCatalog:

    def __init__(self):

        self.users = []
        self.devices = []

        # Devices Catalog Base Path
        self.base_path = 'Catalog'

        # Loading Setting
        self.settings = self.init_sett()

        # Loading Configurations, Device Catalog and Device Info
        self.conf = self.init_conf()
        self.dev_cat_conf = self.conf['device_catalog']

        # Initilize Users, Devices and devices List
        self.init_load_users()
        self.init_load_devices()
        self.init_load_devices()

        self.url = self.dev_cat_conf['device_catalog']['url']
        self.port = self.dev_cat_conf['device_catalog']['port']

    def cat_url(self):
        return self.url

    def cat_port(self):
        return self.port
    
    # Intializing Settings
    def init_sett(self):

        self.path_settings = "/devices_settings.json"
        if os.path.exists(self.base_path+self.path_settings):
            try:
                with open(self.base_path+self.path_settings, 'r') as file:
                    self.settings = json.load(file)

                # MongoDB Device Settings
                self.path_conf = self.settings['device_settings']['path_conf']
                self.path_users = self.settings['device_settings']['path_users']
                self.path_devices = self.settings['device_settings']['path_devices']
                self.time_format = self.settings['device_settings']['time_format']

                # Configuration Load Timeout and Max Retry
                self.conf_timeout = self.settings['timesout_settings']['conf_timeout']
                self.conf_maxretry = self.settings['timesout_settings']['conf_maxretry']

                # Offline Device Threshold (s)
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

    # Create/Open Users List
    def init_load_users(self):
        if os.path.exists(self.base_path+'/'+self.path_users):
            with open(self.base_path+'/'+self.path_users, 'r') as file:
                self.users = json.load(file)
        else:
            self.users = []
            with open(self.base_path+'/'+self.path_users, 'w') as file:
                json.dump(self.users, file, indent=4)

    # Create/Open Devices List
    def init_load_devices(self):
        if os.path.exists(self.base_path+'/'+self.path_devices):
            with open(self.base_path+'/'+self.path_devices, 'r') as file:
                self.devices = json.load(file)
        else:
            self.devices = []
            with open(self.base_path+'/'+self.path_devices, 'w') as file:
                json.dump(self.devices, file, indent=4)

    # Create/Open devices List
    def init_load_devices(self):
        if os.path.exists(self.base_path+'/'+self.path_devices):
            with open(self.base_path+'/'+self.path_devices, 'r') as file:
                self.devices = json.load(file)
        else:
            self.devices = []
            with open(self.base_path+'/'+self.path_devices, 'w') as file:
                json.dump(self.devices, file, indent=4)
    
    # Update Users List
    def update_users_list(self):
        with open(self.base_path+'/'+self.path_users, 'w') as file:
            json.dump(self.users, file, indent=4)

    # Update Devices List
    def update_devices_list(self):
        with open(self.base_path+'/'+self.path_devices, 'w') as file:
            json.dump(self.devices, file, indent=4)
    
    # Get User Devices
    def get_user_devices(self, username):
        user_devs =  next((user for user in self.users if user["username"]==username), None)['devices']
        return {"devices": user_devs}
    
    # User Authentication
    def auth_user(self, username, password):
        user_obj = next((user for user in self.users if user["username"]==username and user["password"]==password), None)
        if user_obj:
            return {'authenticated': True,
                       'devices':user_obj['devices']}
        else:
            return {'authenticated': False}
        
    # User Registeration	
    def reg_user(self, organization, password):
        
        user_obj = True
        while user_obj:
            username = UserGen(organization)
            user_obj = next((user for user in self.users if user["username"]==username), None)

        new_user_obj =  {
                            "username": username,
                            "password": password,
                            "organization": organization,
                            "devices": []
                        }
        self.users.append(new_user_obj)
        self.update_users_list()
        return {'registered': True, 'username':username}
        
    # Add Device By User
    def add_dev(self, dev_id, dev_password, username):
        dev_obj = next(((index, dev) for index, dev in enumerate(self.devices) if dev["dev_id"]==dev_id and dev["dev_password"]==dev_password), None)
        if dev_obj:
            dev_ind, dev_info = dev_obj
            if dev_info['reg_user']!=" ":
                if dev_info['reg_user']==username:
                    return {'status': "Device Duplicate"}
                else:
                    return {'status': "Device Registered Previously"}
            else:
                user_ind, _ = next(((index, user) for index, user in enumerate(self.users) if user["username"]==username), None)
                self.users[user_ind]['devices'].append(dev_id)
                self.devices[dev_ind]['reg_user'] = username
                self.update_users_list()
                self.update_devices_list()
                return {'status': "Device Registered"}
        else:
            return {'status': "Device Not Found"}
        
    def reg_device(self, params):
        serv_obj = next(((index, serv) for index, serv in enumerate(self.devices) if serv["id"]==params['id']), None)

        if serv_obj:
            serv_ind, serv_info = serv_obj
            if serv_info['name']==params['name']:
                self.devices[serv_ind] = params
                self.devices[serv_ind]['last_update'] = datetime.now().strftime(self.time_format)
                self.update_devices_list()
                print(f"{Fore.LIGHTYELLOW_EX}+ [SRV=UPDATE][{self.devices[serv_ind]['last_update']}] Device ID: {self.devices[serv_ind]['id']} Updated{Fore.RESET}")
                return {'status': 'Updated'}
            else:
                return {'status': "Failed", 'log':'Device ID Not Available'}
        else:
            address_dup = False
            address_dup_list = []
            for param_endpoint in params['endpoints']:
                for Device in self.devices:
                    for endpoint in Device['endpoints']:
                        if param_endpoint['address']==endpoint['address']:
                            address_dup = True
                            address_dup_list.append(param_endpoint['address'])

            if address_dup==False:
                new_device = params.copy()
                new_device['last_update'] = datetime.now().strftime(self.time_format)
                self.devices.append(new_device)
                self.update_devices_list()
                print(f"{Fore.GREEN}+ [{new_device['last_update']}][SRV=ONLINE] Device ID: {new_device['id']} Registered{Fore.RESET}")
                return {'status': "Registered"}
            else:
                return {'status': "Failed", 'log':f'Address(s) [{", ".join(address_dup_list)}] Already Exists'}
            
    def check_devices(self):
        offline_devices = []
        online_devices = []
        for index, item in enumerate(self.devices):
            time_now = datetime.now().strftime(self.time_format)
            if TimeDiff(item['last_update'], time_now)>self.update_thresh:
                offline_devices.append(item['id'])
                removed_item = self.devices.pop(index)
            else:
                online_devices.append(item['id'])
                
        self.update_devices_list()
        print(f"{Fore.CYAN}+ [{time_now}] devices Status:{Fore.RESET}")
        print(f"{Fore.CYAN}- ONLINE devices:{', '.join(online_devices)}{Fore.RESET}")
        print(f"{Fore.CYAN}- OFFLINE devices:{', '.join(offline_devices)} Registered{Fore.RESET}")

        time.sleep(self.update_thresh)


class deviceCatalogWebdevice:

    exposed = True

    def __init__(self):
        self.dev_cat = DeviceCatalog()

    def devices_status(self):
        while True:
            self.dev_cat.check_devices()

    def webdevice_url(self):
        return self.dev_cat.cat_url()
    
    def webdevice_port(self):
        return self.dev_cat.cat_port()
    
    def webdevice_conf(self):
        return {
                    '/': {
                        'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                        'tools.sessions.on': True
                    }
                }

    def GET(self, *uri, **params):
        if len(uri)>0:

            # Fetch User Devices List | Telegram Bot
            if str(uri[0])=="get_user_devices":
                try:
                    if "username" in params:
                        return json.dumps({"devices": self.dev_cat.get_user_devices(params["username"])})
                    else:
                        raise cherrypy.HTTPError(404, "User Not Found")
                except:
                    raise cherrypy.HTTPError(400, "Invalid Parameters")
                
            # Authenticate Users | Telegram Bot	& Web Application
            if str(uri[0])=="auth_user":
                if "username" and "password" in params:
                    return json.dumps(self.dev_cat.auth_user(params["username"],
                                                                  params["password"]))
                else:
                    raise cherrypy.HTTPError(400, "Invalid Parameters")
                
    @cherrypy.tools.json_in()			
    @cherrypy.tools.json_out()			
    def POST(self, *uri, **params):
        if len(uri)>0:   
            if str(uri[0])=="reg_user":
                request_body = json.loads(cherrypy.request.json)
                if "organization" and "password" in request_body.keys():
                    return self.dev_cat.reg_user(request_body["organization"],
                                                              request_body["password"])
                else:
                    raise cherrypy.HTTPError(400, "Invalid Parameters")
                    
            elif str(uri[0])=="add_device":
                request_body = json.loads(cherrypy.request.json)
                if "dev_id" and "dev_password" and "username" in request_body.keys():
                    return self.dev_cat.add_dev(request_body["dev_id"],
                                                             request_body["dev_password"],
                                                             request_body["username"])
                else:
                    raise cherrypy.HTTPError(400, "Invalid Parameters")
                
            elif str(uri[0])=="reg_device":
                request_body = json.loads(cherrypy.request.json)
                if 'id' and 'name' and 'endpoints' in request_body.keys():
                    return self.dev_cat.reg_device(request_body)
                
if __name__ == '__main__':

    device_cat_webdevice = deviceCatalogWebdevice()
    cherrypy.tree.mount(device_cat_webdevice, '/', device_cat_webdevice.webdevice_conf())
    cherrypy.config.update({'server.socket_host': device_cat_webdevice.webdevice_url()})
    cherrypy.config.update({'server.socket_port': device_cat_webdevice.webdevice_port()})

    function_thread = threading.Thread(target=device_cat_webdevice.devices_status())
    function_thread.daemon = True
    cherrypy.engine.start()
    cherrypy.engine.block()