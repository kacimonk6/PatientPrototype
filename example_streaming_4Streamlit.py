import streamlit as st 
import USB_ExampleClassStreamlit
from ThreeSpaceAPIStreamlit import *
from time import time_ns, sleep
import sys
import csv
import os
import keyboard  # Import the keyboard library
import re
import winsound


from colorama import init, Fore, Style
init(autoreset=True)  # Initialize colorama to auto-reset colors after each print statement

# Initialize constants and globals
MICROSECONDS_IN_A_SECOND = 1000000
NANOSECONDS_IN_A_SECOND = 1000000000
PORT = None  # Autodetect the port, modify if necessary
TIMEOUT = 0.7
LOGICAL_IDS = [0, 1]  # Assuming two sensors
DESIRED_SAMPLES_PER_SECOND = 100

# Initialize control variables
recording = False  # State variable to track recording status
files_open = False  # Tracks if the files are open
csvfile_0 = None
csvfile_1 = None
writer_0 = None
writer_1 = None
iteration = 0

# CONSTANTS / GLOBALS
MICROSECONDS_IN_A_SECOND = 1000000  # 1 million, 6 zeros
us = MICROSECONDS_IN_A_SECOND
NANOSECONDS_IN_A_SECOND = 1000000000  # 1 billion, 9 zeros
ns = NANOSECONDS_IN_A_SECOND

PORT = None  # we will try to autodetect the port
# change/comment out if needed
# PORT = '/dev/ttyACM0'  # pi
# PORT = "COM26"  # windows

LOGICAL_IDS = [0,1]

# change if needed. raise if there are data transfer problems
TIMEOUT = 0.7

# change if needed. 0 should be fine. using 1 as an example.
START_STREAM_DELAY_IN_SECONDS = 1

# change if needed
TIME_TO_WAIT_BEFORE_GIVING_UP = 5

# change if needed
DESIRED_SAMPLES_PER_SECOND = 100
hz = DESIRED_SAMPLES_PER_SECOND



print(Fore.CYAN + "Getting com class")
senCom = USB_ExampleClassStreamlit.UsbCom(PORT, timeout=TIMEOUT)
print(Fore.CYAN + "Getting tss class (if you hang here, double check your COM port)")
senTSS = None
try:
    senTSS = ThreeSpaceSensor(senCom, streamingBufferLen=1000)
except:
    print(Fore.YELLOW + "Resetting dongle/sensor, please wait about 10 seconds.")
    print(Fore.YELLOW + "If the program hangs, power cycle your dongle / sensors and restart the program.")
    senCom.write(":226\n".encode('latin'),None)  # resets dongle/sensor
    success = False
    while not success:
        try:
            senTSS = ThreeSpaceSensor(senCom, streamingBufferLen=1000)
            success = True
            for id in LOGICAL_IDS:
                sleep(0)
                senTSS.stopStreaming(logicalID=id)
        except:
            sleep(1)
sleep(0)
senTSS.comClass.sensor.reset_input_buffer()


print("Taring sensors")
for id in LOGICAL_IDS:
    senTSS.tareWithCurrentOrientation(logicalID=id)

print("Setting streaming slots")
for id in LOGICAL_IDS:
    senTSS.setStreamingSlots(Streamable.READ_TARED_ORIENTATION_AS_EULER, 
                             Streamable.READ_TARED_ORIENTATION_AS_QUAT, logicalID=id)
print("Setting response header bitfield")
# headerConfig=0x1+0x2+0x4+0x8+0x10+0x20+0x40
# senTSS.setResponseHeaderBitfield(headerConfig=0x1+0x2+0x4+0x8+0x10+0x20+0x40)
#senTSS.setResponseHeaderBitfield(headerConfig=0x1+0x2+0x4)

print("Setting streaming timing")
interval = 0
if hz != 0:
    interval = round(float(us)/hz)
for id in LOGICAL_IDS:
    senTSS.setStreamingTiming(
        interval=interval,
        duration=STREAM_CONTINUOUSLY,  # 0xFFFFFFFF
        delay=START_STREAM_DELAY_IN_SECONDS*us,
        logicalID=id
    )

# additional setup
packets = {}
for id in LOGICAL_IDS:
    packets[id] = []


print(Fore.GREEN + "Starting stream...")
for id in LOGICAL_IDS:
    senTSS.startStreaming(logicalID=id)

eepy = 0.9/(float(hz)*len(LOGICAL_IDS))
eepy = 0

sleep(3)
for i in range(10):
    for id in LOGICAL_IDS:
        senTSS.getOldestStreamingPacket(logicalID=id)
    sleep(eepy)
sleep(3)
    
start_time = time_ns()
# Function definitions


def find_next_iteration_number():
    # Pattern to match the files, assuming they are named like 'IMU00_Duration_Collection_01.csv'
    pattern = re.compile(r'IMU\d{2}_Duration_Collection_(\d{2})\.csv')
    highest_iteration = 0

    # List all files in the current directory
    for filename in os.listdir('.'):
        match = pattern.match(filename)
        if match:
            # Extract iteration number from filename and convert to int
            iteration_number = int(match.group(1))
            if iteration_number > highest_iteration:
                highest_iteration = iteration_number

    # Return the next iteration number
    return highest_iteration + 1


def start_recording():
    global recording, csvfile_0, csvfile_1, writer_0, writer_1, iteration
    # Only start recording if not already recording
    if not recording:
        winsound.Beep(400, 50) # Beep at 400 Hz for 50 milliseconds
        winsound.Beep(800, 70) # Beep at 800 Hz for 70 milliseconds

        recording = True
        # Find next iteration number
        iteration = find_next_iteration_number()
        # Open new CSV files for writing
        csvfile_0 = open(f'IMU00_Duration_Collection_{iteration:02d}.csv', 'w', newline='')
        csvfile_1 = open(f'IMU01_Duration_Collection_{iteration:02d}.csv', 'w', newline='')
        # Create new CSV writers
        writer_0 = csv.writer(csvfile_0)
        writer_1 = csv.writer(csvfile_1)
        print(Fore.CYAN + f"Recording started: Session {iteration}")

def stop_recording():
    global recording, csvfile_0, csvfile_1, writer_0, writer_1
    # Only stop recording if currently recording
    if recording:
        winsound.Beep(700, 50) # Beep at 700 Hz for 50 milliseconds
        winsound.Beep(300, 70) # Beep at 300 Hz for 70 milliseconds
        recording = False
        # Close the files if they are open
        if csvfile_0 is not None:
            csvfile_0.close()
            csvfile_0 = None  # Reset file object to None
        if csvfile_1 is not None:
            csvfile_1.close()
            csvfile_1 = None  # Reset file object to None
        # Reset writers to None
        writer_0 = None
        writer_1 = None
        print(Fore.RED + "Recording stopped")


def record_data():
    for id in LOGICAL_IDS:
        packet = senTSS.getOldestStreamingPacket(logicalID=id)
        if packet is not None and writer_0 is not None and writer_1 is not None:
            if id == 0:
                writer_0.writerow(packet)
            elif id == 1:
                writer_1.writerow(packet)

# Keyboard hooks
keyboard.add_hotkey('s', start_recording)
keyboard.add_hotkey('e', stop_recording)

# Main loop
try:
    print(Fore.MAGENTA + "Press 's' to start recording, 'e' to stop. Ctrl+C to exit.")
    winsound.Beep(200, 200)  # Beep at 200 Hz for 200 milliseconds
    while True:
        if recording:
            record_data()
        sleep(eepy)  # Adjust as needed to manage CPU usage
except KeyboardInterrupt:
    print(Fore.BLUE + "\nProgram terminated by user.")
finally:
    winsound.Beep(900, 50) # Beep at 900 Hz for 50 milliseconds
    winsound.Beep(500, 70) # Beep at 500 Hz for 70 milliseconds
    # Cleanup
    if csvfile_0 is not None:
        csvfile_0.close()
    if csvfile_1 is not None:
        csvfile_1.close()
    print("Cleaned up files.")
    print("Stopping stream")
    for id in LOGICAL_IDS:
        senTSS.stopStreaming(logicalID=id)
    print(Fore.YELLOW + "Closed Stream! Goodbye!")
    winsound.Beep(600, 50) # Beep at 600 Hz for 50 milliseconds
    winsound.Beep(400, 70) # Beep at 200 Hz for 70 milliseconds
