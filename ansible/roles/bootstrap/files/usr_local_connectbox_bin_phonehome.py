#!/usr/bin/python3
#  Allows ConnectBox to send status and receive updates from Chathost APIs
#
# phonehome.py — Remote telemetry and configuration sync script.
#
# This script is invoked manually or via cron to:
#   1. Authenticate the device with the remote Chathost server using a
#      per-device bearer token (MAC-address + UUID).
#   2. POST device roster/status information (brand name, site admin
#      contacts, package name) to /chathost/courseRosters.
#   3. POST the local content access log to /chathost/logs/content.
#   4. GET any pending configuration changes from /chathost/settings and
#      apply them via connectboxmanage.
#   5. Trigger an openwell content refresh in the background.
#
# All server_url, server_sitename, and authorization values are read from
# /usr/local/connectbox/brand.j2, which is the single source of truth for
# device configuration.

print ("phonehome: Starting...")

import requests
import json
import subprocess
import uuid
import os

# -------------------------------------------------------------------------
# Load device configuration from brand.j2.
# brand.j2 is JSON and holds all device-level settings including the remote
# server URL and the per-device authorization token.
# -------------------------------------------------------------------------
f = open('/usr/local/connectbox/brand.j2',)
brand = json.load(f)
print (brand)

# -------------------------------------------------------------------------
# Sanity checks — abort early if essential config is missing.
# A missing server_url or server_sitename means we have nothing to connect
# to, so there is no point continuing.
# -------------------------------------------------------------------------
error = 0
if len(brand['server_url']) < 5:
  print ("FATAL: No server_url")
  error=1
if len(brand['server_sitename']) < 1:
  print ("FATAL: No server_sitename")
  error=1
if error == 1:
  exit(1)

# -------------------------------------------------------------------------
# Derive the device's unique box ID from its Ethernet MAC address.
# The MAC address is stable across reboots and uniquely identifies this
# device to the server without requiring any registration step.
# Colons are replaced with hyphens to produce a URL-safe identifier.
# -------------------------------------------------------------------------
results = subprocess.run(["cat", "/sys/class/net/eth0/address"], stdout=subprocess.PIPE)
boxId = results.stdout.decode('utf-8')
boxId = boxId.replace(":","-")
boxId = boxId.replace("\n","")
print ("boxId: " + boxId)

# -------------------------------------------------------------------------
# Authorization token generation and persistence.
# If brand.j2 does not yet contain a server_authorization UUID (length < 8),
# generate one now and save it back to brand.j2 so it persists across reboots.
# The bearer token combines the box ID and the authorization UUID so the
# server can identify both the device and verify its registration.
# -------------------------------------------------------------------------
if len(brand["server_authorization"]) < 8:
  brand["server_authorization"] = str(uuid.uuid4())
  print ("No server_authorization so we generated a GUID: " + brand["server_authorization"])
  # Save token to json
  with open('/usr/local/connectbox/brand.j2', 'w', encoding='utf-8') as f:
    json.dump(brand, f, ensure_ascii=False, indent=4)
  print ("Saved authorization to brand.j2")
token = "Bearer " + boxId + "|" + brand["server_authorization"]
print ("token: " + token)

headers = {"Authorization": token}


def processSettings(settings):
  """Apply a list of remote configuration settings to this device.

  Each setting is a dict with 'key', 'value', and 'deleteId' fields.
  The key is translated into a connectboxmanage command and executed via
  sudo.  On success the setting is deleted from the server so it is not
  re-applied on the next phonehome run.

  Special-cased keys:
    'authorization'     — mapped to 'set brand server authorization=<value>'
    'moodle-security-key' — mapped to 'set securitykey <value>'
  All other keys use the generic 'set <key> <value>' form.

  Parameters
  ----------
  settings : list of dict
      List of setting objects from the /chathost/settings endpoint.

  Returns
  -------
  None
  """
  print ("processSettings: Start")
  print (settings)
  for setting in settings:
    # Build the connectboxmanage command for this setting key.
    # Special keys require a different command structure.
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

    # Only notify the server to delete the setting if connectboxmanage
    # returned a non-empty result, indicating the command was processed.
    if len(results) > 0:
      print ("Setting For " + command + " was successful! Now inform server to delete setting")
      response = requests.delete(brand["server_url"] + "/chathost/settings/" + setting["deleteId"],headers=headers)
      if response.status_code == 200:
        print ("phonehome: Successful delete of setting")
      else:
        print ("ERROR: Can't Delete Setting " + brand["server_url"])


# -------------------------------------------------------------------------
# Step 1: Health check — verify the server is reachable before doing any work.
# Abort immediately if we cannot reach the server; all subsequent steps
# depend on a live connection.
# -------------------------------------------------------------------------
response = requests.get(brand["server_url"] + "/chathost/healthcheck", headers=headers)
if response.status_code == 200:
	print ("phonehome: Successful connection to healthcheck")
else:
	print ("FATAL: Can't Connect to " + brand["server_url"])
	exit(1)


# -------------------------------------------------------------------------
# Step 2: POST device roster to the server.
# The roster includes brand name, site admin contacts, and current package
# status. The server uses this to track which devices are online and what
# content they are running.
# -------------------------------------------------------------------------
data = []
results = subprocess.run(["connectboxmanage", "get", "package"], stdout=subprocess.PIPE)
package = results.stdout.decode('utf-8').strip('\n')
print (package);
results = subprocess.run(["connectboxmanage", "get", "packagestatus"], stdout=subprocess.PIPE)
packageStatus = results.stdout.decode('utf-8').strip('\n')
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
	"package": package,
	"packageStatus": packageStatus
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

# -------------------------------------------------------------------------
# Step 3: POST content access log to the server.
# The web log records which content items were accessed and is used for
# analytics on the server side. Only posted if the log has meaningful
# content (length > 5 to skip empty/whitespace-only responses).
# -------------------------------------------------------------------------
results = subprocess.run(["connectboxmanage", "get", "syncweblog"], stdout=subprocess.PIPE)
data = results.stdout.decode('utf-8').strip('\n')
if (len(data) > 5):
	jsonLog = json.loads(data)
	response = requests.post(brand["server_url"] + "/chathost/logs/content", json = jsonLog, headers=headers)
	if response.status_code == 200:
		print ("phonehome: Successful post to /logs/content")
	elif response.status_code == 401:
		print ("FATAL: Unauthorized to " + brand["server_url"])
		exit(1)
	else:
		print ("FATAL: Can't Connect to " + brand["server_url"])
		exit(1)
else:
	print ("phonehome: No weblog to sync")


# -------------------------------------------------------------------------
# Step 4: Fetch and apply any pending configuration changes from the server.
# Settings are queued on the server and consumed here, then deleted so they
# are not re-applied on subsequent phonehome runs.
# -------------------------------------------------------------------------
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

# -------------------------------------------------------------------------
# Step 5: Trigger an openwell content refresh in the background.
# This is fire-and-forget (output discarded, runs detached) so phonehome
# completes immediately without waiting for the potentially long refresh.
# -------------------------------------------------------------------------
print ("Launch connectboxmanage do openwellrefresh in background to sync subscribed content");
os.system("sudo connectboxmanage do openwellrefresh >/dev/null 2>/dev/null &")

print ("phonehome: Done")
