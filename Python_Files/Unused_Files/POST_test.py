#!/usr/bin/python3
import requests
import datetime as dt
url = "https://webapps.umassd.edu/cen/telemetry/index.php"
experiment_id = "testID"
# data = {
		# 'experiment_id' : 'test_experiment', 
		# 'displacement'  : '0.0', 
		# 'weight': '-0.8431372548922595', 
		# 'time': '19.490132'
		# }

def post(displacement, weight, elapsed_time):
	'''
		Format data into key value pairs and post to database
	'''
	global experiment_id, url
	
	data = {
		'experiment_id' : experiment_id, 
		'displacement'  : str(displacement), 
		'weight': "{:0.2f}".format(weight), 
		'time': "{:0.2f}".format(time)
		}
	
	pr = requests.post(url = url, data = data) # post response
	
	return pr


displacement = 0.0
weight = 19.33333
time = 34.48284839

pr = post(displacement, weight, time)
gr = requests.get(url = url)

print(pr.status_code)
print("POST response: ", pr.text)
print(gr.status_code)
print("GET response: ", gr.text)