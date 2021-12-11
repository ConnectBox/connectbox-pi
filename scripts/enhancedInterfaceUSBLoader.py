#  Loads content from USB and creates the JSON / file structure for enhanced media interface


print ("loader: Starting...")

import json
import os
import pathlib
import shutil 
import mimetypes

mimetypes.init()

# Defaults for Connectbox / TheWell
mediaDirectory = "/media/usb0"
templatesDirectory = "/var/www/enhanced/content/www/assets/templates/en"
contentDirectory = "/var/www/enhanced/content/www/assets/content/"

# Retrieve languageCodes.json
f = open('/var/www/enhanced/content/www/assets/templates/languageCodes.json',)
languageCodes = json.load(f)

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

print ("Building Content For " + brand['Brand'])

# Copy templates to content folder
try:
	shutil.rmtree(contentDirectory)
except:
	temp = 1 # There is a directory already

# Insert Brand and Logo into the interface template.  We will write this at the end to each language
f = open (templatesDirectory + "/data/interface.json");   # We will always place USB content in EN language which is default
interface = json.load(f);
interface["APP_NAME"] = brand["Brand"]
interface["APP_LOGO"] = brand["Logo"]

# Load dictionary of file types
f = open (templatesDirectory + "/data/types.json");
types = json.load(f);
#print (types)


mains = {}  # This object contains all the data to construct each main.json at the end.  We add as we go along

for path,dirs,files in os.walk(mediaDirectory):
	print (path,dirs,files)
	# These next two lines ignore directories and files that start with .
	files = [f for f in files if not f[0] == '_']
	dirs[:] = [d for d in dirs if not d[0] == '_']
	files = [f for f in files if not f[0] == '.']
	dirs[:] = [d for d in dirs if not d[0] == '.']
    
	language = "en"  # By default but it will be overwritten if there are other language directories on the USB
	if path.replace(mediaDirectory + "/","") in languageCodes:
		language = path.replace(mediaDirectory + "/","")
	for filename in files:
		print ("Processing: " + filename)
		fullFilename = path + "/" + filename							# Example /media/usb0/video.mp4
		slug = pathlib.Path(path + "/" + filename).stem					# Example  movie      (ALSO, slug is a term used in the BoltCMS mediabuilder that I'm adapting here)
		extension = pathlib.Path(path + "/" + filename).suffix			# Example  .mp4
		#print (slug,extension)
		if (extension is None or extension == ''):
			print ("		Skipping: Extension null: " + fullFilename)
			continue
		if (extension not in types):
			print ("		Skipping: Extension not supported: " + fullFilename)
			continue
		# Load the item template file
		f = open (templatesDirectory + "/data/item.json");
		item = json.load(f);
		# Update item attributes
		item["filename"] = filename
		item["image"] = types[extension]["image"]
		item["mediaType"] = types[extension]["mediaType"]
		print ("	Determining Mimetype of " + extension)

		if (types[extension]["mediaType"] == "image"):
			item["image"] = filename
			os.system ("ln -s '" + fullFilename + "' " + contentDirectory + "/" + language + "/images/")
		if (hasattr(types[extension],"mimeType")):
			item["mimeType"] = types[extension]["mimeType"]		
			print ("	mimetypes types.json says: " + item["mimeType"])
		elif (mimetypes.guess_type(fullFilename)[0] is not None):
			item["mimeType"] = mimetypes.guess_type(fullFilename)[0]
			print ("	mimetypes modules says: " + item["mimeType"])
		else:
			item["mimeType"] = "application/octet-stream"
			print ("	Default mimetype: " + item["mimeType"])
		item["slug"] = slug
		item["title"] = slug
		item["categories"].append(types[extension]["category"])
		# If the directory is not a language, make a non-duplicate category to organize that content
		if (os.path.basename(os.path.normpath(path)) != language and path != mediaDirectory and types[extension]["category"] != os.path.basename(os.path.normpath(path)).capitalize()):
			item["categories"].append(os.path.basename(os.path.normpath(path)).capitalize())
		#print (item)

		# See if the language already exists in the directory, if not make and populate a directory from the template
		if (not os.path.exists(contentDirectory + language)):
			print ("Creating Directory: " + contentDirectory + language)			
			shutil.copytree(templatesDirectory, contentDirectory + language)
			os.system ("chown -R www-data.www-data " + contentDirectory + language)
			# Load the main.json template and populate the mains for that language.
			f = open (templatesDirectory + "/data/main.json")
			mains[language] = json.load(f)

		# Save the item to item json file -- one per item
		with open(contentDirectory + language + "/data/" + slug + ".json", 'w', encoding='utf-8') as f:
			json.dump(item, f, ensure_ascii=False, indent=4)
			
		# Make a symlink to the file on USB to display the content
		os.system ("ln -s '" + fullFilename + "' " + contentDirectory + "/" + language + "/media/")

		# Add item to main.json -- which is the store of all content in this language
		mains[language]["content"].append(item)
		print ("Based on file type " + fullFilename + " added to enhanced interface for language " + language)


# Now go through each language that we found and processed and write the interface.json and main.json for each 
languageJson = []
for language in mains:
	print ("Writing main.json for " + language)
	with open(contentDirectory + language + "/data/main.json", 'w', encoding='utf-8') as f:
		json.dump(mains[language], f, ensure_ascii=False, indent=4)
	print ("Writing interface.json for " + language)
	with open(contentDirectory + language + "/data/interface.json", 'w', encoding='utf-8') as f:
		json.dump(interface, f, ensure_ascii=False, indent=4)
	# Add this language to the language interface
	languageJsonObject = {}
	languageJsonObject["codes"] = [language]
	languageJsonObject["text"] = languageCodes[language]["native"][0]
	languageJson.append(languageJsonObject)

# Determine which language should be default.  It is english or first one found
hasDefault = 0
for record in languageJson:
	if (record["codes"][0] == "en"):
		hasDefault = 1
		record["default"] = True
if (hasDefault == 0):
	languageJson[0]["default"] = True

print ("Writing languages.json")
with open(contentDirectory + "languages.json", 'w', encoding='utf-8') as f:
	json.dump(languageJson, f, ensure_ascii=False, indent=4)
