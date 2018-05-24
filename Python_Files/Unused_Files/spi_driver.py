import RPi.GPIO as GPIO
import time
#import threading

GPIO.setmode(GPIO.BOARD) # Use board numbers, not BCM
GPIO.setwarnings(False) # Disables the warning that other things may be using the same pins

# Define pins
SCLK = 9 # Position 19, clock input, D- from dial indicator
MISO = 10 # Position 21, data input, D+ from dial indicator

#PWR = 2; # Position 3, output, power cycles dial indicator

# Set up input pins with pull up resistors
GPIO.setup([SCLK, MISO], GPIO.IN) 

# Set up output pin with initial value high
#GPIO.setup(PWR, GPIO.OUT, initial=GPIO.HIGH)

# See for threaded callbacks https://sourceforge.net/p/raspberry-gpio-python/wiki/Inputs/
#GPIO.add_event_detect(BTN_G, GPIO.BOTH, handle)

# Bit counter
count = 0
control = []

# Sleep constant
SLEEP_TIME = 0.070

# Buffer for incoming bits
bit_array = []

def read_bit(SCLK, MISO, bit_array, count):
# This function reads a single bit and returns either 0 or 1
# Bits are valid when SCLK is low

	SCLK = GPIO.wait_for_edge(SCLK, GPIO.FALLING);
	if SCLK is None:
		# Never detected a falling edge
		print("Nothing to read")
		# Do nothing
		return count
	else:
		bit_array.append(GPIO.input(MISO))
		count += 1
		return count
			
while True:
	control = GPIO.wait_for_edge(SCLK, GPIO.FALLING, timeout = 10); # 10 ms timeout
	print(control)
	if control is None:
		# Time out, trigger reset
		time.sleep(SLEEP_TIME) # 70 ms
	else:
		# Detected falling edge
		
		# Read first bit here, already detected falling edge so safe to read
		bit_array.append(GPIO.input(MISO))
		
		# Set up a timer here to reset count after ~12 ms
		
		while count < 31: # 6 groups of 4 bits, 1st read above
			count = read_bit(SCLK, MISO, bit_array, count)
		
		print(bit_array)
		print("\n\n\n")
	
	