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
templatesDirectory = "/var/www/enhanced/content/www/assets/templates"
contentDirectory = "/var/www/enhanced/content/www/assets/content"

# Init 
mains = {}        # This object contains all the data to construct each main.json at the end.  We add as we go along


# Clear the content directory so we replace it in whole and create the en directory for default
# Copy templates to content folder
try:
	os.system ("rm -r " + contentDirectory)
except:
	temp = 1 # There is a directory already

os.system ("mkdir " + contentDirectory)
shutil.copytree(templatesDirectory + '/en', contentDirectory + '/en')
os.system ("chown -R www-data.www-data " + contentDirectory + '/en')   # REMOVE AFTER TEST
f = open (templatesDirectory + "/en/data/main.json")
mains["en"] = json.load(f)
os.system ("chmod -R 755 " + mediaDirectory)

# Retrieve languageCodes.json
f = open(templatesDirectory + '/languageCodes.json',)
languageCodes = json.load(f)

# Retrieve brand.txt
f = open('/usr/local/connectbox/brand.txt',)
brand = json.load(f)

# Sanity Checks
error = 0
try:
	print ("Custom Branding: " + brand['Brand'])
except:
	brand['Brand'] = "The Open Well"
try:
	print ("Custom Logo: " + brand['Logo'])
except:
	brand['Logo'] = "imgs/logo.png"

print ("Building Content For " + brand['Brand'])

# Insert Brand and Logo into the interface template.  We will write this at the end to each language
f = open (templatesDirectory + "/en/data/interface.json");   # We will always place USB content in EN language which is default
interface = json.load(f);
interface["APP_NAME"] = brand["Brand"]
interface["APP_LOGO"] = brand["Logo"]

# Load dictionary of file types
f = open (templatesDirectory + "/en/data/types.json");
types = json.load(f);
#print (types)

webpaths = []     # As we find web content, add here so we skip files and folders within

# Check for empty directory and write default content if empty
if len(os.listdir(mediaDirectory) ) == 0:
	print("Directory is empty")
	f = open(mediaDirectory + "/theopenwell.txt", "a")
	f.write("<h2>Media Directory Is Empty</h2>Please refer to documentation (placeholder).")
	f.close()

for path,dirs,files in os.walk(mediaDirectory):
	print (path,dirs,files)
	# These next two lines ignore directories and files that start with .
	files = [f for f in files if not f[0] == '_']
	dirs[:] = [d for d in dirs if not d[0] == '_']
	files = [f for f in files if not f[0] == '.']
	dirs[:] = [d for d in dirs if not d[0] == '.']
    
	language = "en"  # By default but it will be overwritten if there are other language directories on the USB

	# Check for language folder
	tryLanguage = os.path.basename(os.path.normpath(path))
	print ('Checking For Language Folder: '+ tryLanguage)
	try:
		print ('Found Language: ' + json.dumps(languageCodes[tryLanguage]))
		language = tryLanguage
	except:
		notANewLanguage = True  # This is not going to do anything.  More of a comment

	# For web content, we need to see if we've made this folder and index then skip everything else in that folder
	skipWebPath = False;
	for testPath in webpaths:
		if path.find(testPath) != -1:
			print ("	Skipping web path: " + path)
			skipWebPath = True
	if (skipWebPath):
		continue;

		
	if (os.path.exists(path + "/index.html") or os.path.exists(path + "/index.htm")):
		print ("	" + path + " is HTML web content")
		# See if the language already exists in the directory, if not make and populate a directory from the template
		# Make a symlink to the file on USB to display the content
		os.system ("ln -s '" + path + "' " + contentDirectory + "/" + language + "/web/")
		print (dirs,path,files)
		dirs = []
		webpaths.append(path)
	for filename in files:
		print ("Processing: " + filename)

		print(webpaths,path)
		
		if (path in webpaths and filename != 'index.html' and filename != 'index.htm'):
			print ("Webpath file " + filename + " is not index so skip")
			continue
		fullFilename = path + "/" + filename							# Example /media/usb0/video.mp4
		slug = pathlib.Path(path + "/" + filename).stem					# Example  movie      (ALSO, slug is a term used in the BoltCMS mediabuilder that I'm adapting here)
		extension = pathlib.Path(path + "/" + filename).suffix			# Example  .mp4

		if (extension is None or extension == ''):
			print ("		Skipping: Extension null: " + fullFilename)
			continue
		if (extension not in types):
			print ("		Skipping: Extension not supported: " + fullFilename)
			continue

		# Load the item template file
		f = open (templatesDirectory + "/en/data/item.json");
		item = json.load(f);

		# Handle Web Content Index Page
		if (extension == '.html'):
			print (path,filename)
			item["webPath"] = "/assets/content/en/web/" + path.replace(mediaDirectory,"") + "/" + filename
			slug = os.path.basename(os.path.normpath(path))
			print (filename)

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
		if (not os.path.exists(contentDirectory + "/" + language)):
			print ("Creating Directory: " + contentDirectory + "/" + language)			
			shutil.copytree(templatesDirectory + '/en', contentDirectory + "/" + language)
			os.system ("chown -R www-data.www-data " + contentDirectory + "/" + language)
			# Load the main.json template and populate the mains for that language.
			f = open (templatesDirectory + "/en/data/main.json")
			mains[language] = json.load(f)

		# If this is a video, we can probably make a thumbnail
		if (item["mediaType"] == 'video'):
			print ("	Attempting to make a thumbnail for the video")
			os.system("ffmpeg -i '" + fullFilename + "' -ss 00:00:05.000 -vframes 1 " + contentDirectory + "/" + language + "/images/" + slug + ".png")
			item["image"] = slug + ".png"
			print ("	Thumbnail is created at: " + item["image"])

		# Save the item to item json file -- one per item
		with open(contentDirectory + "/" + language + "/data/" + slug + ".json", 'w', encoding='utf-8') as f:
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
	with open(contentDirectory + "/" + language + "/data/main.json", 'w', encoding='utf-8') as f:
		json.dump(mains[language], f, ensure_ascii=False, indent=4)
	print ("Writing interface.json for " + language)
	with open(contentDirectory + "/" + language + "/data/interface.json", 'w', encoding='utf-8') as f:
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
with open(contentDirectory + "/languages.json", 'w', encoding='utf-8') as f:
	json.dump(languageJson, f, ensure_ascii=False, indent=4)
