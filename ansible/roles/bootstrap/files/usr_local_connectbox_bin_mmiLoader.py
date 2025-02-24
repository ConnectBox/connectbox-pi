#!/usr/bin/python3
#  Loads content from USB and creates the JSON / file structure for enhanced media interface


import json
import os
import pathlib
import shutil
import mimetypes
import logging
import time
from indexer import *
import threading

def mmiloader():

	print ("loader: Starting...")

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
	complex = 0

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
		time.sleep(2)
		os.system("rm " + comsFileName)
		exit(0)

	f = open(comsFileName, "w", encoding='utf-8')
	f.write('Indexing USB')
	f.close()
	os.system ("mkdir " + contentDirectory)
	shutil.copytree(templatesDirectory + '/en', contentDirectory + '/en')
	shutil.copy(templatesDirectory + '/footer.html', contentDirectory)
	print ("copyied templates for en and footer")

	#os.system ("chown -R www-data.www-data " + contentDirectory)   # REMOVE AFTER TEST
	#print ("finished chown of contentdirectory")

	f = open (templatesDirectory + "/en/data/main.json", "r")
	mains["en"] = json.load(f)
	f.close()
	print("main.json loaded")
	#os.system ("chmod -R 755 " + mediaDirectory)

	#print ("changed mode -R 755 of mediaDirectory")
	print ("going to get the languae codes now")

	# Retrieve languageCodes.json
	f = open(templatesDirectory + '/languageCodes.json', "r")
	languageCodes = json.load(f)
	f.close()
	print ("language codes aquired")

	# Retrieve brand.txt
	f = open('/usr/local/connectbox/brand.j2', "r")
	brand = json.load(f)
	f.close()
	print ("brand Aquired")

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
	f = open (templatesDirectory + "/en/data/interface.json", "r")   # We will always place USB content in EN language which is default
	interface = json.load(f)
	f.close()
	interface["APP_NAME"] = brand["Brand"]

	if brand["enhancedInterfaceLogo"] != "" :
	        interface["APP_LOGO"] = brand["enhancedInterfaceLogo"]
	else:
	        interface["APP_LOGO"] =  brand["Logo"]


	# Load dictionary of file types
	f = open (templatesDirectory + "/en/data/types.json", "r")
	types = json.load(f)
	f.close()
	#print (types)

	webpaths = []     # As we find web content, add here so we skip files and folders within

	# Check for empty directory and write default content if empty
	try:
		if len(os.listdir(mediaDirectory) ) == 0:
			print("Directory is empty")
			f = open(mediaDirectory + "/content/connectbox.txt", "a")
			f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
			f.close()
	except:
			print("Directory is empty")
			f = open(mediaDirectory + "/content/connectbox.txt", "a")
			f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
			f.close()

	language = "en"  # By default but it will be overwritten if there are other language directories on the USB
	directoryType = "" # By default we don't have a directory type (language, folder, folders, singular, etc.

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
		print(path)
		thisDirectory = os.path.basename(os.path.normpath(path))
		if ((thisDirectory == "content") and (mediaDirectory == path) and doesRootContainLanguage):
			continue
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
			if (os.path.isdir(mediaDirectory + '/' + thisDirectory) and ((mediaDirectory + '/' + thisDirectory) == path) and (thisDirectory in doesRootContainLanguage)):
				print ("	Directory is a valid language directory since it is in the root of the USB")
				print ('	Found Language: ' + json.dumps(languageCodes[thisDirectory]))
				language = thisDirectory
				logging.info ('Found a language directory in the root content folder ' + language + ' which is ' +  json.dumps(languageCodes[thisDirectory]))
				directoryType = "language"
				NoISOCodes = 0
				print("         this is the language: ", language)
				print("		noISOCodes is : ",NoISOCodes)
			elif os.path.isfile(mediaDirectory + "/.language"):
				print ("	Root Directory has .language file")
				file = open(mediaDirectory + "/.language")
				lineCounter = 0
				for line in file:
					lineCounter+=1
					if (lineCounter == 1):
						language = line.strip()
				if ( json.dumps(languageCodes[language])):
					print ('	Found Language: ' + language)
					logging.info ("Found a .language folder containing a valid .langage in th root contents " + language + " which is " + json.dumps(languageCodes[language]))
					directoryType = "language"
					NoISOCodes = 1
				else:
					print ("	Ok were in language folder content anad changing to language = 'en'")
					language = "en"
					directoryType = "language"
					NoISOCodes = 1
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
			f.close()

		##########################################################################
		# Check for Complex file structure with multiple directories
		##########################################################################

		try:
			complex_lst = []
			f = open("/usr/local/connectbox/complex_dir", "r", encoding="utf-8")
			complex_lst = json.load(f)
			f.close()
		except:
			complex_lst = []


		# The following code checks for dirs matching the complex_lst as well as path matching complex_lst
		print ("starting complex_lst from file is: ",complex_lst)
		y = 0
		z = 0
		while ((y < len(complex_lst)) and (directoryType == "") and (len(dirs)>1)):		#This code checks for an exsisting processed directory name in complex_lst or a subdirectory in complex_lst
			x = 0
			for dirname in dirs:
				if ((str(dirname).find(str(complex_lst[y])) >= 0) or (str(path).find(str(complex_lst[y])) >= 0)):
					if (y < (len(complex_lst)-1)):
						z += 1
						if complex_lst[y+1] == ";":
							directoryType = "folders"
						else:
							if directoryType == "" : directoryType = 'folder'
					elif directoryType == "":
						directoryType = "folder"
						z += 1
					break
				else:	x += 1
			y += 1

		if directoryType == "":							#We enter here if we don't have exsisting language, master directory or subdirectories (meaning we must have master)
											#And we havn't checked the current path,dirs,files
			x = 0
			if (((len(files) == 0) or ((len(files)==1) and (str(files).find("index.htm")>=0))) and (len(dirs) > 0)):
				print(" were starting a complex directory evaluation")  # Ok were starting up an evaluation because we have a complex directory 1st time.
				if complex_lst != []:
					complex_lst.append(path)
					complex_lst.append(";")
					directoryType = 'folders'
				else:		# This is our first fime to find the index.htm* file in a folder
					while x < len(files):	# ok we foound an index.htm* file in the current path
						if (str(files[x]).find("index.htm") >=0):
							complex_lst.append(path)    #this has a file attached which has to be index.htm
							if len(files) == 1:
								complex_lst.append(";")
								directoryType = 'folders'
							else:
								directoryType = 'folder'
							break
						else: x += 1
					if x < len(files):
						f = open("/usr/local/connectbox/complex_dir", "w", encoding='utf-8')
						json.dump(complex_lst, f)
						f.close()
						if (directoryType == ""): directoryType = 'folders'
				if x != 0:
					f = open(comsFile, "w", encoding='utf-8')
					f.write('Highly Complex' + chr(10) + 'Filesystem')
					f.close()
				f = open("/usr/local/connectbox/complex_dir", "w", encoding='utf-8')
				print("complex list is now: 2.5 ",complex_lst)
				for dir in  dirs:	# ok were going to look at the subfolders of this complex folder
					if (os.path.isdir(os.path.join(path, dir))):
						for xdir, dirnames, filenames in os.walk(os.path.join(path, dir)):
							if (((len(filenames)== 0) or ('índex.htm' in filenames)) and (len(dirnames)>0)):  # if no files but directories or index.htm* and directories this is the start of 
																	  # another complex file
								complex_lst.append(xdir)
								complex += 1	# we don't add the ";" since its not the top entry
								print ("Added directory to complex_lst: ",xdir, complex_lst)
								if directoryType == "": directoryType = 'folder'
							if str(filenames).find("index.htm")>= 0:
								print("OK we have a problem in directory: ",xdir," as it has  HTHM code and index.htm...we will overwrite")
								logging.info("OK we have a problem in directory: ",xdir," as it has  HTHM code and index.htm...we will overwrite")
					else:
						print ("help, i don't konow what to do the join e of path and dir wasn't a path")
				json.dump(complex_lst, f)
				f.close()
				if ((directoryType != 'folders') or (directoryType != 'folder')):			# if we know what we are and its in the complex_lst it not our first time here
					print("************************  Directory Commplexity is: " + str(complex)+ " ****************************")
					print("************************  we have saved out the complex_lst of ",complex_lst,"*************************")
					print("Complex_lst is now: ",complex_lst)
					os.sync()
					print("recursing mmiLoader", path, path)
					process_dir(path, path, "verbose, recursive")
					print("threading a new mmiLoader")
					t = threading.Thread(target=mmiloader())
					t.start()
					print("were exiting mmiLoader after we have threaded a new one")
					sys.exit()

			f = open(comsFileName, "w", encoding='utf-8')
			f.write('Indexing USB')
			f.close()

		###########################################################################
		# Check this path as a subpath of one main path already handled in extended
		###########################################################################
		x = 0
		y = 0
		while  x < (len(complex_lst)-2):
			if ((str(path).find(str(complex_lst[x]) >= 0)) and (complex_lst[x+1] == ';')):
				print ("This directory is a major directory  of a complex one.  skip it except for index.htm*")
				webpaths.append(path)
				break
			else:
				if (str(path).find(str(complex_lst[x])) >= 0):
					print ("this directory is a mionor subdirectory of a complex one, skip it")
					webpaths.append(path)
				else: x += 1
		if (x < len(complex_lst)):
			if (str(path).find(str(complex_lst[x])) >= 0): webpaths.append(path)


		##########################################################################
		#  If this directory contains index.html then treat as web content
		##########################################################################

		if ((os.path.isfile(path + "/index.html") or (os.path.isfile(path + "/index.htm")) or ((str(path).find('index.htm'))>= 0) and (y>0))):

			SkipArchive = 1
			print ("	" + path + " is HTML web content")
			# See if the language already exists in the directory, if not make and populate a directory from the template
			# Make a symlink to the file on USB to display the content
			print ("	WebPath: Writing symlink to /html folder")
			os.system ("ln -s '" + path + "' " + contentDirectory + "/" + language + "/html/")
			x = 0

			print("well the complex_lst is: 3", complex_lst," and length ", len(complex_lst))
#			if complex_lst != ['']:
#				while ((x < len(complex_lst)-1) and (x>=0)):
#					if (str(complex_lst[x]).find(path))>= 0:
#						print ("Found the directory tree", path)
#						if (str(complex_lst[x+1]).find(";")) >= 0:
#							print ("Found the ; indicating root")
#							directoryType = 'folders'
#							x = -1
#							continue
#						elif x>= 0:
#							directoryType = ""
#							print ("Didn't find a root direectory")
#							x += 1
#					else:
#						x = len(complex_lst)
#			else:
#				pass

			print ("directoryType: ",directoryType)
			if (not(os.path.isfile(mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))) and ('folder' in directoryType)):
				f = open(comsFileName, "w", encoding='utf-8')
				f.write('Creating ZIP'+chr(10)+"File")
				f.close()
				logging.info ("Trying to archive a web file set for " + thisDirectory)
				try:
					print ("	WebPath: Creating web archive zip file on USB for: ",path)
					shutil.make_archive(mediaDirectory +  ("/.webarchive-" + language + "-" + thisDirectory).replace('--','-'), 'zip', (path))
					print ("	WebPath: Linking web archive zip")
				except:
					print ("	Error making web archive ")
				logging.info ("succeeded in finishing the zip file")
			else:
				print(("webarchive already exsists /.webarchive-" + language + '-' + thisDirectory + ".zip").replace("--","-"))
			f = open(comsFileName, "w", encoding='utf-8')
			f.write('Indexing USB')
			f.close()
			os.system ("ln -s '"+ mediaDirectory + "/.webarchive-" + language + "-" + thisDirectory + ".zip'  '" + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'".replace("--","-"))
			dirs = []
			webpaths.append(path)
			if directoryType != 'folders':  directoryType = "html"


		print ("Directory Type is: ", directoryType)
		##########################################################################
		#  See if this directory is skipped because it resides within a webPath for a web site content such as ./images or ./js
		##########################################################################

		for testPath in webpaths:
			if ((path.find(testPath) != -1) and (not('folder' in directoryType))):
				print ("	Skipping web path: " + path)
				skipWebPath = True
			else: print (" path not found in testPath or directoryType = 'folder/s': ",path,testPath)
		if (skipWebPath):
			continue
		SkipArchive = 0		#This flag is to be used to determine if we had an index.html or index.htm or we had an AndroidManifest.xml


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
				f = open(comsFileName, "w", encoding='utf-8')
				f.write('Creating ZIP'+chr(10)+"File")
				f.close()
				logging.info ("Trying to archive an Android XML file set for " + thisDirectory)
				try:
					print ("	WebPath: Creating web archive zip file on USB at: "+ mediaDirectory + "/.webarchive-" + language + "-" + thisDirectory + ".zip")
					shutil.make_archive(mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory ).replace('--','-'), "zip", (path))
				except:
					print ("	error  making web archive")
				logging.info ("succeeded in finishing the zip file")
				f = open(comsFileName, "w", encoding='utf-8')
				f.write('Indexing USB')
				f.close()
			else: print (" Found it!!")
			print ("	WebPath: Linking web archive zip")
			os.system ("ln -s '" + mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace("--","-") + "'  '" + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'")
			dirs = []
			webpaths.append(path)
			directoryType = "html"


		#############################################################################################
		#  Finish detecting directoryType (root, language, html, img,  collection, singular, folders)
		#############################################################################################
		if ((path == mediaDirectory) and (not ('folder' in directoryType))):
			directoryType = 'root'
		elif (directoryType == '' and len(files) > 2):
			directoryType = 'collection'
		elif (directoryType == "" and len(files) <=2):
			directoryType = 'singular'
		elif (directoryType == 'folders'):
			pass
		elif (directoryType == 'folder'):
			pass
		elif (directoryType == 'language'):
			pass
		else: directoryType = 'singular'

		print ("	Processing Directory: " + path)
		print ("	Processing Files According To directoryType = " + directoryType)
		print ("	Processing Files According to language type= "+ language)
		print ("	--------------------------------------------------")



		##########################################################################
		#  If we have a .compress file in the root content folder we zip any directory with multiple items except languages.
		##########################################################################
		if (((directoryType == 'collection') or (len(files) > 1)) and (directoryType != "language") and (os.path.isfile(mediaDirectory + "/" + ".compress")) and (SkipArchive == 0)):
			print("        Looking to create a zip file of directory, thisDirectory:Looking to create a zip file of directory, thisDirectory: "+ thisDirectory, directoryType)
			# Make a symlink to the file on USB to display the content
			x = 0
			for filename in files:
				if ((pathlib.Path(path + "/" + filename).suffix).lower() in '.zip, .gzip, .zy, .gz, .gzip, .7z, .bz2, .tar'): x = 1
			if (x==0):
				print ("	Path: Writing symlink to /html folder")
				os.system ("ln -s '" + path + "' '" + contentDirectory + "/" + language + "/html/" + thisDirectory + "'")
				print ("        Path is equal to: " + path)

				if doesRootContainLanguage:
					print ("looking at: " + mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))
					if not os.path.isfile(mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-')):
						logging.info ("trying to create a zip file of " + mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")

						f = open(comsFileName, "w", encoding='utf-8')
						f.write('Creating ZIP'+chr(10)+"File")
						f.close()
						try:
							print ("	Path: Creating archive zip file on USB")
							shutil.make_archive(mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
							print ("	Path: Linking archive zip")
						except:
							print ("	error  making archive")
						os.system ('ln -s '+ mediaDirectory + "/" + language + "/" + thisDirectory +  "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
						logging.info ("succeeded in finishing the zip file")
						f = open(comsFileName, "w", encoding='utf-8')
						f.write('Indexing USB')
						f.close()
				else:
					print ("looking at: " + mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")
					if not os.path.isfile(mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip"):
						logging.info ("trying to create a zip file of " + mediaDirectory + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")
						f = open(comsFileName, "w", encoding='utf-8')
						f.write('Creating ZIP'+chr(10)+"File")
						f.close()
						try:
							print ("	Path: Creating archive zip file on USB")
							shutil.make_archive(mediaDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
							print ("	Path: Linking web archive zip")
						except:
							print ("	error  making archive")
						os.system ('ln -s '+ mediaDirectory + "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
						logging.info ("succeeded in finishing the zip file")
						f = open(comsFileName, "w", encoding='utf-8')
						f.write('Indexing USB')
						f.close()
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
			print ("	Processing according to language " + language)

			##########################################################################
			#  Understand the  file being processed
			##########################################################################

			# Skip all files in a web path not named index.html because we just build an item for the index
			if (path in webpaths and ((filename != 'index.htm') and (filename != 'index.html') and (filename != 'AndroidManifest.xml'))):
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
					f.close()
					collection["episodes"] = []
					collection['image'] = 'blank.gif'				#default value but may be changed
				f = open (templatesDirectory + "/en/data/episode.json")
				content = json.load(f)
				f.close()
				content['image'] = 'blank.gif'						#default value but may be changed
			else:    #Singular, folders, root
				print ("	Loading Item JSON")
				f = open (templatesDirectory + "/en/data/item.json")
				content = json.load(f)
				content['image'] = 'blank.gif'
				f.close()

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
				if (('.htm' in extension) and (directoryType != 'folders')): content['image'] = "www.png"
				elif (extension == '.xml'): content['image'] = "app.png"
				elif (directoryType == 'folders'):
					content['image'] = 'folders.png'
				if (directoryType == "collection"):
					if '.htm' in extension: collection['image'] = "www.png"
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
				if ('collection' in locals() or 'collection' in globals()) and collection['image'] == 'blank.gif': collection['image'] = "images.png"


			# If this is a video, we can probably make a thumbnail
			if ((content["mediaType"] == 'video') and (content["image"] == 'blank.gif')):
				print("        Were looking for .thumbnail-" + language + '-' + slug + '.png')
				try:
					if not (os.path.isfile(mediaDirectory + "/.thumbnail-" + language +  "-" + slug + ".png")):
						print ("	Attempting to make a thumbnail for the video")
						x = os.system("ffmpeg -y  -ss 15 -i '" + fullFilename + "' -an -frames:1 '" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png'  >/dev/null 2>&1")
						try:
							img = Image.open(mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png")
							clrs = img.getcolors()
							print ("Looked at colors of ffmpeg image and got: ",clrs)
							if len(clrs) == 1:
								print("Retrying the image as it was all one color")
								print("continue?")
								x = os.system("ffmpeg -y  -ss 30 -i '" + fullFilename + "' -an -frames:1 '" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png'  >/dev/null 2>&1")
						except:
							x = 1
						if x <= 0: print ("Wonderful the ffmpeg succeded and the thumbnail was created.")
						else:
							print ("The ffmpeg failed as far as we can tell.")
							content['image'] = 'video.png'
							raise
					else: print ("        We found the thumbnail")
				except:
					print ("Something whent wrong with the ffmpeg or elsewhere")
					content['image'] = 'video.png'
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
					if ('collection' in locals() or 'collection' in globals()) and (collection['image'] == 'blank.gif' or collection['image'] != 'video.png'): collection['image'] = "video.png"


			# if this is an audio file, we can probably get an image from the mp3
			if ((content["mediaType"] == 'audio') and (content["image"] == 'blank.gif')):
				print("        Were looking for " + ".thumbnail-" + language + "-" + slug + ".png")
				if not os.path.isfile( mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"):
					print ("	Attempting to make a thumbnail for the audio")
					os.system("ffmpeg -y -i '" + fullFilename + "' -an -c:v copy '" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png'  >/dev/null 2>&1")
				else: print("        We found the image so lets link it. in language" + language)
				try:
					if (os.path.getsize( mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png') > 100):
						x = os.system ('ln -s "' + mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png' + '"  "' + contentDirectory + '/' + language + '/images/.thumbnail-' + language + '-' + slug + '.png"')
						if x <= 0: print ("	Thumbnail image link complete at: " + mediaDirectory + "/.thumbnail-"+ language + "-" + slug + ".png")
						else: print ("       Thumbnail image did not get linked.... " + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png ?????? What to do????? ")
						content['image'] = ".thumbnail-"  + language + "-" + slug + ".png"
				except: content["image"] = "sound.png"
				if ('collection' in locals() or 'collection' in globals()) and (collection['image'] == 'blank.gif' or collection['image'] != "sound.png"): collection['image'] = "sound.png"

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
				elif ((content["mediaType"] in 'document, text, docx, xlsx, pptx') and (collection['image'] == 'blank.gif')):  collection['image'] = 'book.png'
				elif ((content['mediaType'] in 'epub') and (collection['image']== 'blank.gif')): collection ['image'] = 'epub.png'
				elif ((content['mediaType'] == 'pdf') and (collection['image'] == 'blank.gif')): collection['image'] = 'pdf.png'
				elif ((content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg') and (collection['image'] == 'blank.gif')): collection['image'] = 'images.png'
				elif (content['mediaType'] == 'application') :
					collection['image'] = 'apps.png'
					content['title'] = content['title'] + extension
			else:
				if (content["mediaType"] in 'audio'):  content['image'] = 'sound.png'
				elif (content["mediaType"] in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar'):  content['image'] = 'zip.png'
				elif (content["mediaType"] in 'document, text, docx, xlsx, pptx'):  content['image'] = 'book.png'
				elif (content['mediaType'] in 'epub'): content ['image'] = 'epub.png'
				elif (content['mediaType'] == 'pdf') : content['image'] = 'pdf.png'
				elif (content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg'):
					if ((content['image'] == "") or (content['image'] == 'blank.gif')):
						 content['image'] = 'images.png'
				elif (content['mediaType'] == 'application') :
					content['image'] = 'apps.png'
					content['title'] = content['title'] + extension

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
					elif ((content['image'] != "blank.gif") and (collection['image'] == 'blank.gif')):
						#now the default on creation of collection
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
				f.close()
			else:
				print ("	Item completed.  Writing item.json")
				# Since there's no episodes, just copy content into item
				# Write the item.json
				with open(contentDirectory + "/" + language + "/data/" + slug + ".json", 'w', encoding='utf-8') as f:
					json.dump(content, f, ensure_ascii=False, indent=4)
				f.close()
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

	try:
		os.system("rm /usr/local/connectbox/complex_dir")
	except:
		pass

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
		f.close()
		print ("Writing interface.json for " + language)
		with open(contentDirectory + "/" + language + "/data/interface.json", 'w', encoding='utf-8') as f:
			json.dump(interface, f, ensure_ascii=False, indent=4)
		f.close()
		# Add this language to the language interface
		languageJsonObject = {}
		languageJsonObject["codes"] = [language]
		try:
			languageJsonObject["text"] = languageCodes[language]["native"][0]
		except:
			languageJsonObject ["text"] = languageCodes[language]["english"][0]

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
	f.close()

	print ("Copying Metadata to Zip File On USB")
	os.system ("(cd " + contentDirectory + " && zip --symlinks -r " + zipFileName + " *)")
	logging.info("Finished mmiLoader.py run successfully to create the user interface and index the data contents")
	os.system("rm " + comsFileName)
	print ("DONE")
	sys.exit()


if __name__ == '__main__' :

	try:
		os.system("rm /usr/local/connectbox/complex_dir")
	except:
		pass
	mmiloader()
