#  Allows ConnectBox to send status and receive updates from Chathost APIs


print ("phonehome: Starting...")

import requests
import json
import subprocess
import uuid

# Retrieve brand.txt
f = open('/usr/local/connectbox/brand.txt',)
brand = json.load(f)
print (brand)

# Get boxId
results = subprocess.run(["cat", "/sys/class/net/eth0/address"], stdout=subprocess.PIPE)
boxId = results.stdout.decode('utf-8')
boxId = boxId.replace(":","-")
boxId = boxId.replace("\n","")
print ("boxId: " + boxId)

# Get authorization token
if len(brand["server_authorization"]) < 8: 
  brand["server_authorzation"] = str(uuid.uuid4())
  print ("No server_authorization so we generated a GUID: " + brand["server_authorization"])
token = "Bearer " + brand["server_authorization"]
print ("token: " + token)

headers = {"X-BoxId": boxId, "Authorization": token}


def processSettings(settings):
  print ("processSettings: Start")
  print (settings) 
  for setting in settings:
    command = "set " + setting["key"] + " " + setting["value"];
    if setting["key"] == 'authorization':
      command = "set brand server_" + setting["key"] + " " + setting["value"];
    print ("Handling Setting: " + command)
    results = subprocess.check_output("sudo /usr/local/connectbox/bin/ConnectBoxManage.sh " + command, shell=True)
    print(results.decode('utf-8'))
    if results.decode('utf-8') == "SUCCESS\n":
      print ("Setting For " + command + " was successful! Now inform server to delete setting") 
      response = requests.delete(brand["server_url"] + "/chathost/settings/" + setting["deleteId"],headers=headers)
      if response.status_code == 200: 	
        print ("phonehome: Successful delete of setting")
      else:
        print ("FATAL: Can't Delete Setting " + brand["server_url"])
        exit(1)


# Main Operation Here

# Initial Trail Connection To Server
response = requests.get(brand["server_url"] + "/chathost/healthcheck", headers=headers)
if response.status_code == 200: 	
	print ("phonehome: Successful connection to healthcheck")
else:
	print ("FATAL: Can't Connect to " + brand["server_url"])
	exit(1)


# TODO: Send logs

# Send roster object
data = []
record = {
	"id":1,
	"course_name":brand["Brand"],
	"students":[],
	"teachers":[],
	"notMoodle": True,
	"sitename":brand["server_sitename"],
	"siteadmin_name":brand["server_siteadmin_name"],
	"siteadmin_email":brand["server_siteadmin_email"],
	"siteadmin_phone":brand["server_siteadmin_phone"],
}
data.append(record)
print (data)
response = requests.post(brand["server_url"] + "/chathost/courseRosters", json = data, headers=headers)
if response.status_code == 200: 	
	print ("phonehome: Successful post to /courseRosters")
elif response.status_code == 401: 	
	print ("FATAL: Unauthorized to " + brand["server_url"])
	exit(1)
else:
	print ("FATAL: Can't Connect to " + brand["server_url"])
	exit(1)

# Get Settings
response = requests.get(brand["server_url"] + "/chathost/settings", headers=headers)
if response.status_code == 200: 	
	print ("phonehome: Successful connection to settings:")
	settings = response.json()
	if len(settings) > 0:
	  print ("Handling " + str(len(settings)) + " settings")
	  processSettings(settings)
	else:
	  print ("No settings to handle")
else:
	print ("FATAL: Can't Connect to " + brand["server_url"])
	exit(1)


print ("phonehome: Done")
