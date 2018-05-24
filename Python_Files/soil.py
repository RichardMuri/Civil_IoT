#!/usr/bin/python3
import sys
import time
import signal # catch SIGTERM
import datetime as dt	# used for recording date and time
import queue	# queue data structure for recording keyboard events

import RPi.GPIO as GPIO	# GPIO control
from scale import Scale # HX711 sense amplifier package
import keyboard	# Key logging package

# import requests	# REST package
# import json

# Authenticate to database
# login_payload = {'device_info': {'app-id': 'fc', 'os-type': 'os'}}
# authentication = (login, password)  
# url = 'http://example.com/login'
# response = requests.post(url, data=login_payload, auth=authentication)

# Class for controlling sense amplifier
scale = Scale()

# HOW TO CALCULATE THE REFERENCE UNIT
#########################################
# To set the reference unit to 1.
# Call get_weight before and after putting 1000g weight on your sensor.
# Divide difference with grams (1000g) and use it as reference unit.
scale.setReferenceUnit(1)
scale.tare()
scale.reset()

# GPIO control setup
GPIO.setmode(GPIO.BCM) # Use BCM numbering
GPIO.setwarnings(False) # Disables warning pins may be in use

dial_read = 3 # Pin used to trigger reads from dial indicator
dial_power = 2 # Pin used to power 

GPIO.setup([dial_read, dial_power], GPIO.OUT, initial=GPIO.LOW) 
time.sleep(3) # wait long enough to discharge dial indicator, ensure it's off
GPIO.output(dial_power, True) # turn dial indicator back on

# Global variables
start_time = dt.datetime.now() # Date and time the experiment starts
events = queue.Queue() # Queue to hold keyboard events

if len(sys.argv) > 1: # Experiment id is provided as an argument
	experiment_id = str(sys.argv[1])
else: # Else, use today's date as the experiment id 
	experiment_id = start_time.strftime("%m-%d-%y")

displacement = []
weight = [] # weight on the weight rack
elapsed_time = [] # total experiment elapsed time in seconds	
Active = True # boolean to determine when to stop recording

# Function definitions
def handle_event(event):
	''' 
		Callback function that records keyboard events into global
		queue. Non-blocking record of any keyboard event.
	'''
	global events
	events.put(event)

def read_dial_indicator():
	'''
		This function works by logging keyboard input from the USB keyboard 
		plugged into the Pi. The dial indicator spoofs a Dell keyboard; it 
		outputs numbers in the format "0.00\n". The reading is in mm.
		
		Connects blue wire from keyboard reader to ground. Triggers
		dial indicator to type the current reading followed by the 
		enter key. When a reading is triggered, the handle_event callback
		will record the keyboard event
		
		Must go from no connection (False) to connected (True) for 
		approximately 0.5 seconds and back in order to trigger a 
		read. Done twice just in case, this function is fast enough
		only one read is ever triggered
	'''
	#print("Initiating read")
	i = 0
	while i < 2:
		GPIO.output(dial_read, True)
		time.sleep(.5)
		GPIO.output(dial_read, False)
		i += 1

def generator():
	'''
		As keyboard events arrive in the queue, remove them from the
		queue in order to be read by keyboard.get_typed_strings
	'''
	global events
	while True:
		yield events.get()

def format_entry(displacement, weight, elapsed_time):
	'''
		Format data into a json string for posting to the database
	'''
	global experiment_id
	
	return str.format("experiment_id: {0}, displacement: {1}, weight: {2}, time: {3}", experiment_id, displacement, weight, elapsed_time)
	
def signal_handler(signal, frame):
	'''
		Catch signals and exit gracefully
	'''
	exitmsg = str.format("Exiting because of signal")
	print(exitmsg)
	f.write(exitmsg)
	cleanup()

def cleanup():
	'''
		Close files and GPIO objects before exit
	'''
	global f
	GPIO.cleanup()
	f.close()
	sys.exit()

# Catch and gracefully handle signals
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)
	
print("Starting soil consolidation experiment with id " + experiment_id)
f = open(experiment_id + ".log", 'w') # open a file in write mode

keyboard.hook(handle_event) # set call back for keyboard event arrival	
nums = keyboard.get_typed_strings(generator()) # generator for keyboard strings
timer = time.time() # timer for the main control loop
offset = 0 # initial offset is 0
weight = scale.getWeight() # initial reading, check every 4 minutes
scale.powerDown()
# Main control loop
while Active:
	try:
		# This if statement prevents dial indicator from timing itself out
		# by power cycling it. Not an exact measurement, subject to drift
		# but good enough for our purpose
		if(time.time() - timer >= 240): # More than four minutes passed
			print("Resetting dial indicator to prevent timeout")
			offset = reading # preserve previous reading through reset
			GPIO.output(dial_power, False) # turn off dial indicator
			time.sleep(3) # wait long enough to discharge dial indicator, ensure it's off
			GPIO.output(dial_power, True) # turn dial indicator back on
			timer = time.time() # reset timer
			
			# Get new scale reading, needs to be reset every time
			scale.powerUp()
			weight = scale.getWeight()
			scale.powerDown()
		
		time.sleep(10)
		read_dial_indicator()
		reading = -float(next(nums)) + offset # pull current reading off generator
		
		# Calculate elapsed time in seconds
		elapsed_time = (dt.datetime.now()  - start_time).total_seconds()
		if(elapsed_time >= 820800): # if running for 9.5+ days
			Active = False
		entry = format_entry(reading, weight, elapsed_time) # create the json string with all data
		f.write(entry + "\n") # write json to text file
		print(entry)
	except: 
		print("Unexpected error:", sys.exc_info()[0])
		cleanup()

f.write("Finished experiment, exiting")
cleanup()