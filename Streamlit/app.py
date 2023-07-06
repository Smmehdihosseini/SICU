
import os
import time
import json
import toml
import threading
import requests
import pandas as pd
import streamlit as st
from colorama import Fore
from PIL import Image, ImageFilter
from streamlit_extras.add_vertical_space import add_vertical_space as VERTICAL_SPACE
from utils.ErrorHandler import ConfError, SettError, CatError

class SICU_WEB:	

    def __init__(self):

        self.base_path = ""

        # Loading Setting
        self.settings = self.init_sett()

        # Loading Configurations, Service Catalog and Service Info
        self.conf = self.init_conf()
        self.serv_cat = self.conf['service_catalog']
        self.serv_info = self.conf['service_info']

        self.streamlit_url = self.serv_info['endpoints']['REST']['url'] 
        self.streamlit_port = self.serv_info['endpoints']['REST']['port']

        self.mongodb_rest_address= self.serv_info['connections']['MongoDB']['REST']['address']

    def init_sett(self):

        # Intializing Settings
        self.path_settings = "settings.json"
        if os.path.exists(self.base_path+self.path_settings):
            try:
                with open(self.base_path+self.path_settings, 'r') as file:
                    self.settings = json.load(file)

                # Streamlit Service Settings
                self.path_conf = self.settings['service_settings']['path_conf']
                self.app_title = self.settings['service_settings']['app_title']
                self.app_layout = self.settings['service_settings']['app_layout']
                self.app_sidebar_init_state = self.settings['service_settings']['app_sidebar_init_state']
                self.app_logo_path = self.settings['service_settings']['app_logo_path']
                self.app_sidebarlogo_path = self.settings['service_settings']['app_sidebarlogo_path']
                self.dir_config = self.settings['service_settings']['dir_config']

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

    def init_conf(self):

        # Intializing Configurations
        conf_retries = 0
        conf_loaded = False
        if os.path.exists(self.base_path+self.path_conf):
            with open(self.base_path+self.path_conf, 'r') as file:
                self.conf = json.load(file)
        else:
            # Retry to Load Configuration File - If Reaches to Max Retry, Raise an Error
            while not conf_loaded:
                if conf_retries==self.conf_maxretry:
                    raise ConfError(f"Failed to Load Configuration File ({self.base_path}/{self.path_conf}): Max Retries Reached ({self.conf_maxretry})")
                print(f"{Fore.RED}[CNF] Failed to Load Configuration File, Retrying in {self.conf_timeout} Seconds ({conf_retries}/{self.conf_maxretry}) {Fore.RESET}")
                time.sleep(self.conf_timeout)
                try:
                    with open(self.base_path+self.path_conf, 'r') as file:
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
                    service_registered = True
                    print(f"{Fore.LIGHTYELLOW_EX}+ [SRV=OK] Re-registered to 'Service Catalog'{Fore.RESET}")
                elif json_resp['status']=='Updated':
                    service_registered = True
                    print(f"{Fore.LIGHTYELLOW_EX}+ [SRV=OK] Updated in 'Service Catalog'{Fore.RESET}")

            except:
                print(f"{Fore.RED}[SRV] Failed to Update to Service Catalog! {Fore.RESET}")

            time.sleep(self.update_thresh)

    def start(self):

        # Start Streamlit Service
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
        
        print(f"{Fore.LIGHTYELLOW_EX}\n+ [SRV=OK] {self.serv_info['name']} Service: [ONLINE] ...\n----------------------------------------------------------------------------------{Fore.RESET}")

    def set_app_config(self):
        
        # Set Streamlit UI Application Configurations
        # Load the config.toml File
        with open(self.dir_config, 'r') as file:
            config = toml.load(file)

        # Set Streamlit URL and Port
        config['server']['port'] = self.streamlit_port
        config['browser']['serverAddress'] = self.streamlit_url
        config['browser']['serverPort'] = self.streamlit_port

        # Save the config.toml File
        with open(self.dir_config, 'w') as file:
            toml.dump(config, file)

        # Start Page Config
        st.set_page_config(page_title=self.app_title,
                           layout=self.app_layout,
                           initial_sidebar_state=self.app_sidebar_init_state,
                           page_icon=Image.open(self.app_logo_path))
        
        # Hide Header / Footer / Ham Burger Menu
        hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
        
        st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    def init_session_states(self):

        # Initial Session State Variables
        if 'live_data' not in st.session_state:
            st.session_state['live_data'] = False
        if 'auth' not in st.session_state:
            st.session_state['auth'] = None
        if 'username' not in st.session_state:
            st.session_state['username'] = None
        if 'password' not in st.session_state:
            st.session_state['password'] = None
        if 'devices' not in st.session_state:
            st.session_state['devices'] = None

    def run_app_navigation(self):

        # Navigation
        auth_placeholder = st.sidebar.empty()

        if st.session_state['auth']==None or st.session_state['auth']==False:

            with auth_placeholder:
                logo_sidebar = Image.open(self.app_sidebarlogo_path)
                logo_sidebar.thumbnail((1000, 1000), Image.BICUBIC)
                logo_sidebar = logo_sidebar.filter(ImageFilter.SHARPEN)

                with st.sidebar.columns([1,1,1])[1]:
                    st.sidebar.image(logo_sidebar)

                with st.sidebar:
                    VERTICAL_SPACE(2)
                    auth_option = st.radio(label="Choose:", options=["Sign-in", "Sign-up"], key="sidebar-auth-option", label_visibility="collapsed")
                    if auth_option=="Sign-in":
                        signin_form = st.form(key="signin-form")
                        signin_form.header('Sign-in to SICU Dashboard:')

                        username = signin_form.text_input(label="Username", key='sub-signin-username')
                        password = signin_form.text_input(label="Password", type='password', key='sub-signin-password')
                        signin_btn = signin_form.form_submit_button(label="Sign-in", type='primary', use_container_width=True)

                        if signin_btn:
                            json_req = {"username":username, "password":password}
                            json_resp = requests.get(f"{self.serv_cat['address']}/auth_user", params=json_req).json()
                            if json_resp['authenticated']==True: 
                                st.session_state['auth'] = True
                                st.session_state['username'] = username
                                st.session_state['password'] = password
                                st.session_state['devices'] = json_resp["devices"]
                            else:
                                st.session_state['auth']=False
                    else:
                        signup_form = st.form(key="signup-form")
                        signup_form.header('Sign-up to SICU Dashboard:')
                        organization = signup_form.text_input(label="Organization", key='sub-signup-organization')
                        password = signup_form.text_input(label="Password", type='password', key='sub-signup-password')
                        signup_btn = signup_form.form_submit_button(label="Sign-up", type='primary', use_container_width=True)
                        if signup_btn:
                            if organization and password:
                                json_req = {"organization":organization,
                                            "password":password
                                            }
                                json_resp = requests.post(f"{self.serv_cat['address']}/reg_user", json=json.dumps(json_req)).json()
                                if json_resp['registered']==True:
                                    st.success("Sign-up Succesfully! Here are your credentials:")
                                    st.warning(f"Username: {json_resp['username']}")
                                    st.warning(f"Password: {json_req['password']}")
                            else:
                                st.error("Missing Organization/Password !")

        # Check the Authentication Status
        elif st.session_state['auth']:

            with st.sidebar:
                st.sidebar.empty()
                st.success("You're Signed-In!")
                device_form = st.form(key="add-device-form")
                device_form.header('Add New Device:')

                device_id = device_form.text_input(label="Device ID", key='sub-signin-username')
                device_password = device_form.text_input(label="Device Password", type='password', key='sub-signin-password')
                device_btn = device_form.form_submit_button(label="Add Device", type='primary', use_container_width=True)

                if device_btn:
                    json_req = {"dev_id":device_id, "dev_password":device_password, "username":st.session_state['username']}
                    json_resp = requests.post(f"{self.serv_cat['address']}/add_device", json=json.dumps(json_req)).json()

                    if json_resp['status']=="Device Duplicate":
                        st.warning(f"Device in List")
                    elif json_resp['status']=="Device Registered Previously":
                        st.error(f"Device Registered Previously")
                    elif json_resp['status']=="Device Not Found":
                         st.error(f"Device Not Found, Check ID/Pass")
                    elif json_resp['status']=="Device Registered":
                         st.success(f"Device Succesfully Added")
                         st.session_state['devices'].append(device_id)

                VERTICAL_SPACE(4)
                sign_out_btn = st.button(label="Sign-Out", type='primary', key='sign-out', use_container_width=True)
                if sign_out_btn:
                    st.session_state['auth'] = None

            # Dashboard title
            st.title("Dashboard")
            st.subheader("Please Choose Your Device:")

            if len(st.session_state['devices']):
                sel_dev = st.selectbox(label="Device ID", options=list(st.session_state['devices']), key="sel-dev-id")
            else:
                st.warning("No Registered Devices Found")

            data_tab, report_tab, warning_tab = st.tabs(["Data", "Reports", "Warnings"])
            with data_tab:

                if len(st.session_state['devices']):

                    placeholder = st.empty()
                    data_live_colA, data_live_colB, data_live_colC, data_live_colD = st.columns([1,1,1,1])

                    with data_live_colB:
                        # Default Value is Set to 60 Second
                        live_time = st.text_input(label="Live Data Monitoring Time (s) :",
                                    key='time-enter-check', value=60,
                                    type='default', help="e.g. 60 = Monitor Patient for 60 Second")
                        
                    with data_live_colC:
                        # Default Value is Set to Each 0.5 Second
                        live_freq = st.text_input(label="Update Data Frequency (s) :",
                                    key='freq-enter-check', value=0.5,
                                    type='default', help="e.g. 1 = Get Data Each 1 Second")
                                
                    with st.columns([2,1,2])[1]:
                        live_btn_placeholder = st.empty()
                        with live_btn_placeholder:
                            live_btn = st.button(label="Get Live Data", key='live-data-btn', type='primary',
                                                disabled=not live_time and live_freq=="" and not st.session_state['live_data'], use_container_width=True)        
                    VERTICAL_SPACE(4) 
                    placeholder = st.empty()
                    if live_btn:
                        elasped_time = 0
                        try:
                            while elasped_time<int(live_time):
                                
                                st.session_state['live_data'] = True
                                json_live = requests.get(f"{self.mongodb_rest_address}/live_data",
                                                            params={'dev_id':sel_dev}).json()

                                with placeholder.container():

                                    # Create Three Columns
                                    met1, met2, met3, met4 = st.columns(4)
                                    # fill in those three columns with respective metrics or KPIs
                                    ox_sat_unit = "%"
                                    with met1:
                                        ox_colA, ox_colB, ox_colC = st.columns([1,3,1])
                                        with ox_colB:
                                            st.metric(
                                                label="Oxygen Saturation (SpO2) :",
                                                value=f"{json_live.get('oxygen', {}).get('measurements', [{}])[0].get('spo2', 'N/A')} {ox_sat_unit}",
                                            )
                                    bp_sat_unit = "mmHg"
                                    with met2:
                                        sys_colA, sys_colB, sys_colC = st.columns([1,3,1])
                                        with sys_colB:
                                            st.metric(
                                            label="Blood Pressure : (Systolic)",
                                            value=f"{json_live.get('pressure', {}).get('measurements', [{}])[0].get('systolic', 'N/A')} {bp_sat_unit}",
                                            )
                                    bp_sat_unit = "mmHg"
                                    with met3:
                                        dia_colA, dia_colB, dia_colC = st.columns([1,3,1])
                                        with dia_colB:
                                            st.metric(
                                            label="Blood Pressure : (Diastolic)",
                                            value=f"{json_live.get('pressure', {}).get('measurements', [{}])[0].get('diastolic', 'N/A')} {bp_sat_unit}",
                                            )
                                    hr_sat_unit = "BPM"
                                    with met4:
                                        hr_colA, hr_colB, hr_colC = st.columns([1,3,1])
                                        with hr_colB:
                                            st.metric(
                                            label="Heartrate : ",
                                            value=f"{json_live.get('ecg', {}).get('reports', [{}])[0].get('mean_freq', 'N/A')} {hr_sat_unit}",
                                            )
                                    heartrate_signal = pd.DataFrame(json_live.get('ecg', {}).get('measurements', [{}])[0].get('ecg_seg', 'N/A'),
                                                                    columns=["Heartrate Signal"])
                                    heartrate_signal.index.name = "Sample"
                                    st.line_chart(heartrate_signal)
                                    time.sleep(float(live_freq))
                                    elasped_time+=float(live_freq)
                        except:
                            st.error("Error Occured During Live Monitoring Please Try Again!")

                        st.session_state['live_data'] = False
                        st.warning("Monitoring Time Finished")
                else:
                    st.warning("Monitoring is not possible / No Registered Devices Found")

            with report_tab:
                if len(st.session_state['devices']):
                    sel_report = st.selectbox(label="Report Type :", options=["Oxygen", "Pressure", "ECG"], key=f"sel-report-id-{sel_dev}")
                    json_report = requests.get(f"{self.mongodb_rest_address}/get_report",
                                                params={'report_type':sel_report.lower(), 'dev_id':sel_dev}).json()
                    if sel_report=="Oxygen":
                        try:
                            ox_df = pd.DataFrame(json_report['oxygen']['reports'])
                            ox_df = ox_df[['timestamp', 'max_spo2', 'min_spo2', 'mean_spo2']].rename(columns={
                                                        'max_spo2': 'Max SpO2 (%)',
                                                        'min_spo2': 'Min SpO2 (%)',
                                                        'mean_spo2': 'Mean SpO2 (%)',
                                                        'timestamp':'Report Time'
                                                    })
                            ox_df['Report Time'] = pd.to_datetime(ox_df['Report Time'], unit='s')
                            ox_df.set_index('Report Time', inplace=True)
                            st.dataframe(data=ox_df, use_container_width=True)
                            
                        except:
                            st.warning("No Recorded Report") 

                    elif sel_report=="Pressure":
                        try:
                            pressure_df = pd.DataFrame(json_report['pressure']['reports'])
                            pressure_df = pressure_df[['timestamp', 'max_diastolic', 'min_diastolic',
                                                    'mean_diastolic', 'max_systolic', 'min_systolic', 'mean_systolic']].rename(columns={
                                                        'max_diastolic': 'Max Diastolic (mmHg)',
                                                        'min_diastolic': 'Min Diastolic (mmHg)',
                                                        'mean_diastolic': 'Mean Diastolic (mmHg)',
                                                        'max_systolic': 'Max Systolic (mmHg)',
                                                        'min_systolic': 'Min Systolic (mmHg)',
                                                        'mean_systolic': 'Mean Systolic (mmHg)',
                                                        'timestamp':'Report Time'
                                                    })
                            
                            pressure_df['Report Time'] = pd.to_datetime(pressure_df['Report Time'], unit='s')
                            pressure_df.set_index('Report Time', inplace=True)
                            
                            st.dataframe(data=pressure_df, use_container_width=True)
                            
                        except:
                            st.warning("No Recorded Report")

                    elif sel_report=="ECG":
                        try:
                            ecg_df = pd.DataFrame(json_report['ecg']['reports'])
                            ecg_df = ecg_df[['timestamp', 'mean_freq', 'max_freq', 'min_freq',
                                             'mean_rr', 'max_rr', 'min_rr', 'std_rr']].rename(columns={
                                                        'mean_freq': 'Mean Heartbeat (BPM)',
                                                        'max_freq': 'Max Heartbeat (BPM)',
                                                        'min_freq': 'Min Diastolic (BPM)',
                                                        'mean_rr': 'Mean R-R',
                                                        'max_rr': 'Max R-R',
                                                        'min_rr': 'Min R-R',
                                                        'std_rr': 'STD R-R',
                                                        'timestamp': 'Report Time',
                                                    })
                            
                            ecg_df['Report Time'] = pd.to_datetime(ecg_df['Report Time'], unit='s')
                            ecg_df.set_index('Report Time', inplace=True)
                            
                            st.dataframe(data=ecg_df, use_container_width=True)
                            
                        except:
                            st.warning("No Recorded Report") 
                else:
                    st.warning("Reports are not available / No Registered Devices Found")

            with warning_tab:
                if len(st.session_state['devices']):
                    sel_warning = st.selectbox(label="Warning Type :", options=["Oxygen", "Pressure", "ECG"], key=f"sel-warning-id-{sel_dev}")
                    json_warning = requests.get(f"{self.mongodb_rest_address}/get_warning",
                                                params={'warning_type':sel_warning.lower(), 'dev_id':sel_dev}).json()
                    if sel_warning=="Oxygen":
                        try:              
                            ox_warn_df = pd.DataFrame(json_warning['oxygen']['warnings'])
                            ox_warn_df = ox_warn_df[['timestamp',
                                                    'warning',
                                                    'value']]
                            
                            ox_warn_df = ox_warn_df.rename(columns={
                                                        'warning': 'Warning Message',
                                                        'value': 'Reported Value (%)',
                                                        'timestamp':'Warning Time'
                                                    })
                            
                            ox_warn_df['Warning Time'] = pd.to_datetime(ox_warn_df['Warning Time'], unit='s')
                            ox_warn_df.set_index('Warning Time', inplace=True)

                            st.dataframe(data=ox_warn_df, use_container_width=True)
                            
                        except:
                            st.warning("No Recorded Warning") 

                    elif sel_warning=="Pressure":
                        try:                    
                            pressure_warn_df = pd.DataFrame(json_warning['pressure']['warnings'])
                            pressure_warn_df = pressure_warn_df[['timestamp',
                                                    'warning',
                                                    'value']]
                            
                            pressure_warn_df = pressure_warn_df.rename(columns={
                                                        'warning': 'Warning Message',
                                                        'value': 'Reported Value (mmHg)',
                                                        'timestamp':'Warning Time'
                                                    })
                            
                            pressure_warn_df['Warning Time'] = pd.to_datetime(pressure_warn_df['Warning Time'], unit='s')
                            pressure_warn_df.set_index('Warning Time', inplace=True)

                            st.dataframe(data=pressure_warn_df, use_container_width=True)
                            
                        except:
                            st.warning("No Recorded Warning") 

                    elif sel_warning=="ECG":
                        try:
                            ecg_warns = json_warning['ecg']['warnings']
                            ecg_warns_flt = []
                            for data in ecg_warns:
                                data.update(data.pop('value'))
                                ecg_warns_flt.append(data)

                            ecg_warn_df = pd.DataFrame(ecg_warns_flt)
                            ecg_warn_df = ecg_warn_df[['timestamp',
                                                        'warning',
                                                        'mean_freq',
                                                        'max_freq',
                                                        'min_freq',
                                                        'mean_rr',
                                                        'max_rr',
                                                        'min_rr',
                                                        'std_rr',
                                                        'envelope']]
                            
                            ecg_warn_df = ecg_warn_df.rename(columns={
                                                        'warning': 'Warning Message',
                                                        'mean_freq': 'Reported Mean Heartbeat (BPM)',
                                                        'max_freq': 'Reported Max Heartbeat (BPM)',
                                                        'min_freq': 'Reported Min Diastolic (BPM)',
                                                        'mean_rr': 'Reported Mean R-R',
                                                        'max_rr': 'Reported Max R-R',
                                                        'min_rr': 'Reported Min R-R',
                                                        'std_rr': 'Reported STD R-R',
                                                        'timestamp': 'Warning Time',
                                                    })
                            
                            ecg_warn_df['Warning Time'] = pd.to_datetime(ecg_warn_df['Warning Time'], unit='s')

                            ecg_warn_df_show = ecg_warn_df.copy()
                            ecg_warn_df_show = ecg_warn_df_show.drop(columns=['envelope'])
                            ecg_warn_df.set_index('Warning Time', inplace=True)
                            ecg_warn_df_show.set_index('Warning Time', inplace=True)
                            st.dataframe(data=ecg_warn_df_show, use_container_width=True)
                            sel_warn_time = st.selectbox(label="Choose Warning Time", options=ecg_warn_df_show.index)

                            try:
                                heartrate_signal = pd.DataFrame(ecg_warn_df.iloc[ecg_warn_df_show.index.get_loc(sel_warn_time)]['envelope'], columns=["envelope"])
                                st.line_chart(heartrate_signal)
                            except:
                                st.error("Error with Loading Envelope")
                    
                        except:
                            st.warning("No Recorded Warning")  

                else:
                    st.warning("Warnings are not available / No Registered Devices Found")
                
        else:
            if st.session_state['auth']==False:
                with st.sidebar:
                    st.error("Username/Password is Wrong!")

    def run(self):

        self.start()
        self.set_app_config()
        self.init_session_states()
        self.run_app_navigation()

if __name__ == "__main__":

    sicu_web_app = SICU_WEB()
    sicu_web_app.run()
    sicu_web_app_thread = threading.Thread(target=sicu_web_app.update_service_status)
    sicu_web_app_thread.daemon = True
    sicu_web_app_thread.start()
      
