#!/usr/bin/python3
import sys
import time
import signal # catch SIGTERM
import datetime as dt	# used for recording date and time
import queue	# queue data structure for recording keyboard events
import RPi.GPIO as GPIO	# GPIO control
#from scale import Scale # HX711 sense amplifier package
import keyboard	# Key logging package
import requests	# REST package
import code # allows breaking out into shell for debugging

# Whenever weight is added, take readings more frequently.
# Take reading every FREQUENT_READING_INTERVAL seconds,
# repeat FREQUENT_READING_REPETITIONS times
FREQUENT_READING_INTERVAL = 5
FREQUENT_READING_REPETITIONS = 24

# Normal reading interval in seconds after weight has settled
READING_INTERVAL = 60

# True if results are posted to University database
# False if results are logged only locally
LIVE = True

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
	i = 0
	while i < 2:
		GPIO.output(dial_read, True)
		time.sleep(.5)
		GPIO.output(dial_read, False)
		i += 1

def reset_dial_indicator(reading):
	'''
		This function turns off the dial indicator for a few seconds
		and then turns it back on. A side effect of this operation is 
		that it zeroes the reading, so the reading must be preserved
		before the reset. Zeroes timer of how long it has been since
		since last indicator reset
	'''
	global f, dial_power
	
	offset = reading # preserve previous reading through reset
	string = str.format("Resetting dial indicator to prevent timeout at elapsed time {}s\n", elapsed_time)
	#print(string)
	f.write(string)
	
	GPIO.output(dial_power, False) # turn off dial indicator
	time.sleep(3) # wait long enough to discharge dial indicator, ensure it's off
	GPIO.output(dial_power, True) # turn dial indicator back on
	time.sleep(3) # wait long enough to make sure dial indicator is back on
	
	return time.time(), offset # reset timer
		
def generator():
	'''
		As keyboard events arrive in the queue, remove them from the
		queue in order to be read by keyboard.get_typed_strings
	'''
	global events
	while True:
		yield events.get()

def format_entry(displacement, weight, elapsed_time, pr):
	'''
		Format data into a string for local logging
	'''
	global experiment_id
	
	return str.format("experiment_id: {0}, displacement: {1}, weight: {2}, time: {3}, POST_response: {4}", experiment_id, displacement, weight, elapsed_time, pr)

def post(displacement, weight, elapsed_time):
	'''
		Format data into key value pairs and post to database
	'''
	global experiment_id, url
	
	data = {
		'experiment_id' : experiment_id, 
		'displacement'  : str(displacement), 
		'weight': "{:.2}".format(weight), 
		'time': "{:.2}".format(elapsed_time)
		}
	if(LIVE):
		pr = requests.post(url = url, data = data) # post response
	else:
		pr = "Didn't POST\n"
	return pr

def signal_handler(signal, frame):
	'''
		Catch signals and exit gracefully
	'''
	exitmsg = str.format("Exiting because of signal")
	print(exitmsg)
	f.write(exitmsg)
	cleanup()

def update_weight(weight_btn):
	'''
		Callback function that triggers on pin interrupt from weight_btn.
		Increments the weight_index to signify technician has added a
		weight to the oedometer pendulum. Take readings more frequently after
		weight change, just like beginning of the program
	'''
	global debounce, weight, weight_index, reset_timer, reading, offset
	if(debounce):
		if(weight_index < 9):
			weight_index = weight_index + 1
			weight = weight_table[weight_index]
		debounce = False
		str = "Updated weight value\n"
		print(str)
		f.write(str)

		reset_timer,offset = reset_dial_indicator(reading);
		for i in range(FREQUENT_READING_REPETITIONS):
			time.sleep(FREQUENT_READING_INTERVAL)
			read_dial_indicator()
			reading = -float(next(nums)) + offset # pull current reading off generator

			# Calculate elapsed time in seconds
			elapsed_time = (dt.datetime.now()  - start_time).total_seconds()

			pr = post(reading, weight, elapsed_time) # post data to database

			entry = format_entry(reading, weight, elapsed_time, pr) # create string with all data
			f.write(entry + "\n") # write local log to text file
			f.flush()
			#print(entry)
	else:
		print("Weight was already updated within last 4 minutes")
	
def cleanup():
	'''
		Close files and GPIO objects before exit
	'''
	global f
	GPIO.cleanup()
	f.close()
	sys.exit()


url = "https://webapps.umassd.edu/cen/telemetry/index.php" # REST URL

# # Class for controlling sense amplifier
# scale = Scale()

# # HOW TO CALCULATE THE REFERENCE UNIT
# #########################################
# # To set the reference unit to 1.
# # Call get_weight before and after putting 1000g weight on your sensor.
# # Divide difference with grams (1000g) and use it as reference unit.
# scale.setReferenceUnit(1)
# scale.tare()
# scale.reset()

# GPIO control setup
GPIO.setmode(GPIO.BCM) # Use BCM numbering
GPIO.setwarnings(False) # Disables warning pins may be in use

dial_read = 3 # Pin used to trigger reads from dial indicator
dial_power = 2 # Pin used to power 
weight_btn = 17 # Pin used to indicate adding weight

GPIO.setup([dial_read, dial_power], GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(weight_btn, GPIO.IN,  pull_up_down=GPIO.PUD_UP) 
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
weight_table = [0.25, 0.5, 1, 2, 4, 8, 16, 8, 4, 2] # Pressure in tsf
weight_index = 0 # where are we in the weight table?
weight = weight_table[weight_index] # weight on the weight rack
# Event to update weight when a button is pressed
GPIO.add_event_detect(weight_btn, GPIO.FALLING, callback = update_weight, bouncetime=500)
elapsed_time = [] # total experiment elapsed time in seconds	
Active = True # boolean to determine when to stop recording
debounce = True # boolean used to debounce weight button

# Catch and gracefully handle signals
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

print("Starting soil consolidation experiment with id " + experiment_id)
f = open(experiment_id + ".log", 'w') # open a file in write mode

keyboard.hook(handle_event) # set call back for keyboard event arrival	
nums = keyboard.get_typed_strings(generator()) # generator for keyboard strings
offset = 0 # initial offset is 0

# weight = scale.getWeight() # initial reading, check every 4 minutes
# scale.powerDown()

# At the start of the test, use a shorter time for data collection
# Same as main control loop but takes entries more frequently
for i in range(FREQUENT_READING_REPETITIONS):
	time.sleep(FREQUENT_READING_INTERVAL)
	read_dial_indicator()
	reading = -float(next(nums)) + offset # pull current reading off generator

	# Calculate elapsed time in seconds
	elapsed_time = (dt.datetime.now()  - start_time).total_seconds()

	pr = post(reading, weight, elapsed_time) # post data to database

	entry = format_entry(reading, weight, elapsed_time, pr) # create string with all data
	f.write(entry + "\n") # write local log to text file
	f.flush()
	#print(entry)
	
reset_timer = time.time() # timer for the dial indicator reset
read_timer = time.time() # timer for taking reads

# Reset the dial indicator before moving into main control loop
reset_timer, offset = reset_dial_indicator(reading)

# Main control loop
while Active:
	try:
		# elapsed time for use in loop controlling dial indicator reset
		reset_time = time.time() - reset_timer 
		read_time = time.time() - read_timer # elapsed time for use taking readings

		# This if statement controls when a reading is taken. If true, take reading,
		# else check if we need to prevent the dial indicator from reseting, else 
		# do nothing
		if(read_time >= READING_INTERVAL): 
			time.sleep(1)
			read_dial_indicator()			
			reading = -float(next(nums)) + offset # pull current reading off generator

						
			# Calculate elapsed time in seconds
			elapsed_time = (dt.datetime.now()  - start_time).total_seconds() # for whole experiment
			if(elapsed_time >= 820800): # if running for 9.5+ days end the experiment
				Active = False
			
			read_timer = time.time() # reset timer
			# # Get new scale reading, needs to be reset every time
			# scale.powerUp()
			# weight = scale.getWeight()
			# scale.powerDown()
			
			pr = post(reading, weight, elapsed_time) # post data to database
			entry = format_entry(reading, weight, elapsed_time, pr) # create string with all data
			f.write(entry + "\n") # write local log to text file
			f.flush() # write to disk so we can check what's going on outside process
			#print(entry)
		
		# This if statement prevents dial indicator from timing itself out
		# by power cycling it. Not an exact measurement, subject to drift
		# but good enough for our purpose. Reset loop time in here
		if(reset_time >= 240): # More than four minutes passed
			reset_timer, offset = reset_dial_indicator(reading)			
			if(not debounce): # weight button was pressed, allow it to be pressed again
				debounce = True
	except:
		#code.interact(local = locals()) # Useful for debugging
		print("Unexpected error:", sys.exc_info()[0])
		cleanup()

f.write("Finished experiment, exiting\n")
cleanup()