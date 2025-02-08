import USB_ExampleClassStreamlit

from ThreeSpaceAPIStreamlit import *
from time import sleep
import csv
import os
#import winsound
from colorama import init, Fore, Style
import streamlit as st
import re
import time

init(autoreset=True)  # Initialize colorama to auto-reset colors after each print statement

# Streamlit app header and instructions
st.markdown("<h1 style = 'text-align: center; color: #001e69;'>Welcome to the LETREP25 Project!</h1>", unsafe_allow_html=True)
st.subheader("Please login with your username and password below")
st.markdown("")

# Simulate authentication
def authenticate(username, password):
    return username == "letrep" and password == "letrep123"

# Create input fields for username and password
username = st.text_input("Username")
password = st.text_input("Password", type="password")

# Initialize session state for logged_in
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Initialize session state for data collection active state
if 'data_collection_active' not in st.session_state:
    st.session_state.data_collection_active = False

# Initialize session state for data recording variables
if 'recording' not in st.session_state:
    st.session_state.recording = False

# Initialize session state for CSV file writers
if 'csvfile_0' not in st.session_state:
    st.session_state.csvfile_0 = None
if 'csvfile_1' not in st.session_state:
    st.session_state.csvfile_1 = None
if 'writer_0' not in st.session_state:
    st.session_state.writer_0 = None
if 'writer_1' not in st.session_state:
    st.session_state.writer_1 = None

# Create a button to trigger the authentication process
if st.button("Login"):
    if authenticate(username, password):
        st.session_state.logged_in = True
        st.success("Logged in successfully!")
    else:
        st.session_state.logged_in = False
        st.error("Invalid username or password")

# Initialize constants and globals
MICROSECONDS_IN_A_SECOND = 1000000
PORT = None  # Autodetect the port, modify if necessary
TIMEOUT = 0.7
LOGICAL_IDS = [0, 1]  # Assuming two sensors
DESIRED_SAMPLES_PER_SECOND = 100

# Function to find the next iteration number for saving CSV files
def find_next_iteration_number():
    pattern = re.compile(r'IMU\d{2}_Duration_Collection_(\d{2})\.csv')
    highest_iteration = 0

    for filename in os.listdir('.'):
        match = pattern.match(filename)
        if match:
            iteration_number = int(match.group(1))
            if iteration_number > highest_iteration:
                highest_iteration = iteration_number

    return highest_iteration + 1

# Function to start recording
def start_recording(patient_name, date):
    iteration = find_next_iteration_number()
    fileName = str(patient_name + date)

    # Open new CSV files for writing
    st.session_state.csvfile_0 = open(f'IMU00_{fileName}.csv', 'w', newline='')
    st.session_state.csvfile_1 = open(f'IMU01_{fileName}.csv', 'w', newline='')

    # Create new CSV writers
    st.session_state.writer_0 = csv.writer(st.session_state.csvfile_0)
    st.session_state.writer_1 = csv.writer(st.session_state.csvfile_1)
    st.session_state.recording = True

    #winsound.Beep(400, 50)  # Beep at 400 Hz for 50 milliseconds
    #winsound.Beep(800, 70)  # Beep at 800 Hz for 70 milliseconds

    #st.write(Fore.CYAN + f"Recording started: Session {iteration}")
    #st.write("Recording started")
    st.session_state.data_collection_active = True
    return iteration

# Function to stop recording
def stop_recording():
    #winsound.Beep(700, 50)  # Beep at 700 Hz for 50 milliseconds
    #winsound.Beep(300, 70)  # Beep at 300 Hz for 70 milliseconds

    if st.session_state.csvfile_0:
        st.session_state.csvfile_0.close()
    if st.session_state.csvfile_1:
        st.session_state.csvfile_1.close()

    st.session_state.recording = False
    st.session_state.writer_0 = None
    st.session_state.writer_1 = None
    st.session_state.csvfile_0 = None
    st.session_state.csvfile_1 = None
    st.session_state.data_collection_active = False

    #st.write(Fore.RED + "Recording stopped")
    #st.write("Recording stopped")

# Function to record data
def record_data(senTSS):
    for id in LOGICAL_IDS:
        packet = senTSS.getOldestStreamingPacket(logicalID=id)
        if packet is not None:
            if id == 0 and st.session_state.writer_0 is not None:
                st.session_state.writer_0.writerow(packet)
            elif id == 1 and st.session_state.writer_1 is not None:
                st.session_state.writer_1.writerow(packet)

# Streamlit login logic
if st.session_state.logged_in:
    st.write("Welcome, you are logged in!")
    st.text("")

    st.write("Please enter the required fields below.")
    patient_name = st.text_input("Please enter your name:")
    date = st.text_input("Please enter the date (e.g., 11_7_24):")

    # Display an alert if patient name or date is not provided
    if not patient_name or not date:
        st.warning("Please fill in both 'Name' and 'Date' before starting data collection.")

    st.text("")
    st.subheader("Click the button below to toggle data collection")

    # Toggle button to start/stop data collection
    toggle_button_label = "Start Data Collection" if not st.session_state.data_collection_active else "Stop Data Collection"
    
    if st.button(toggle_button_label):
        if not st.session_state.data_collection_active:
            # Start the data collection
            if patient_name and date:
                iteration = start_recording(patient_name, date)
                #st.success("Data collection has successfully begun.")
                
                # Setup for the sensor
                senCom = USB_ExampleClassStreamlit.UsbCom(PORT, timeout=TIMEOUT)
                senTSS = None

                try:
                    st.write("Initializing sensor...")
                    senTSS = ThreeSpaceSensor(senCom, streamingBufferLen=1000)
                    st.write("Sensor initialized successfully")
                    st.success("Recording started. Data collection has successfully begun.")
                except Exception as e:
                    st.error(f"Error initializing sensor: {str(e)}")
                    st.error("Make sure the sensor is connected to the correct COM port.")
                    st.error("If the sensor is powered off, turn it on and try again.")

                if senTSS:
                    senTSS.comClass.sensor.reset_input_buffer()
                    for id in LOGICAL_IDS:
                        senTSS.startStreaming(logicalID=id)

                    # Collect data in the background
                    while st.session_state.data_collection_active:
                        record_data(senTSS)
                        sleep(0.01)  # Adjust this based on your desired sample rate
        else:
            # Stop the data collection
            stop_recording()
            st.success("Recording stopped. Data collection has successfully ended. Thank you!")
