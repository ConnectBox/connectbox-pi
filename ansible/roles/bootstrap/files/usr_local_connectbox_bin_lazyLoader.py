#!/usr/bin/python3
#  Loads content from USB and creates the JSON / file structure for enhanced media interface
#
# lazyLoader.py — Subscription-based content downloader for ConnectBox.
#
# This script handles on-demand content loading for ConnectBox devices that
# subscribe to a remote content package feed.  It is complementary to
# mmiLoader.py (which indexes locally-present USB content); lazyLoader.py
# downloads missing media files from a remote server when a package
# subscription is configured.
#
# Usage:
#   python3 lazyLoader.py [url]
#
#   url  (optional) — Direct URL of an openwell.zip content package to
#                     download and extract immediately, bypassing the
#                     subscription check.
#
# Workflow:
#   1. Check brand.j2 and subscription.json for a configured package feed.
#   2. If subscribed, query the feed for available packages and compare
#      the lastUpdated timestamp to determine if an update is available.
#   3. Download and extract the content package (openwell.zip) if needed.
#   4. Walk the content directory and download any media files or images
#      that are referenced in main.json / item JSON but missing on disk.

print ("lazyLoader: Starting...")

import json
import os
import pathlib
import sys
import time
from urllib.parse import unquote

# Defaults for Connectbox / TheWell
contentDirectory = "/var/www/enhanced/content/www/assets/content/"

# Count of items that failed to download; reported at the end for diagnostics.
failedItemCount = 0;

# -------------------------------------------------------------------------
# Parse command-line argument.
# An optional URL argument allows direct package injection (e.g. from
# phonehome.py or the admin interface) without going through the
# subscription feed lookup.
# -------------------------------------------------------------------------
url = ''
try:
  if (sys.argv[1] and len(sys.argv[1]) > 0):
    url = sys.argv[1];
    print ("Download URL: " + url);
except:
  print ("Download URL: NONE")

# -------------------------------------------------------------------------
# Subscription check.
# brand.j2 holds server configuration; subscription.json (in the content
# directory) records the subscribed package name and the timestamp of the
# last successful update.  If both exist and no direct URL was provided,
# this device is in subscription mode.
# -------------------------------------------------------------------------
isSubscribed = False;
try:
  print ("Check For Subscription");
  f = open('/usr/local/connectbox/brand.j2');
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

# -------------------------------------------------------------------------
# Feed query and update check.
# Download the package feed JSON and compare the remote timestamp against
# the locally cached lastUpdated value.  If the remote package is newer,
# set the download URL and update the cached timestamp so we do not
# re-download on the next run when nothing has changed.
# -------------------------------------------------------------------------
if (isSubscribed):
  print ("Getting packagesAPIFeed From " + subscription['packagesAPIFeed'])
  os.system("wget -nv '" + subscription['packagesAPIFeed'] + "' -O /tmp/packages.json")
  f = open('/tmp/packages.json');
  packages = json.load(f);
  for record in packages:
    # Look for the slim variant of the subscribed package by name.
    # Slim packages are optimised for low-bandwidth delivery.
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

# -------------------------------------------------------------------------
# Package download and extraction.
# If a URL was provided (directly or via the subscription feed), download
# the openwell.zip package and extract it into the web-server asset tree.
# The -o flag overwrites existing files so the content directory is always
# up to date after extraction.
# -------------------------------------------------------------------------
if (len(url) > 1):
  print ("Handling File: " + url)
  os.system("wget -nv '" + url + "' -O /tmp/openwell.zip")
  os.system("unzip -o /tmp/openwell.zip -d /var/www/enhanced/content/www/assets/")
  print ("Loaded Package File")
else:
  print ("No Package File To Download");

print ("==================================================")
print ("Looking for missing content and trying to download")

# Sub-directories expected inside each language folder.
# These are created if absent so that subsequent wget downloads have a
# valid destination path.
directories = ["data", "images", "media", "html"]

# -------------------------------------------------------------------------
# Missing-content recovery loop.
# Walk every language directory in the content tree and compare the media
# files listed in main.json against what is actually on disk.  Download any
# missing images or media files individually from their resourceUrl / imageUrl.
#
# This handles the case where a package was partially downloaded or where
# individual files were deleted from the content directory.
# -------------------------------------------------------------------------
for language in next(os.walk(contentDirectory))[1]:
	print ("Found Possible Language Folder: " + language)
	if os.path.exists(contentDirectory + language + "/data/main.json"):
		print ("Confirmed Language: " + language + " main.json exists")
		# Load main.json to process
		f = open (contentDirectory + language + "/data/main.json")
		thisMain = json.load(f)

		# Ensure all expected sub-directories exist for this language.
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

		# Walk each content item declared in main.json.
		for content in thisMain["content"]:
			print (" Processing: " + content["title"])
			f = open (contentDirectory + language + "/data/" + content["slug"] + ".json")
			details = json.load(f)

			# Determine whether this is a collection (multiple episodes) or a
			# single item.  Collections have an 'episodes' key; single items
			# are wrapped in a list so the download loop below is uniform.
			items = []
			try:
				items = details["episodes"]
				os.system("wget -nv '" + details["imageUrl"] + "' -O " + contentDirectory + language + "/images/" + details["image"])
				print ("	Loading Multi-Episodic Content: " + details["title"] )
			except:
				items = [details]
				print ("	Single Episodic Content: " + details["title"])

			# For each item (or episode), check for media and image files on disk.
			# Download only if the file is missing to avoid unnecessary bandwidth use.
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
