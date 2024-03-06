#!/usr/bin/python3
#  Loads content from USB and creates the JSON / file structure for enhanced media interface


print ("loader: Starting...")

import json
import os
import pathlib
import shutil
import mimetypes
import logging

mimetypes.init()

#######################################################
def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3

# Defaults for Connectbox / TheWell
mediaDirectory = "/media/usb0/content"
templatesDirectory = "/var/www/enhanced/content/www/assets/templates"
contentDirectory = "/var/www/enhanced/content/www/assets/content"
zipFileName = mediaDirectory + '/saved.zip';

# Init
mains = {}        # This object contains all the data to construct each main.json at the end.  We add as we go along


# Clear the content directory so we replace it in whole and create the en directory for default
# Copy templates to content folder
try:
	os.system ("rm -r " + contentDirectory)
except:
	temp = 1 # There is a directory already

##########################################################################
#  See if this directory is language folder or content
##########################################################################
print ("	Check for saved.zip");
if (os.path.exists(mediaDirectory + "/saved.zip")):
	print ("	Found saved.zip.  Unzipping and restoring to " + contentDirectory);
	print (" ")
	print ("****If you want to reload the USB, delete the file saved.zip from the USB drive.");
	os.system ("mkdir " + contentDirectory)
	os.system ("(cd " + contentDirectory + " && unzip " + zipFileName + ")");
	print ("DONE");
	exit(0);

os.system ("mkdir " + contentDirectory)
shutil.copytree(templatesDirectory + '/en', contentDirectory + '/en')
shutil.copy(templatesDirectory + '/footer.html', contentDirectory)
os.system ("chown -R www-data.www-data " + contentDirectory)   # REMOVE AFTER TEST
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
	if (len(brand['Brand']) < 5):
		throw();
	print ("Custom Branding: " + brand['Brand'])
except:
	brand['Brand'] = os.popen('cat /etc/hostname').read()
try:
	if (len(brand['Logo']) < 5):
		throw();
	print ("Custom Logo: " + brand['Logo'])
except:
	brand['Logo'] = "imgs/logo.png"

print ("Building Content For " + brand['Brand'])

# Insert Brand and Logo into the interface template.  We will write this at the end to each language
f = open (templatesDirectory + "/en/data/interface.json");   # We will always place USB content in EN language which is default
interface = json.load(f);
interface["APP_NAME"] = brand["Brand"]

if brand["enhancedInterfaceLogo"] != "" :
        interface["APP_LOGO"] = brand["enhancedInterfaceLogo"]
else:
        interface["APP_LOGO"] =  brand["Logo"]


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


language = "en"  # By default but it will be overwritten if there are other language directories on the USB


##########################################################################
#  Check mediaDirectory for at least one language directory.  If one exists, then only process language folders
##########################################################################
doesRootContainLanguage = intersection(next(os.walk(mediaDirectory))[1],languageCodes)
if (doesRootContainLanguage):
  print ("Root Directory Contains Languages so we skip all root level folders that aren't languages: " + json.dumps(doesRootContainLanguage))

##########################################################################
#  Main Loop
##########################################################################
for path,dirs,files in os.walk(mediaDirectory):
	thisDirectory = os.path.basename(os.path.normpath(path))
	print ("====================================================")
	print ("Evaluating Directory: " + thisDirectory)
	print (path,dirs,files)
	shortPath = path.replace(mediaDirectory + '/d','')
	# These next two lines ignore directories and files that start with .
	files = [f for f in files if not f[0] == '_']
	dirs[:] = [d for d in dirs if not d[0] == '_']
	files = [f for f in files if not f[0] == '.']
	dirs[:] = [d for d in dirs if not d[0] == '.']
	files.sort()

	directoryType = ''  	# Always start a directory with unknown
	skipWebPath = False;    # By default
	mp3image = ""
	faudio = False


	##########################################################################
	#  See if this directory is language folder or content
	##########################################################################

	print ('	Checking For Language Folder: '+ thisDirectory)
	try:
		if (os.path.isdir(mediaDirectory + '/' + thisDirectory) and mediaDirectory + '/' + thisDirectory == path):
			print ("	Directory is a valid language directory since it is in the root of the USB")
		else:
			fail() # This is a placeholder to trigger the try:except to have an exception that goes to except below
		print ('	Found Language: ' + json.dumps(languageCodes[thisDirectory]))
		language = thisDirectory
		directoryType = "language"
	except:
		print ('	NOT a Language: ' + thisDirectory)

	##########################################################################
	#  IF directory is not a language but we are ignoring non language root folders
	##########################################################################
	if (path == mediaDirectory and directoryType != "language" and doesRootContainLanguage):
		print ('	Skipping because directory is not a lanugage: ' + thisDirectory)
		continue;

	##########################################################################
	#  New language set up
	##########################################################################

	# See if the language already exists in the directory, if not make and populate a directory from the template
	if (not os.path.exists(contentDirectory + "/" + language)):
		print ("	Creating Directory: " + contentDirectory + "/" + language)
		shutil.copytree(templatesDirectory + '/en', contentDirectory + "/" + language)
		os.system ("chown -R www-data.www-data " + contentDirectory + "/" + language)
		# Load the main.json template and populate the mains for that language.
		f = open (templatesDirectory + "/en/data/main.json")
		mains[language] = json.load(f)

	##########################################################################
	#  See if this directory is skipped because it resides within a webPath or xml structurefor a web site content such as ./images or ./js
	##########################################################################

	for testPath in webpaths:
		if path.find(testPath) != -1:
			print ("	Skipping web path: " + path)
			skipWebPath = True
	if (skipWebPath):
		continue;

	##########################################################################
	#  If this directory contains index.html then treat as web content
	##########################################################################

	if (os.path.exists(path + "/index.html") or os.path.exists(path + "/index.htm")):
		print ("	" + path + " is HTML web content")
		# See if the language already exists in the directory, if not make and populate a directory from the template
		# Make a symlink to the file on USB to display the content
		print ("	WebPath: Writing symlink to /html folder")
		os.system ("ln -s '" + path + "' " + contentDirectory + "/" + language + "/html/")
		try:
			if (brand['makeArchive'] == True):
			  print ("	WebPath: Creating web archive zip file on USB")
			  shutil.make_archive(mediaDirectory + "/" + language + "/webarchive-" + thisDirectory, 'zip', path)
			  print ("	WebPath: Linking web archive zip")
			  os.system ('ln -s "'+ mediaDirectory + '/' + language + '/webarchive-' + thisDirectory + '.zip" "' + contentDirectory + '/' + language + '/html/' + thisDirectory + '.zip"')
		except:
			print ("	NOT making web archive according to brand.txt, makeArchive is not true");
		dirs = []
		print ("	WebPath: Set webpaths to true for this directory: " +thisDirectory)
		webpaths.append(path)
		directoryType = 'collection'

#########################################################################################################################################################################

	##########################################################################
	# If this directgory ends in .apk and  contains .xml files then it is considered like a webpath
        ##########################################################################

	print("thisDirectory: ", thisDirectory, "dirs: ", dirs)
	if thisDirectory.find(".apk") > -1:
		x = 0
		while (x <= (len(files)-1)):
			y = files[x].find(".xml")
			print("looking for .xml file in ",thisDirectory,"file is: ",files[x],"location is: ",y)
			if (y > -1):
				print("         Found XML in file, testpdir value is: ", thisDirectory, files[x])
				os.system('ln -s "' + thisDirectory + '/' + files[x] + '" "' + contentDirectory + '/' + language + '/xml/"')
				try:
					if (brand['makeArchive'] == True):
						print ("	WebPath: Creating web archive zip file on USB")
						shutil.make_archive(mediaDirectory + "/" + language + "/webarchive-" + thisDirectory, 'zip', path)
						print ("	WebPath: Linking web archive zip")
						os.system ('ln -s "'+ mediaDirectory + '/' + language + '/webarchive-' + thisDirectory + '.zip" "' + contentDirectory + '/' + language + '/xml/' + thisDirectory + '.zip"')
				except:
					print ("	NOT making web archive according to brand.txt, makeArchive is not true");
				filess ="[" + file[x] + "]"
				print ("	WebPath: Set webpaths to true for this directory: " +thisDirectory)
				webpaths.append(thisDirectory)
#				webpaths.append( dirs )
				dirs = '[' + thisDirectory + ']'
				x = 1
				directoryType = 'collection'
			else: x = x + 1

	##########################################################################
	# If this directory contains .mp3 then look for a thumbnail image
	##########################################################################
	faudio = 0
	if (directoryType != 'language')  and (directoryType  != "collection"):
		for file in files:
			x = file.find(".")
			if x > 0:
				if file[x+1:] == 'mp3':
					faudio = True
					if len(files) > 1: directoryType = 'collection'
					else: direcotryType= ""
				if ((file[x+1:]) in 'img, tif, tiff, wbmp, ico, jpg, bmp, svg, svgz, webp') and (mp3image == ""):
					mp3image = thisDirectory +'/'+ file
					print("Found image in mp3 directory: ", file)

#########################################################################################################################################################################


	##########################################################################
	#  Finish detecting directoryType (root, language, html, collection)
	##########################################################################
	if (path == mediaDirectory):
		directoryType = 'root'
	elif (directoryType == ''):
		directoryType = 'collection'

	print ("	Processing Directory: " + path)
	print ("	Processing Files According To directoryType = " + directoryType)
	print ("	--------------------------------------------------")

	# Now loop through each file
	for filename in files:
		print ("	--------------------------------------------------")
		print ("	Processing File: " + filename)

		##########################################################################
		#  Understand the  file being processed
		##########################################################################

		# Skip all files in a web path not named index.html because we just build an item for the index
		if (path in webpaths):
			if ((filename != 'index.html') and (filename != 'index.htm') and (filename.find(".xml") < 0 ) and (filename.find('.zip') < 0)):
				print ("	Webpath file " + filename + " is not index  or *.xml or path.zip so skip")
				continue

		# Get certain data about the file and path
		fullFilename = path + "/" + filename					# Example /media/usb0/content/video.mp4
		shortName = pathlib.Path(path + "/" + filename).stem			# Example  video      (ALSO, slug is a term used in the BoltCMS mediabuilder that I'm adapting here)
		relativePath = path.replace(mediaDirectory +'/','')
		slug = relativePath.replace('/','-') + '-' + os.path.basename(fullFilename).replace('.','-')			# Example  video.mp4
		extension = pathlib.Path(path + "/" + filename).suffix			# Example  .mp4

		# Ignore certain extensions
		if (extension is None or extension == ''):
			print ("		Skipping: Extension null: " + fullFilename)
			continue
		if (extension not in types):
			print ("		Skipping: Extension not supported: " , fullFilename , "extension" , (extension))
			continue

		##########################################################################
		#  Depending on collection / single.  Load default json(s)
		##########################################################################

		# Load the item template file
		if (directoryType == "collection"):
			print ("	Loading Collection and Episode JSON")
			if ('collection' not in locals() and 'collection' not in globals()):
				f = open (templatesDirectory + "/en/data/item.json");
				collection = json.load(f);
				collection["episodes"] = [];
				collection['image'] = 'blank.gif'				#default value but may be changed
			f = open (templatesDirectory + "/en/data/episode.json");
			content = json.load(f);
			content['image'] = 'blank.gif'						#default value but may be changed
		else:
			print ("	Loading Item JSON")
			f = open (templatesDirectory + "/en/data/item.json");
			content = json.load(f);
			content['image'] = 'blank.gif'						#default value but may be changed

		# Update content attributes
		content["filename"] = filename
		content["mediaType"] = types[extension]["mediaType"]
		content["slug"] = slug
		content["title"] = shortName
		##########################################################################
		#  Handle Web Content Index Page
		##########################################################################
		# For html, the slug is just the directory name
		#			the mimeType is always zip for the zip file to download
		#			the filename is always to the zip file

		if (extension == '.html'):
			print ("	Handling index.html for webpath")
			slug = os.path.basename(os.path.normpath(path))
			content["slug"] = slug
			content["mimeType"] = "application/zip"
			content["title"] = os.path.basename(os.path.normpath(path))
			content["filename"] = slug + ".zip"
			content['image'] = "www.png"
			if (directoryType == "collection"):
				collection['image'] = "www.png"

		##########################################################################
		#  Mime type determination.  Try types.json, then mimetype library
		##########################################################################

		print ("	Determining Mimetype of " + extension)
		if (content["mimeType"]):
			print ("	mimeType already determined to be " + content["mimeType"])
		elif (hasattr(types[extension],"mimeType")):
			content["mimeType"] = types[extension]["mimeType"]
			print ("	mimetypes types.json says: " + content["mimeType"])
		elif (mimetypes.guess_type(fullFilename)[0] is not None):
			content["mimeType"] = mimetypes.guess_type(fullFilename)[0]
			print ("	mimetypes modules says: " + content["mimeType"])
		else:
			content["mimeType"] = "application/octet-stream"
			print ("	Default mimetype: " + content["mimeType"])
			collection['image'] = 'apps.png'
		##########################################################################
		#  Thumbnail Management
		##########################################################################


		# If this is a video, we can probably make a thumbnail
		if ((content["mediaType"] == 'video') and (content["image"] == 'blank.gif') and (os.path.exists(mediaDirectory + "/" + language + "/.thumbnail-" + slug + ".png")) == False):
			print ("	Attempting to make a thumbnail for the video")
			os.system("ffmpeg -y -i '" + fullFilename + "' -an -ss 00:00:15 -vframes 1 '" + mediaDirectory + "/" + language + "/.thumbnail-" + slug + ".png' >/dev/null 2>&1")
			print ("	Thumbnail is created at: " + mediaDirectory + "/" + language + '/.thumbnail-' + slug + '.png') 
			if (os.path.exists(mediaDirectory + "/" + language + "/.thumbnail-" + slug + ".png")):
				content["image"] = ".thumbnail-" + slug + ".png"
				if ('collection' in locals() or 'collection' in globals()) and ((collection['image'] == 'blank.gif') or (collection ['image'] == "")): collection['image'] = './thumbnail-' + slug + ".png"
			else: content["image"] = 'video.png'
			if ('collection' in locals() or 'collection' in globals()) and ((collection['image'] == 'blank.gif') or (collection ['image'] == "")): collection['image'] = "video.png"
		# Look for thumbnail.  If there is one, use it.  If not
		print ("	Looking For Thumbnail (.thumbnail-" + content["image"] + ") in " + mediaDirectory + '/' + language)
		if ((types[extension]["mediaType"] == "image") or (mp3image != "")):
			print ("	Since item is image, thumbnail is the same image")
			if (types[extension]['mediaType'] == 'image'):
				content["image"] = filename
				os.system ('ln -s "'+ fullFilename + '" "' + contentDirectory + '/' + language + '/images/' + filename + '"')
			if ('collection' in locals() or 'collection' in globals()) and (mp3image != ""):
				mp3file =pathlib.Path(mp3image).name
				collection['image'] = mp3file
				os.system ('ln -s "'+  mediaDirectory + '/' + language + '/' +mp3image + '" "' + contentDirectory + '/' + language + '/images/' + mp3file + '"')
			elif ('collection' in locals() or 'collection' in globals()): collection['image'] = 'image.png'

		if (os.path.exists(mediaDirectory + "/" + language + "/.thumbnail-" + slug + ".png")):
			if (os.path.getsize(mediaDirectory + "/" + language + "/.thumbnail-" + slug + ".png") > 0):
				print ("	Linking Thumbnail: " + mediaDirectory + "/" + language +  "/.thumbnail-" + slug + ".png")
				os.system ('ln -s "'+ mediaDirectory + '/' + language + '/.thumbnail-' + slug + '.png" "' + contentDirectory + '/' + language + '/images/' + slug + '.png"')
				if ('collection' in locals() or 'collection' in globals()):
					if (collection['image'] == "") or (collection['image'] == 'blank.gif'): collection['image']= slug + '.png'
					print("         Linking complete for collection['image'] as: ", collection['image'])
				if content['image'] == "" or  content['image'] == 'blank.gif': content['image']= slug + '.png'
				print ("        Linnk complete for content['imamge'] as:  ",content['image'])
			else:
				print ("	Thumbnail exsists but is of zero length")
		else:
			print ("	thumbnails not found.  Using standard image")

################################################################################################################################################################################

		if ('collection' in locals() or 'collection' in globals()):
			if (content["mediaType"] in 'audio') or faudio :
				if (mp3image != ""): collection['image'] = pathlib.Path(mp3image).name
				else:  collection['image'] = 'sound.png'
				collection['mediaType'] = 'audio'
			elif (content["mediaType"] in 'zip, 7zip, rar'):  collection['image'] = 'zip.png'
			elif (content["mediaType"] in 'document, text, docx, xlsx, pptx'):  collection['image'] = 'book.png'
			elif (content['mediaType'] in 'epub'): collection ['image'] = 'epub.png'
			elif (content['mediaType'] == 'pdf') : collection['image'] = 'pdf.png'
			elif (content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jpg, bmp, svg, svgz, webp') :
				if (mp3image != ""):
					collection['image'] = pathlib.Path(mp3image).name
					print(collection['image'], "this is the name:")
					collection['mediaType'] = "audio"
				else:  collection['image'] = 'images.png'
			elif (content['mediaType'].find('application') >= 0) : collection['image'] = 'apps.png'
		else:
			print ("Skipping Collection Image Because This is Not A Collection")
			if (content["mediaType"] in 'audio'):  content['image'] = 'sound.png'
			elif (content["mediaType"] in 'zip, 7zip, rar'):  content['image'] = 'zip.png'
			elif (content["mediaType"] in 'document, text, docx, xlsx, pptx'):  content['image'] = 'book.png'
			elif (content['mediaType'] in 'epub'): content ['image'] = 'epub.png'
			elif (content['mediaType'] == 'pdf') : content['image'] = 'pdf.png'
			elif (content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jpg, bmp, svg, svgz, webp') : content['image'] = 'images.png'
			elif (content['mediaType'] == 'application') : content['image'] = 'apps.png'

################################################################################################################################################################################

		# os.system ('touch "' + mediaDirectory + '/.thumbnail-' + slug + '.png"')
		# COMMENTED OUT 20220512 because now MMI uses icons instead of images.
		# if (not content["image"]) :
		#	print ("	Writing Default Icon As Content Image")
		#	content["image"] = types[extension]["image"]

		##########################################################################
		#  Compiling Collection or Single
		##########################################################################
		if (directoryType == 'collection'):
			print ("	Adding Episode to collection.json")
			if (len(collection["episodes"]) == 0):
				collection['title'] = os.path.basename(os.path.normpath(path))
				collection['slug'] = 'collection-' + collection['title']
				collection['mediaType'] = content['mediaType']
				collection['mimeType'] = content['mimeType']
				if content["image"] == types[extension]["image"] and content["image"] != 'blank.gif':
					collection['image'] = content['image']
				elif ((content['image'] != "blank.gif") and (collection['image'] == 'blank.gif')):				#now the default on creation of collection
					collection['image'] = 'images.png'
				else:
                                        #  I have no idea when we get here or why
					print("Woops we have an unknow  image state\g\g")
					logging.info("Woops we have an uknow image state "+language+" and collection : "+collection['title'])
			elif (collection['mediaType'] == "application" and content['mediaType'] != "application"):
				print ("  Replacing collection content type with new value: " + content['mediaType']);
				collection['mediaType'] = content['mediaType']
			collection["episodes"].append(content)
			with open(contentDirectory + "/" + language + "/data/" + collection['slug'] + ".json", 'w', encoding='utf-8') as f:
				json.dump(collection, f, ensure_ascii=False, indent=4)
		else:
			print ("	Item completed.  Writing item.json")
			# Since there's no episodes, just copy content into item
			# Write the item.json
			with open(contentDirectory + "/" + language + "/data/" + slug + ".json", 'w', encoding='utf-8') as f:
				json.dump(content, f, ensure_ascii=False, indent=4)
			mains[language]["content"].append(content)

		# Make a symlink to the file on USB to display the content
		print ("	Creating symlink for the content")
		os.system ('ln -s "' + fullFilename + '" "' + contentDirectory + '/' + language + '/media/"')
		print ("	Symlink: " + contentDirectory + '/' + language + '/media/' + filename)

		print ("	COMPLETE: Based on file type " + fullFilename + " added to enhanced interface for language " + language)
		# END FILE LOOP

	# Wait to write collection to main.json until directory has been fully processed
	if (('collection' in locals() or 'collection' in globals()) and directoryType == "collection"):
		print ("	No More Episodes / Wrap up Collection for " + thisDirectory)
		# slug.json has already been saved so we don't need to do that.  Just write the collection to the main.json
		mains[language]["content"].append(collection)
		del collection
	# END DIRECTORY LOOP

##########################################################################
#  Wrap up: main.json, languages.json and interface.json
##########################################################################
print ("*************************************************")
print ("Completing Final Compilation of languages and items")

# Now go through each language that we found and processed and write the interface.json and main.json for each
languageJson = []
for language in mains:
	if (len(mains[language]["content"]) == 0):
		print ("Skipping Empty Content for language:" +language)
		if (language == 'en'):
			shutil.rmtree(contentDirectory + '/en')
		continue
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

if (len(languageJson) == 0):
	print ("No valid content found on the USB.  Exiting");
	exit(1);

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


print ("Copying Metadata to Zip File On USB");
os.system ("(cd " + contentDirectory + " && zip --symlinks -r " + zipFileName + " *)");
print ("DONE");
