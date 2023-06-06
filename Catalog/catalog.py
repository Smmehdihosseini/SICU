import cherrypy
import json

class Catalog:

    exposed = True

    def __init__(self):
        self.catalog = []

    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def GET(self, *uri, **params):

        if len(uri)>0:

            if str(uri[0])=="get_devices":

                input_json = cherrypy.request.json
                username = input_json.get('username')

                with open('Catalog/users.json', 'r') as file:
                    users = json.load(file)

                devices_list = []
                for user in users:
                    if user['username']==username:
                        devices_list = user["devices"]

                return {"devices":devices_list}

    @cherrypy.tools.json_out()
    @cherrypy.tools.json_in()
    def POST(self, *uri, **params):

        if len(uri)>0:   

            if str(uri[0])=="authenticate":
                
                input_json = cherrypy.request.json
                username = input_json.get('username')
                password = input_json.get('password')

                with open('Catalog/users.json', 'r') as file:
                    users = json.load(file)

                authenticated = False
                for user in users:
                    if user['username']==username and user['password']==password:
                        authenticated = True
                        devs_list = user['devices']
                        break

                if authenticated:
                    return {'authenticated': True,
                            'devices':devs_list}
                else:
                    return {'authenticated': False}
                
            elif str(uri[0])=="register":

                input_json = cherrypy.request.json
                username = input_json.get('username')
                password = input_json.get('password')
                organization = input_json.get('organization')

                with open('Catalog/users.json', 'r') as file:
                    users = json.load(file)

                registered = False
                for user in users:
                    if user['username']==username:
                        registered = True
                        break

                if registered:
                    return {'register': False}

                else:

                    new_user =  {
                                    "username": username,
                                    "password": password,
                                    "organization": organization,
                                    "devices": []
                                }

                    users.append(new_user)

                    with open('Catalog/users.json', 'w') as file:
                        json.dump(users, file, indent=4)

                    return {'register': True}
                
            elif str(uri[0])=="add_device":

                input_json = cherrypy.request.json
                device_id = input_json.get('dev_id')
                password = input_json.get('dev_password')
                username = input_json.get('username')

                with open('Catalog/users.json', 'r') as file:
                    users = json.load(file)

                with open('Catalog/devices.json', 'r') as file:
                    devices = json.load(file)

                duplicate = False
                registered = False
                exists = False

                dev_index = None
                for n_dev in range(len(devices)):
                    if devices[n_dev]['dev_id']==device_id and devices[n_dev]['password']==password:
                        exists = True
                        dev_index = n_dev
                        if devices[n_dev]['reg_user']!="None":
                            if devices[n_dev]['reg_user']==username:
                                duplicate = True
                                break
                            else:
                                registered = True
                                break

                for n_user in range(len(users)):
                    if users[n_user]['username']==username:
                        user_index = n_user

                if exists:

                    if registered:
                        return {'status': 'Dev Pre-Reg'}
                    
                    elif duplicate:
                        return {'status': 'Dev Duplicate'}

                    else:
                        users[user_index]['devices'].append(device_id)
                        devices[dev_index]['reg_user'] = username

                        with open('Catalog/users.json', 'w') as file:
                            json.dump(users, file, indent=4)

                        with open('Catalog/devices.json', 'w') as file:
                            json.dump(devices, file, indent=4)

                        return {'status': 'Dev Added'}

                else:
                    return {'status': "Dev Not Exist"}

if __name__ == '__main__':

    # Set Port and URL
    port = 8080
    url = '0.0.0.0'

    # Configure CherryPy server
    cherrypy.config.update({'server.socket_host': url, 'server.socket_port': port})
    cherrypy.tree.mount(Catalog(), '/',
                        {'/':
                         {'request.dispatch': cherrypy.dispatch.MethodDispatcher(),
                          'tools.sessions.on': True}})

    # Start the CherryPy server
    cherrypy.engine.start()
    cherrypy.engine.block()