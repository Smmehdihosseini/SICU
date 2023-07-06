import os
import json
import time
from datetime import datetime
import threading
import cherrypy
from colorama import Fore
from utils.ErrorHandler import SettError, ConfError
from utils.funcs import TimeDiff

class DeviceCatalog:

    def __init__(self):

        self.devices = []

        # devices Catalog Base Path
        self.base_path = 'Catalog'

        # Loading Setting
        self.settings = self.init_sett()

        # Loading Configurations, Device Catalog and Device Info
        self.conf = self.init_conf()
        self.dev_cat_conf = self.conf['device_catalog']

        # Initilize Devices
        self.init_load_devices()

        self.url = self.dev_cat_conf['url']
        self.port = self.dev_cat_conf['port']

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

    # Update Devices List
    def update_devices_list(self):
        with open(self.base_path+'/'+self.path_devices, 'w') as file:
            json.dump(self.devices, file, indent=4)
        
    def reg_device(self, params):
        self.init_load_devices()
        dev_obj = next(((index, dev) for index, dev in enumerate(self.devices) if dev["dev_id"]==params['dev_id']), None)

        if dev_obj:
            dev_ind, dev_info = dev_obj
            temp_reg_user = self.devices[dev_ind]['reg_user']
            self.devices[dev_ind] = params
            self.devices[dev_ind]['reg_user'] = temp_reg_user
            self.devices[dev_ind]['last_update'] = datetime.now().strftime(self.time_format)
            self.update_devices_list()
            print(f"{Fore.LIGHTYELLOW_EX}+ [DEV=UPDATE][{self.devices[dev_ind]['last_update']}] Device ID: {self.devices[dev_ind]['dev_id']} Updated{Fore.RESET}")
            return {'status': 'Updated'}

        else:
            address_dup = False
            address_dup_list = []
            for param_endpoint in params['endpoints']:
                for Device in self.devices:
                    for endpoint in Device['endpoints']:
                        if params['endpoints'][param_endpoint]['address']==Device['endpoints'][endpoint]['address']:
                            address_dup = True
                            address_dup_list.append(params['endpoints'][param_endpoint]['address'])

            if address_dup==False:
                new_device = params.copy()
                new_device['reg_user'] = " "
                new_device['last_update'] = datetime.now().strftime(self.time_format)
                self.devices.append(new_device)
                self.update_devices_list()
                print(f"{Fore.GREEN}+ [{new_device['last_update']}][DEV=ONLINE] Device ID: {new_device['dev_id']} Registered{Fore.RESET}")
                return {'status': "Registered"}
            else:
                return {'status': "Failed", 'log':f'Address(s) [{", ".join(address_dup_list)}] Already Exists'}
            
    def check_devices(self):
        offline_devices = []
        online_devices = []
        time_now = datetime.now().strftime(self.time_format)
        for index, item in enumerate(self.devices):
            if TimeDiff(item['last_update'], time_now)>self.update_thresh:
                offline_devices.append(item['dev_id'])
            else:
                online_devices.append(item['dev_id'])
                
        print(f"{Fore.CYAN}+ [{time_now}] Devices Status:{Fore.RESET}")
        print(f"{Fore.CYAN}- No. ONLINE Devices: [{len(online_devices)}]{Fore.RESET}")
        print(f"{Fore.CYAN}- No. OFFLINE Devices: [{len(offline_devices)}]{Fore.RESET}")

        time.sleep(self.update_thresh)


class DeviceCatalogWebService:

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
                
    @cherrypy.tools.json_in()			
    @cherrypy.tools.json_out()			
    def POST(self, *uri, **params):
        if len(uri)>0:             
            if str(uri[0])=="reg_device":
                request_body = json.loads(cherrypy.request.json)
                if 'dev_id' and 'name' and 'endpoints' in request_body.keys():
                    return self.dev_cat.reg_device(request_body)
                
if __name__ == '__main__':

    device_cat_webdevice = DeviceCatalogWebService()
    cherrypy.tree.mount(device_cat_webdevice, '/', device_cat_webdevice.webdevice_conf())
    cherrypy.config.update({'server.socket_host': device_cat_webdevice.webdevice_url()})
    cherrypy.config.update({'server.socket_port': device_cat_webdevice.webdevice_port()})
    cherrypy.engine.start()
    device_cat_webdevice_thread = threading.Thread(target=device_cat_webdevice.devices_status)
    device_cat_webdevice_thread.daemon = True
    device_cat_webdevice_thread.start()
    cherrypy.engine.block()

    try:
        while True:
            pass
    except KeyboardInterrupt:
        cherrypy.engine.stop()
        device_cat_webdevice_thread.terminate()