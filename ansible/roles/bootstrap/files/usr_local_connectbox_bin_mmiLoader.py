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
# Handel memory issues  by setting up automated free memory
######################################################

os.system("sync && echo 3 > sudo tee /proc/sys/vm/drop_caches")

#######################################################
def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3

# Defaults for Connectbox / TheWell
mediaDirectory = "/media/usb0/content"
templatesDirectory = "/var/www/enhanced/content/www/assets/templates"
contentDirectory = "/var/www/enhanced/content/www/assets/content"
zipFileName = mediaDirectory + '/saved.zip'
comsFileName = "/usr/local/connectbox/creating_menus.txt"




# Init
mains = {}        # This object contains all the data to construct each main.json at the end.  We add as we go along
logging.info("Starting a run of mmiLoader.py to index the data contents and create the user interface")

# Clear the content directory so we replace it in whole and create the en directory for default
# Copy templates to content folder
try:
	os.system ("rm -r " + contentDirectory)
	os.system ("rm " + comsFileName)
except:
	temp = 1 # There is a directory already

os.system("touch " +  comsFileName) 

##########################################################################
#  See if this directory is language folder or content
##########################################################################
print ("	Check for saved.zip")
if (os.path.isfile(mediaDirectory + "/saved.zip")):
	print ("	Found saved.zip.  Unzipping and restoring to " + contentDirectory)
	print (" ")
	print ("****If you want to reload the USB, delete the file saved.zip from the USB drive.")
	os.system ("mkdir " + contentDirectory)
	os.system ("(cd " + contentDirectory + " && unzip " + zipFileName + ")")
	print ("DONE")
	os.system("rm " + comsFileName)
	exit(0)

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
		throw()
	print ("Custom Branding: " + brand['Brand'])
except:
	brand['Brand'] = os.popen('cat /etc/hostname').read()
try:
	if (len(brand['Logo']) < 5):
		throw()
	print ("Custom Logo: " + brand['Logo'])
except:
	brand['Logo'] = "imgs/logo.png"

print ("Building Content For " + brand['Brand'])

# Insert Brand and Logo into the interface template.  We will write this at the end to each language
f = open (templatesDirectory + "/en/data/interface.json")   # We will always place USB content in EN language which is default
interface = json.load(f)
interface["APP_NAME"] = brand["Brand"]

if brand["enhancedInterfaceLogo"] != "" :
        interface["APP_LOGO"] = brand["enhancedInterfaceLogo"]
else:
        interface["APP_LOGO"] =  brand["Logo"]


# Load dictionary of file types
f = open (templatesDirectory + "/en/data/types.json")
types = json.load(f)
#print (types)

webpaths = []     # As we find web content, add here so we skip files and folders within

# Check for empty directory and write default content if empty
if len(os.listdir(mediaDirectory) ) == 0:
	print("Directory is empty")
	f = open(mediaDirectory + "/connectbox.txt", "a")
	f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
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
	skipWebPath = False    # By default
	thisDirectory2 = thisDirectory
	x = thisDirectory2.find(" ")
	while (x>=0):
		if ((x < len(thisDirectory2)) and (x >= 0)):
			thisDirectory2 = thisDirectory2[0:x] + '\ ' + thisDirectory2[x+1:]
			x = thisDirectory2[x+2].find(" ")
		else:
			thisDirectory2 = thisDirectory.rstrip()
			x = -1

	##########################################################################
	#  See if this directory is language folder or content
	##########################################################################

	print ('	Checking For Language Folder with: '+ thisDirectory)
	try:
		if (os.path.isdir(mediaDirectory + '/' + thisDirectory) and ((mediaDirectory + '/' + thisDirectory) == path)):
			print ("	Directory is a valid language directory since it is in the root of the USB")
			print ('	Found Language: ' + json.dumps(languageCodes[thisDirectory]))
			language = thisDirectory
			logging.info ('Found a language directory in the root content folder ' + language + ' which is ' +  json.dumps(languageCodes[thisDirectory]))
			directoryType = "language"
		elif os.path.isfile(mediaDirectory + "/.language"):
			print ("	Root Directory has .language file")
			file = open(mediaDirectory + "/.language")
			lineCounter = 0
			for line in file:
				lineCounter+=1
				if (lineCounter == 1):
					language = line.strip()
			print ('	Found Language: ' + language)
			logging.info ("Found a .language folder containing a valid .langage in th root contents " + language + " which is " + json.dumps(languageCodes[language]))
			directoryType = "language"
		else:
			fail() # This is a placeholder to trigger the try:except to have an exception that goes to except below
	except:
		print ('	NOT a Language: ' + thisDirectory)

	##########################################################################
	#  IF directory is not a language but we are ignoring non language root folders
	##########################################################################
	if (path == mediaDirectory and directoryType != "language" and doesRootContainLanguage):
		print ('	Skipping because directory is not a lanugage: ' + thisDirectory)
		continue

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
	#  See if this directory is skipped because it resides within a webPath for a web site content such as ./images or ./js
	##########################################################################

	for testPath in webpaths:
		if path.find(testPath) != -1:
			print ("	Skipping web path: " + path)
			skipWebPath = True
	if (skipWebPath):
		continue
	SkipArchive = 0		#This flag is to be used to determine if we had an index.html or index.htm or we had an AndroidManifest.xml

	##########################################################################
	#  If this directory contains index.html then treat as web content
	##########################################################################

	if (os.path.isfile(path + "/index.html") or os.path.isfile(path + "/index.htm")):
		SkipArchive = 1
		print ("	" + path + " is HTML web content")
		# See if the language already exists in the directory, if not make and populate a directory from the template
		# Make a symlink to the file on USB to display the content
		print ("	WebPath: Writing symlink to /html folder")
		os.system ("ln -s '" + path + "' " + contentDirectory + "/" + language + "/html/")
		print("Path is: " + path)
		print("looking for " + mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))
		if not os.path.isfile(mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-')):
			logging.info ("Trying to archive a web file set for " + thisDirectory)
			try:
				print ("	WebPath: Creating web archive zip file on USB")
				shutil.make_archive(mediaDirectory +  ("/.webarchive-" + language + "-" + thisDirectory).replace('--','-'), 'zip', (mediaDirectory))
				print ("	WebPath: Linking web archive zip")
			except:
				print ("	Error making web archive ")
			logging.info ("succeeded in finishing the zip file")
		os.system ("ln -s '"+ mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip'  '").replace('--','-') + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'")
		dirs = []
		webpaths.append(path)
		directoryType = "html"

	##########################################################################
	#  If this directory contains AndroidManifest.xml then treat as Android App
	##########################################################################

	if (os.path.isfile(path + "/AndroidManifest.xml")):
		SkipArchive = 1
		print ("	" + path + " is Android App")
		# See if the language already exists in the directory, if not make and populate a directory from the template
		# Make a symlink to the file on USB to display the content
		print ("	WebPath: Writing symlink to /html folder")
		os.system ("ln -s '" + path + "'  " + contentDirectory + "/" + language + "/html/")
		print ("    Path is equal to: " + path)
		print("    Looking for: " + mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))
		if (not os.path.isfile(mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))):
			logging.info ("Trying to archive an Android XML file set for " + thisDirectory)
			try:
				print ("	WebPath: Creating web archive zip file on USB at: "+ mediaDirectory + "/.webarchive-" + language + "-" + thisDirectory + ".zip")
				shutil.make_archive(mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory ).replace('--','-'), "zip",mediaDirectory)
			except:
				print ("	error  making web archive")
			logging.info ("succeeded in finishing the zip file")
		else: print (" Found it!!")
		print ("	WebPath: Linking web archive zip")
		os.system ("ln -s '" + mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace("--","-") + "'  '" + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'")
		dirs = []
		webpaths.append(path)
		directoryType = "html"


	##########################################################################
	#  Finish detecting directoryType (root, language, html, img,  collection)
	##########################################################################
	if (path == mediaDirectory):
		directoryType = 'root'
	elif (directoryType == ''):
		directoryType = 'collection'


	print ("	Processing Directory: " + path)
	print ("	Processing Files According To directoryType = " + directoryType)
	print ("	--------------------------------------------------")



	##########################################################################
	#  If we have a .compress file in the root content folder we zip any directory with multiple items except languages.
	##########################################################################
	if (((directoryType == 'collection') or (len(files) > 1)) and (directoryType != "language") and (os.path.isfile(mediaDirectory + "/" + ".compress")) and (SkipArchive == 0)):
		print("        Looking to create a zip file of directory, thisDirectory: "+ thisDirectory)
		# Make a symlink to the file on USB to display the content
		x = 0
		for filename in files:
			if ((pathlib.Path(path + "/" + filename).suffix).lower() in '.zip, .gzip, .zy, .gz, .gzip, .7z, .bz2, .tar'): x = 1
		if (x==0):
			print ("	Path: Writing symlink to /html folder")
			os.system ("ln -s '" + path + "' '" + contentDirectory + "/" + language + "/zip/" + thisDirectory + "'")
			print ("        Path is equal to: " + path)

			if doesRootContainLanguage:
				print ("looking at: " + mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))
				if not os.path.isfile(mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-')):
					logging.info ("trying to create a zip file of " + mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")
					try:
						print ("	Path: Creating archive zip file on USB")
						shutil.make_archive(mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
						print ("	Path: Linking archive zip")
					except:
						print ("	error  making archive")
					os.system ('ln -s '+ mediaDirectory + "/" + language + "/" + thisDirectory +  "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
					logging.info ("succeeded in finishing the zip file")
			else:
				print ("looking at: " + mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")
				if not os.path.isfile(mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip"):
					logging.info ("trying to create a zip file of " + mediaDirectory + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")
					try:
						print ("	Path: Creating archive zip file on USB")
						shutil.make_archive(mediaDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
						print ("	Path: Linking web archive zip")
					except:
						print ("	error  making archive")
					os.system ('ln -s '+ mediaDirectory + "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
					logging.info ("succeeded in finishing the zip file")
			if (str(files).find("archive-" + language + "-" + thisDirectory + '.zip') < 0): files.append( "archive-" + language + "-" + thisDirectory + '.zip')
		else:
			print("files in directory contain .zip extensions Ignoring data compresssion request.")
			logging.info("Directory: " + mediaDirectory + " contains a Compressed file so we won't try to zip it for easy download") 
	###########################################################################
	# Loop through each file in this directory
	##########################################################################

	for filename in files:
		print ("	--------------------------------------------------")
		print ("	Processing File: " + filename)

		##########################################################################
		#  Understand the  file being processed
		##########################################################################

		# Skip all files in a web path not named index.html because we just build an item for the index
		if (path in webpaths and ((filename != 'index.htm') and (filename != 'index.html')  and (filename != 'AndroidManifest.xml'))):
			print ("	Webpath file " + filename + " is not index or AndrodManifest so skip")
			continue

		# Get certain data about the file and path
		fullFilename = path + "/" + filename							# Example /media/usb0/content/video.mp4
		shortName = pathlib.Path(path + "/" + filename).stem					# Example  video      (ALSO, slug is a term used in the BoltCMS mediabuilder that I'm adapting here)
		relativePath = path.replace(mediaDirectory +'/','')
		slug = (os.path.basename(fullFilename).replace('.','-')).replace('--','-')		# Example  video.mp4
		extension = (pathlib.Path(path + "/" + filename).suffix).lower()			# Example  .mp4
		print(" Slug is now: "+slug)

		# Ignore certain extensions
		if (extension is None or extension == ''):
			print ("		Skipping: Extension null: " + fullFilename)
			continue
		if (extension not in types):
			print ("		Skipping: Extension not supported: " + fullFilename)
			continue

		##########################################################################
		#  Depending on collection / single.  Load default json(s)
		##########################################################################

		# Load the item template file
		if (directoryType == "collection"):
			print ("	Loading Collection and Episode JSON")
			if ('collection' not in locals() and 'collection' not in globals()):
				f = open (templatesDirectory + "/en/data/item.json")
				collection = json.load(f)
				collection["episodes"] = []
				collection['image'] = 'blank.gif'				#default value but may be changed
			f = open (templatesDirectory + "/en/data/episode.json")
			content = json.load(f)
			content['image'] = 'blank.gif'						#default value but may be changed
		else:
			print ("	Loading Item JSON")
			f = open (templatesDirectory + "/en/data/item.json")
			content = json.load(f)
			content['image'] = 'blank.gif'

		# Update content attributes
		if (filename != 'AndroidManifest.xml'): content["filename"] = filename
		else: content["filename"] = thisDirectory
		content["mediaType"] = types[extension]["mediaType"]
		content["slug"] = slug
		content["title"] = shortName
		content["mimeType"] = types[extension]["mediaType"]

		##########################################################################
		#  Handle Web Content Index Page
		##########################################################################
		# For html, the slug is just the directory name
		#			the mimeType is always zip for the zip file to download
		#			the filename is always to the zip file

		if ('.htm' in extension) or (extension == ".xml"):
			print ("	Handling index.html/AndroidManifest.xml  for webpath")
			slug = os.path.basename(os.path.normpath(path))
			content["slug"] = slug
			content["mimeType"] = "application/zip"
			content["title"] = os.path.basename(os.path.normpath(path))
			content["filename"] = slug + ".zip"
			if ('.htm' in extension): content['image'] = "www.png"
			elif (extension== '.xml'): content['image'] = "app.png"
			if (directoryType == "collection"):
				if extension == '.html': collection['image'] = "www.png"
				else: collection['image'] = "app.png"

		##########################################################################
		#  Mime type determination.  Try types.json, then mimetype library4
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

		print("        Media Type is: "+ content["mediaType"])

		##########################################################################
		#  Thumbnail Management
		##########################################################################

		# if this is an image, we use the image as the thumbnail
		if ((content["mimeType"] == "image") and (content["image"] == 'blank.gif')):
			print ("	Since item is image, thumbnail is the same image")
			content["image"] = filename
			print ("        Slug is: " + slug)
			if ('collection' in locals() or 'collection' in globals()):
				if ((mediaDirectory + thisDirectory) == path):			#This means were a root directory and file
					if (collection['image'] == 'blank.gif'): collection['image'] = slug
				elif (collection['image'] == 'blank.gif'): collection['image'] = 'images.png'
			try:
				if os.path.getsize(path + "/" + filename) > 100:				#image is large enough to be usable.
					x = os.system ("ln -s '" + path + "/" + filename + "'  '" + contentDirectory + "/" + language + "/images/" + filename + "'")
					if x <= 0: print ("	Thumbnail image was linked  at: " + content["image"] + " and now linked in the image directory")
					else: print("        Thumbnail image was not linked... " + content["image"] + " so what to do now?????")
				else:
					print (str(os.path.getsize(path + "/" + filename)) + " is the size we got for the image " + path + "/" + filename)
			except: print (" Ok we had an error tryuging to ge the size of " + path + "/" + filename)

		# If this is a video, we can probably make a thumbnail
		if ((content["mediaType"] == 'video') and (content["image"] == 'blank.gif')):
			print("        Were looking for .thumbnail-" + language + '-' + slug + '.png')
			try:
				if not (os.path.isfile(mediaDirectory + "/.thumbnail-" + language +  "-" + slug + ".png")):
					print ("	Attempting to make a thumbnail for the video")
					x = os.system("ffmpeg -y -i '" + fullFilename + "' -an -ss 00:00:15 -vframes 1 '" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png'  >/dev/null 2>&1")
					if x <= 0: print ("Wonderful the ffmpeg succeded and the thumbnail was created.")
					else:
						print ("The ffmpeg failed as far as we can tell.")
						content['image'] = 'blank.gif'
						raise
				else: print ("        We found the thumbnail")
			except:
				print ("Something whent wrong with the ffmpeg or elsewhere")
				content['image'] = 'blank.gif'
			else:
				try:
					if os.path.getsize( mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png") > 100:		#image is large enough to be usable.
						x = os.system ('ln -s "' + mediaDirectory +  '/.thumbnail-' + language + '-' + slug + '.png' + '"  "' + contentDirectory + '/' + language + '/images/.thumbnail-' + language + '-' + slug + '.png"')
						if x <= 0:
							print ("	Thumbnail image link complete at: " + mediaDirectory + "/.thumbnail-" + language + "-" +  slug + ".png")	
							content["image"] =  ".thumbnail-" + language + "-" + slug + ".png"
						else: print ("        Thumbnail link creation failed....")
					else: print ("        Image was too small to use!!!!!!!")
				except: print ("had an error getting size of video !!!!!!!!" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png")


		# if this is an audio file, we can probably get an image from the mp3
		if ((content["mediaType"] == 'audio') and (content["image"] == 'blank.gif')):
			print("        Were looking for " + ".thumbnail-" + language + "-" + slug + ".png")
			if not os.path.isfile( mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"):
				print ("	Attempting to make a thumbnail for the audio")
				os.system("ffmpeg -y -i '" + fullFilename + "' -an -c:v copy '" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png'  >/dev/null 2>&1")
			else: print("        We found the image so lets link it.")
			try:
				if (os.path.getsize( mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png') > 100):
					x = os.system ('ln -s "' + mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png' + '"  "' + contentDirectory + '/' + language + '/images/.thumbnail-' + language + '-' + slug + '.png"')
					if x <= 0: print ("	Thumbnail image link complete at: " + mediaDirectory + "/.thumbnail-"+ language + "-" + slug + ".png")
					else: print ("       Thumbnail image did not get linked.... " + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png ?????? What to do????? ")
					content['image'] = ".thumbnail-"  + language + "-" + slug + ".png"
			except: content["image"] = "blank.gif"
			if ('collection' in locals() or 'collection' in globals()) and collection['image'] == 'blank.gif': collection['image'] = "sound.png"

		# Look for user generateed  thumbnail.  If there is one, use it.
		if ((content["image"] == 'blank.gif') and (os.path.isfile(mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"))):
			print ("	Found Thumbnail" +  mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png")
			content["image"] = ".thumbnail-" + language + "-" + slug + ".png"
			os.system ('ln -s "'+ mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png"' + '"  "' + contentDirectory + '/' + language + '/images/.thumbnail-' + language + '-' + slug + '.png"')
			print ("	Thumbnail link complete at: " + mediaDirectory + "/" +  content["image"])


		##########################################################################
		# Done with thumbnail creation and linkage
		##########################################################################

		if ('collection' in locals() or 'collection' in globals()):
			if (content["mediaType"] in 'audio'):  collection['image'] = 'sound.png'
			elif ((content["mediaType"] in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar') and (collection['image'] == 'blank.gif')):  collection['image'] = 'zip.png'
			elif (content["mediaType"] in 'document, text, docx, xlsx, pptx'):  collection['image'] = 'book.png'
			elif (content['mediaType'] in 'epub'): collection ['image'] = 'epub.png'
			elif (content['mediaType'] == 'pdf'): collection['image'] = 'pdf.png'
			elif ((content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg') and (collection['image'] == 'blank.gif')): collection['image'] = 'images.png'
			elif (content['mediaType'] == 'application') : collection['image'] = 'apps.png'
		else:
			if (content["mediaType"] in 'audio'):  content['image'] = 'sound.png'
			elif (content["mediaType"] in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar'):  content['image'] = 'zip.png'
			elif (content["mediaType"] in 'document, text, docx, xlsx, pptx'):  content['image'] = 'book.png'
			elif (content['mediaType'] in 'epub'): content ['image'] = 'epub.png'
			elif (content['mediaType'] == 'pdf') : content['image'] = 'pdf.png'
			elif (content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg'):
				if ((content['image'] == "") or (content['image'] == 'blank.gif')):
					 content['image'] = 'images.png'
			elif (content['mediaType'] == 'application') : content['image'] = 'apps.png'

#		########################################################################
#		# check image for size and if 0 then use blank
#		########################################################################
#		try:
#			if ((content['image'] != 'blank.gif') and (content['image'] != '')):
#				if (os.path.getsize(contentDirectory + '/' + language + '/images/' + content['image']) < 100 ):
#					content['image'] = 'blank.gif'
#		except:	content['image'] = 'blank.gif'
#		try:
#			if ('collection' in locals() or 'collection' in globals()):
#				if ((collection['image'] != 'blank.gif') and (os.path.getsize(contentDirectory + '/' + language + '/images/' + collection['image']) < 100)):
#					collection['image'] = 'blank.gif'
#		except: collection['image'] = 'blank.gif'
#


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
				if content["image"] == types[extension]["image"]:
					collection['image'] = content['image']
				elif ((content['image'] != "blank.gif") and (collection['image'] == 'blank.gif')):				#now the default on creation of collection
					collection['image'] = 'images.png'
				else:
                                        # We got here because its not an image or the image is balank and the collection image is blank
					print("We have a blank  image state! "+content["image"])
					logging.info("We have a blank image state "+language+" and collection : "+collection['title'])
			elif (collection['mediaType'] == "application" and content['mediaType'] != "application"):
				print ("  Replacing collection content type with new value: " + content['mediaType'])
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
	print ("No valid content found on the USB.  Exiting")
	os.system("rm " + comsFileName)
	exit(1)
	
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


print ("Copying Metadata to Zip File On USB")
os.system ("(cd " + contentDirectory + " && zip --symlinks -r " + zipFileName + " *)")
logging.info("Finished mmiLoader.py run successfully to create the user interface and index the data contents")
os.system("rm " + comsFileName)
print ("DONE")
