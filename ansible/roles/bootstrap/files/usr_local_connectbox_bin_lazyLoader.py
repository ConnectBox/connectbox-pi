#!/usr/bin/python3
#  Loads content from USB and creates the JSON / file structure for enhanced media interface


print ("lazyLoader: Starting...")

import json
import os
import pathlib
import sys
import time
from urllib.parse import unquote

# Defaults for Connectbox / TheWell
contentDirectory = "/var/www/enhanced/content/www/assets/content/"

failedItemCount = 0;

# URL:
url = ''
try:
  if (sys.argv[1] and len(sys.argv[1]) > 0):
    url = sys.argv[1];
    print ("Download URL: " + url);
except:
  print ("Download URL: NONE")

# See if we have a package subscription
isSubscribed = False;
try:
  print ("Check For Subscription");
  f = open('/usr/local/connectbox/brand.txt');
  brand = json.load(f)
  f = open(contentDirectory + 'subscription.json');
  subscription = json.load(f)
  # IF we don't have argument of new URL AND we have subscription data, this is a subscribed box
  if (len(url) == 0 and 'packagesAPIFeed' in subscription):
    isSubscribed = True;
    subscription['packageName'] = unquote(subscription['packagesAPIFeed']).split("packageName=")[1];
    print('Box is subscribed to: ' + subscription['packageName'])
except FileNotFoundError:
  print("This device is not subscribed to Server package");

# If subscribed, let's check for updates
if (isSubscribed):
  print ("Getting packagesAPIFeed From " + subscription['packagesAPIFeed'])
  os.system("wget -nv '" + subscription['packagesAPIFeed'] + "' -O /tmp/packages.json")
  f = open('/tmp/packages.json');
  packages = json.load(f);
  for record in packages:
    #print ("Subscripton: Is this a match? " + record['package']);
    if (record['is_slim'] is True and record['package'] == subscription['packageName']):
      print ("Subscription: " + record["package"]);
      if (subscription['lastUpdated'] < record['timestamp']):
        print ("Subscription: Updates Found");
        url = record['filepath']
        subscription['lastUpdated'] = time.time();
        with open(contentDirectory + 'subscription.json', 'w', encoding='utf-8') as f:
          json.dump(subscription, f, ensure_ascii=False, indent=4)
      else:
        print ("Subscription: No Updates Found");

# First Download the URL and unzip it or find missing content
if (len(url) > 1):
  print ("Handling File: " + url)
  os.system("wget -nv '" + url + "' -O /tmp/openwell.zip")
  os.system("unzip -o /tmp/openwell.zip -d /var/www/enhanced/content/www/assets/")
  print ("Loaded Package File")
else:
  print ("No Package File To Download");

print ("==================================================")
print ("Looking for missing content and trying to download")

directories =  ["data", "images", "media", "html"]

# Go through all the language folders in the package
for language in next(os.walk(contentDirectory))[1]:
	print ("Found Possible Language Folder: " + language)
	if os.path.exists(contentDirectory + language + "/data/main.json"):
		print ("Confirmed Language: " + language + " main.json exists")
		# Load main.json to process
		f = open (contentDirectory + language + "/data/main.json")
		thisMain = json.load(f)
		for directory in directories:
			if os.path.isdir(contentDirectory + language + "/" + directory):
				print ("	Directory Exists: " + contentDirectory + language + "/" + directory)
			else:
				try:
					os.mkdir(contentDirectory + language + "/" + directory)
					print ("	Created Directory at " + contentDirectory + language + "/" + directory)
				except:
					print ("	FAILED to Create Directory at " + contentDirectory + language + "/" + directory)
		print (" ")
		print ("=================================================================================")
		for content in thisMain["content"]:
			print (" Processing: " + content["title"])
			f = open (contentDirectory + language + "/data/" + content["slug"] + ".json")
			details = json.load(f)
			#print (json.dumps(details))
			items = []
			try:
				items = details["episodes"]
				os.system("wget -nv '" + details["imageUrl"] + "' -O " + contentDirectory + language + "/images/" + details["image"])
				print ("	Loading Multi-Episodic Content: " + details["title"] )
			except:
				items = [details]
				print ("	Single Episodic Content: " + details["title"])
			#print (json.dumps(items))
			for item in items:
				print ("	Checking Media Content: " + item["filename"])
				if (os.path.exists(contentDirectory + language + "/media/" + item["filename"])):
					print ("	Content Exists: " + item["filename"])
				else:
					try:
					  print ("	LOAD CONTENT: " + item["filename"] + " from " + item["resourceUrl"])
					  os.system("wget -nv '" + item["resourceUrl"] + "' -O " + contentDirectory + language + "/media/" + item["filename"])
					  print ("		Content Downloaded to: " + item["filename"])
					except:
						print ("		FAILED To Download: " + item["title"])
						failedItemCount+=1;
				print ("----------------------------------------")
				print (" ")
				print ("	Checking Image Content: " + item["image"])
				if (os.path.exists(contentDirectory + language + "/images/" + item["image"])):
					print ("	Content Exists: " + item["image"])
				else:
					try:
					  print ("	LOAD CONTENT: " + item["image"] + " from " + item["imageUrl"])
					  os.system("wget -nv '" + item["imageUrl"] + "' -O " + contentDirectory + language + "/images/" + item["image"])
					  print ("		Content Downloaded to: " + item["image"])
					except:
						print ("		FAILED To Download: " + item["title"])
						failedItemCount+=1;
				print ("----------------------------------------")
				print (" ")

print ("Failed Item Count:" + str(failedItemCount));
print ("Done.")