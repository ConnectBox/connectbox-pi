#  Loads content from USB and creates the JSON / file structure for enhanced media interface


print ("loader: Starting...")

import json
import os
import pathlib
import shutil 

# Defaults for Connectbox / TheWell
mediaDirectory = "/media/usb0"
templatesDirectory = "/var/www/enhanced/content/www/assets/templates"
contentDirectory = "/var/www/enhanced/content/www/assets/content/"

# Retrieve brand.txt
f = open('/usr/local/connectbox/brand.txt',)
brand = json.load(f)

# Sanity Checks
error = 0
if hasattr(brand, "Brand") and len(brand['Brand']) > 2:
	print ("")
else:
	brand['Brand'] = "Connectbox"
if hasattr(brand, 'Logo') and len(brand['Logo']) > 2:
	print ("")
else:
	brand['Logo'] = "imgs/logo.png"

print (brand)

print ("Building Content For " + brand['Brand'])

# Copy templates to content folder
shutil.rmtree(contentDirectory)
shutil.copytree(templatesDirectory, contentDirectory) 
os.system ("chown -R www-data.www-data " + contentDirectory + "/")

# Insert Brand and Logo
f = open (contentDirectory + "/en/data/interface.json");   # We will always place USB content in EN language which is default
interface = json.load(f);
#print (interface)
interface["APP_NAME"] = brand["Brand"]
interface["APP_LOGO"] = brand["Logo"]
#print (interface)
with open(contentDirectory + "/en/data/interface.json", 'w', encoding='utf-8') as f:
    json.dump(interface, f, ensure_ascii=False, indent=4)

# Load dictionary of file types
f = open (contentDirectory + "/en/data/types.json");
types = json.load(f);
#print (types)

# Load main.json template
f = open (contentDirectory + "/en/data/main.json");
main = json.load(f);
#print (main)

# Load directory of files
for filename in os.listdir(mediaDirectory):
	# Get file attributes
	file = os.path.join(mediaDirectory, filename)	# Example  /media/usb0/movie.mp4
	slug = pathlib.Path(file).stem					# Example  movie      (ALSO, slug is a term used in the BoltCMS mediabuilder that I'm adapting here)
	extension = pathlib.Path(file).suffix			# Example  .mp4
	try:
		# Load the item template file
		f = open (contentDirectory + "/en/data/item.json");
		item = json.load(f);
		# Update item attributes
		item["filename"] = filename
		item["image"] = types[extension]["image"]
		item["mediaType"] = types[extension]["mediaType"]
		item["slug"] = slug
		item["title"] = slug
		item["categories"].append(types[extension]["category"])
		# Save the item to a json file
		with open(contentDirectory + "/en/data/" + slug + ".json", 'w', encoding='utf-8') as f:
			json.dump(item, f, ensure_ascii=False, indent=4)
		os.system ("ln -s '" + file + "' " + contentDirectory + "/en/media/")
		# Add item to main.json
		main["content"].append(item)
		print ("Based on file type " + file + " added to enhanced interface")
	except:
		print ("Skipping (extension not supported): " + file)

# Now write main.json with an array of item objects that were pushed
with open(contentDirectory + "/en/data/main.json", 'w', encoding='utf-8') as f:
	json.dump(main, f, ensure_ascii=False, indent=4)


print ("loader: Done")

