#  Allows ConnectBox to send status and receive updates from Chathost APIs


print ("phonehome: Starting...")

import requests
import json
import subprocess
import uuid
import os

# Retrieve brand.txt
f = open('/usr/local/connectbox/brand.txt',)
brand = json.load(f)
print (brand)

# Sanity Checks
error = 0
if len(brand['server_url']) < 5:
  print ("FATAL: No server_url")
  error=1
if len(brand['server_sitename']) < 1:
  print ("FATAL: No server_sitename")
  error=1
if error == 1:
  exit(1)

# Get boxId
results = subprocess.run(["cat", "/sys/class/net/eth0/address"], stdout=subprocess.PIPE)
boxId = results.stdout.decode('utf-8')
boxId = boxId.replace(":","-")
boxId = boxId.replace("\n","")
print ("boxId: " + boxId)

# Get authorization token
if len(brand["server_authorization"]) < 8: 
  brand["server_authorization"] = str(uuid.uuid4())
  print ("No server_authorization so we generated a GUID: " + brand["server_authorization"])
  # Save token to json
  with open('/usr/local/connectbox/brand.txt', 'w', encoding='utf-8') as f:
    json.dump(brand, f, ensure_ascii=False, indent=4)
  print ("Saved authorization to brand.txt")
token = "Bearer " + boxId + "|" + brand["server_authorization"]
print ("token: " + token)

headers = {"Authorization": token}


def processSettings(settings):
  print ("processSettings: Start")
  print (settings) 
  for setting in settings:
    command = "set " + setting["key"] + " " + setting["value"];
    if setting["key"] == 'authorization':
      command = "set brand server " + setting["key"] + "=" + setting["value"];
    if setting["key"] == 'moodle-security-key':
      command = "set securitykey " + setting["value"]; 
    print ("Handling Setting: " + command)
    try:
      results = subprocess.check_output("sudo connectboxmanage " + command, shell=True)
      results = results.decode('utf-8')
    except:
      print ("Could not process the setting: " + command)
      results = "Null (connectboxmanage returned fatal)"
    print("connectboxmanage returned: " + results)
    if len(results) > 0:
      print ("Setting For " + command + " was successful! Now inform server to delete setting") 
      response = requests.delete(brand["server_url"] + "/chathost/settings/" + setting["deleteId"],headers=headers)
      if response.status_code == 200: 	
        print ("phonehome: Successful delete of setting")
      else:
        print ("ERROR: Can't Delete Setting " + brand["server_url"])


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
results = subprocess.run(["connectboxmanage", "get", "package"], stdout=subprocess.PIPE)
package = results.stdout.decode('utf-8').strip('\n')
print (package);
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
	"siteadmin_country":brand["server_siteadmin_country"],
	"package": package
}
data.append(record)
print (data)
print ("=========");
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

print ("Launch connectboxmanage do openwellrefresh in background to sync subscribed content");
os.system("sudo connectboxmanage do openwellrefresh >/dev/null 2>/dev/null &")

print ("phonehome: Done")

