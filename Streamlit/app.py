import streamlit as st
from streamlit_extras.add_vertical_space import add_vertical_space as VERTICAL_SPACE
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import altair as alt
import plotly.express as px # Interactive Chart
import time
import toml
from PIL import Image, ImageFilter
from pymongo import MongoClient, DESCENDING

class SICU_WEB:	

    def __init__(self):
        
        self.app_title = "SICU"
        self.app_layout = "wide"
        self.app_sidebar_init_state = "expanded"
        self.app_logo_path = 'sicu_logo.png'

        self.mongo_url = 'localhost'
        self.mongo_port = 27017

        self.streamlit_url = 'localhost'
        self.streamlit_port = 8501
            
    def _setPageConfig(self):
        
        # Set Page Configurations

        # Load the  config.toml File
        with open('.streamlit/config.toml', 'r') as file:
            config = toml.load(file)

        # Set Streamlit URL and Port
        config['server']['port'] = self.streamlit_port
        config['browser']['serverAddress'] = self.streamlit_url
        config['browser']['serverPort'] = self.streamlit_port


        # Save the config.toml File
        with open('.streamlit/config.toml', 'w') as file:
            toml.dump(config, file)

        # Set Page Configurations
        st.set_page_config(page_title=self.app_title,
                           layout=self.app_layout,
                           initial_sidebar_state=self.app_sidebar_init_state,
                           page_icon=Image.open(self.app_logo_path))
        
    def _connectMongoDB(self):

        # MongoDB Connection
        self.mongo_client = MongoClient(self.mongo_url, self.mongo_port)
        self.db = self.mongo_client['sicu']
        self.measurements_collection = self.db['measurements']
        self.reports_collection = self.db['reports']
        self.warnings_collection = self.db['warnings']

    def _setSessionState(self):

        # Initial Session State Variables

        # Live Data Session State
        if 'live_data' not in st.session_state:
            st.session_state['live_data'] = False

        # Authentication Session State
        if 'auth' not in st.session_state:
            st.session_state['auth'] = None

        if 'username' not in st.session_state:
            st.session_state['username'] = None

        if 'password' not in st.session_state:
            st.session_state['password'] = None

        if 'patients' not in st.session_state:
            st.session_state['patients'] = None

    def _hideHeaderFooter(self):

        hide_streamlit_style = """
                    <style>
                    #MainMenu {visibility: hidden;}
                    footer {visibility: hidden;}
                    header {visibility: hidden;}
                    </style>
                    """
        
        st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    def _appFuncs(self):

        auth_placeholder = st.sidebar.empty()

        if st.session_state['auth']==None or st.session_state['auth']==False:

            with auth_placeholder:

                logo_sidebar = Image.open("sicu_sidebar.png")
                logo_sidebar.thumbnail((1000, 1000), Image.BICUBIC)
                logo_sidebar = logo_sidebar.filter(ImageFilter.SHARPEN)
                with st.sidebar.columns([1,1,1])[1]:
                    st.sidebar.image(logo_sidebar)

                with st.sidebar:

                    VERTICAL_SPACE(2)

                    signin_form = st.form(key="signin-btn")
                    signin_form.header('Sign-in to Dashboard:')

                    entered_username = signin_form.text_input(label="Username",
                                                              key='sub-signin-username-btn')
                    
                    entered_password = signin_form.text_input(label="Password",
                                                              type='password',
                                                              key='sub-signin-password-btn')
                    
                    login_btn = signin_form.form_submit_button(label="Sign-in",
                                                               type='primary',
                                                               use_container_width=True)
                    if login_btn:

                        st.session_state['auth'] = True
                        st.session_state['patients'] ['P-300', 'P-AB-400']

        else:
            with auth_placeholder:
                st.sidebar.empty()

        # Check the Authentication Status
        if st.session_state['auth']:

            with st.sidebar:
                st.success("Signed-in Succefully!")

            # Dashboard title
            st.title("Dashboard")

            st.subheader("Please Choose Your Patient:")

            sel_patient = st.selectbox(label="Patient ID", options=["P300", "P400"], key="sel-patient-id")

            data_tab, report_tab, warning_tab = st.tabs(["Data", "Reports", "Warnings"])

            with data_tab:

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
                
                    while elasped_time<int(live_time):

                        st.session_state['live_data'] = True

                        try:
                            ox_measurements = list(self.measurements_collection.find({"sens_cat": "oxygen", "user_id": sel_patient},
                                                                                sort=[("_id", DESCENDING)]))
                            ox_val = ox_measurements[0]['spo2']
                            if len(ox_measurements)>1:
                                ox_prev = ox_measurements[1]['spo2']
                            else:
                                ox_prev = ox_measurements[0]['spo2']
                        except:
                            ox_val = "N/A"
                            ox_prev = "N/A"
                            
                        try:
                            pressure_measurements = list(self.measurements_collection.find({"sens_cat": "pressure", "user_id": sel_patient},
                                                                                    sort=[("_id", DESCENDING)]))
                            sys_val = pressure_measurements[0]['systolic']
                            dias_val = pressure_measurements[0]['diastolic']

                            if len(pressure_measurements)>1:
                                sys_val_prev = pressure_measurements[1]['systolic']
                                dias_val_prev = pressure_measurements[1]['diastolic']
                            else:
                                sys_val_prev = pressure_measurements[0]['systolic']
                                dias_val_prev = pressure_measurements[0]['diastolic']                    

                        except:
                            sys_val = "N/A"
                            dias_val = "N/A"
                            sys_val_prev = "N/A"
                            dias_val_prev = "N/A"

                        try:
                            heartrate_measurements = list(self.measurements_collection.find({"sens_cat": "ecg", "user_id": sel_patient},
                                                                                        sort=[("_id", DESCENDING)]))
                            heartrate_reps = list(self.reports_collection.find({"sens_cat": "ecg", "user_id": sel_patient},
                                                                        sort=[("_id", DESCENDING)]))
                            heartrate_seg = heartrate_measurements[0]['ecg_seg']
                            heartrate_val = heartrate_reps[0]['mean_freq']
                            if len(heartrate_reps)>1:
                                heartrate_val_prev = heartrate_reps[1]['mean_freq']
                            else:
                                heartrate_val_prev = heartrate_reps[0]['mean_freq']
                        except:
                            heartrate_val = "N/A"
                            heartrate_val_prev = "N/A"

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
                                        value=f"{ox_val} {ox_sat_unit}",
                                    )
                            
                            bp_sat_unit = "mmHg"
                            with met2:
                                sys_colA, sys_colB, sys_colC = st.columns([1,3,1])
                                with sys_colB:
                                    st.metric(
                                    label="Blood Pressure : (Systolic)",
                                    value=f"{sys_val} {bp_sat_unit}",
                                    )

                            bp_sat_unit = "mmHg"
                            with met3:
                                dia_colA, dia_colB, dia_colC = st.columns([1,3,1])
                                with dia_colB:
                                    st.metric(
                                    label="Blood Pressure : (Diastolic)",
                                    value=f"{dias_val} {bp_sat_unit}",
                                    )

                            hr_sat_unit = "BPM"
                            with met4:
                                hr_colA, hr_colB, hr_colC = st.columns([1,3,1])
                                with hr_colB:
                                    st.metric(
                                    label="Heartrate : ",
                                    value=f"{heartrate_val} {hr_sat_unit}",
                                    )

                            heartrate_signal = pd.DataFrame(heartrate_seg, columns=["Heartrate Signal"])
                            heartrate_signal.index.name = "Sample"

                            st.line_chart(heartrate_signal)

                            time.sleep(float(live_freq))

                            elasped_time+=float(live_freq)

                    st.session_state['live_data'] = False

                    st.warning("Monitoring Time Finished")

            with report_tab:

                sel_report = st.selectbox(label="Report Type :", options=["Oxygen", "Pressure", "ECG"], key=f"sel-report-id-{sel_patient}")

                if sel_report=="Oxygen":

                    try:

                        ox_reps = list(self.reports_collection.find({"sens_cat": "oxygen", "user_id": sel_patient},
                                                                            sort=[("_id", DESCENDING)]))
                        
                        ox_df = pd.DataFrame(ox_reps)
                        ox_df = ox_df[['timestamp',
                                                'max_spo2',
                                                'min_spo2',
                                                'mean_spo2']]
                        
                        ox_df = ox_df.rename(columns={
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

                        pressure_reps = list(self.reports_collection.find({"sens_cat": "pressure", "user_id": sel_patient},
                                                                            sort=[("_id", DESCENDING)]))
                        
                        pressure_df = pd.DataFrame(pressure_reps)
                        pressure_df = pressure_df[['timestamp',
                                                'max_diastolic',
                                                'min_diastolic',
                                                'mean_diastolic',
                                                'max_systolic',
                                                'min_systolic',
                                                'mean_systolic']]
                        
                        pressure_df = pressure_df.rename(columns={
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

                        ecg_reps = list(self.reports_collection.find({"sens_cat": "ecg", "user_id": sel_patient},
                                                                            sort=[("_id", DESCENDING)]))
                        
                        ecg_df = pd.DataFrame(ecg_reps)
                        ecg_df = ecg_df[['timestamp',
                                                'mean_freq',
                                                'max_freq',
                                                'min_freq',
                                                'mean_rr',
                                                'max_rr',
                                                'min_rr',
                                                'std_rr']]
                        
                        ecg_df = ecg_df.rename(columns={
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

            with warning_tab:

                sel_warning = st.selectbox(label="Warning Type :", options=["Oxygen", "Pressure", "ECG"], key=f"sel-warning-id-{sel_patient}")

                if sel_warning=="Oxygen":

                    try:

                        ox_warns = list(self.warnings_collection.find({"sens_cat": "oxygen", "user_id": sel_patient},
                                                                            sort=[("_id", DESCENDING)]))
                        
                        ox_warn_df = pd.DataFrame(ox_warns)
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

                        pressure_warns = list(self.warnings_collection.find({"sens_cat": "pressure", "user_id": sel_patient},
                                                                            sort=[("_id", DESCENDING)]))
                        
                        pressure_warn_df = pd.DataFrame(pressure_warns)
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

                        ecg_warns = list(self.warnings_collection.find({"sens_cat": "ecg", "user_id": sel_patient},
                                                                            sort=[("_id", DESCENDING)]))
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

            if st.session_state['auth']==False:
                with st.sidebar:
                    st.error("Username/Password is Wrong!")

    def run(self):

        # Page Config and MongoDB Service Connection
        self._setPageConfig()
        self._connectMongoDB()
        self._setSessionState()
        self._hideHeaderFooter()
        self._appFuncs()

if __name__ == "__main__":

    sicu_web_interface = SICU_WEB()
    sicu_web_interface.run()
