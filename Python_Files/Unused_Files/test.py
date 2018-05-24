import keyboard
import RPi.GPIO as GPIO	# GPIO control
import sys
import time
import threading as thread
import queue

GPIO.setmode(GPIO.BCM) # Use BCM numbering
GPIO.setwarnings(False) # Disables the warning that other things may be using the same pins

dial_read = 3
dial_power = 2

# Set up output pin with initial value low
GPIO.setup([dial_read, dial_power], GPIO.OUT, initial=GPIO.LOW)
time.sleep(5) # wait long enough to discharge dial indicator
GPIO.output(dial_power, True) # turn dial indicator back on

events = queue.Queue()

def handle_event(event):
	global events
	events.put(event)

def generate_events():
	i = 0
	while i < 2:
		GPIO.output(dial_read, True)
		time.sleep(.5)
		GPIO.output(dial_read, False)
		i += 1

def generator():
	global events
	while True:
		yield events.get()


keyboard.hook(handle_event)
strings = keyboard.get_typed_strings(generator())
while True:
	try:
		time.sleep(5)
		generate_events()
		print(next(strings))
	except KeyboardInterrupt:
		GPIO.cleanup()
		sys.exit()