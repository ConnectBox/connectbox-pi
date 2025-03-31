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
#import ffmpeg

def mmiloader_code():


	#######################################################
	def intersection(lst1, lst2):
	    lst3 = [value for value in lst1 if value in lst2]
	    return lst3
	######################################################



	# Defaults for Connectbox / TheWell
	mediaDirectory = "/media/usb0/content"									#The root of data
	templatesDirectory = "/var/www/enhanced/content/www/assets/templates"					#Where we get our structures for data
	contentDirectory = "/var/www/enhanced/content/www/assets/content"					#Where we store our content information data
	zipFileName = mediaDirectory + '/saved.zip'								#Saved quick load file of index data
	comsFileName = "/tmp/creating_menus.txt"								#Creating index of menu's file ocation
	complex_dir = "/tmp/Complex_lst"									#File we save complex directories in temporarily
	complex_lst = []											#List of complex directgories we find
	SkipArchive = 0  											#Flag to skip archiving if we have already done so or have zip file

	# Init

	print ("loader: Starting...")

	mimetypes.init()

	#######################################################
	# Handel memory issues  by setting up automated free memory
	######################################################

	os.system("sync && echo 3 > sudo tee /proc/sys/vm/drop_caches")						#Try to clear any cach data that we have to maximize memory availability


	mains = {}        # This object contains all the data to construct each main.json at the end.  We add as we go along
	logging.info("Starting a run of mmiLoader.py to index the data contents and create the user interface")
	complex = 0 															#Cpunter of complex file directories we have (top directories)

	# Clear the comsFileName directory so we dont have a screen on

	try:
		os.remove(comsFileName)										#Always starat with display off, no leftover elements
	except:
		pass

	try:
		f = open(comsFileName, "w", encoding='utf-8')								#Start display showing were going to do indexxing of data
		f.write('Indexing USB')
		f.close()
	except:
		pass

	try:
		os.system("rm -r " + contentDirectory)								#Get rid of any old content data structures we may have
	except:
		pass

	##########################################################################
	#  See if  we have a saved.zip file to unzip and exit
	##########################################################################

	print ("	Check for saved.zip")
	if (os.path.isfile(mediaDirectory + "/saved.zip")):							#Check for a quick index file for creating the data structures.
		print ("	Found saved.zip.  Unzipping and restoring to " + contentDirectory)
		print (" ")
		print ("****If you want to reload the USB, delete the file saved.zip from the USB drive.")

		os.mkdir(contentDirectory, mode=0o755)
		os.system ("(cd " + contentDirectory + " && unzip " + zipFileName + ")")
		print ("DONE")
		time.sleep(3)
		try:
			x = os.system("rm " + comsFileName)
			x = os.waitstatus_to_exitcode(x)
			while x!=0:
				x = os.system("rm " + comsFileName)
				x = os.waitstatus_to_exitcode(x)
				time.sleep(1)
		except:
			pass											#Clear the display
		exit(0)												#We finished up with restoring the data for this USB stick. exit the app.

	##########################################################################
	# See if this directory is language folder or content
	##########################################################################

	print ("Creating content Directory")
	try:
		f = open(comsFileName, "w", encoding='utf-8')
		f.write('Indexing USB')											#We didn't have a valid saved.zip file so we have to create all the data
		f.close()
	except:
		pass	
	try:
		os.mkdir(contentDirectory, mode=0o755)								#Create a new content directory to store our data in
	except:
		os.system("rm -r " + contentDirectory)
		os.mkdir(contentDirectory, mode=0o755)

	print ("Copying the templates to the main contentDirectory")
	shutil.copytree(templatesDirectory + '/en', contentDirectory + '/en')					#Copy the templates to an /en language file for starters.
	shutil.copy(templatesDirectory + '/footer.html', contentDirectory)					#Get the html footer
	print ("copyied templates for en and footer")


	f = open (templatesDirectory + "/en/data/main.json", "r")						#Get the main data structure
	mains["en"] = json.load(f)										#load it for /en language
	f.close()
	print ("main.json loaded, now changing modes of files in mediaDirectory") 				#Save it off
	os.system("chmod -R 755 " + mediaDirectory)

	print ("going to get the language codes now")

	# Retrieve language codes
	f = open(templatesDirectory + '/languageCodes.json', "r")						#Get the master language list
	languageCodes = json.load(f)
	f.close()
	print ("language codes loaded")


	# Retrieve brand.txt
	f = open('/usr/local/connectbox/brand.j2', "r")								#Get the current brand information
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
		brand['Brand'] = os.popen('cat /etc/hostname').read()						#Get the current host name
	try:
		if (len(brand['Logo']) < 5):									#Get the current brand logo
			throw()
		print ("Custom Logo: " + brand['Logo'])
	except:
		brand['Logo'] = "imgs/logo.png"									#set default logo if no custom

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
	print ("Brand applied")

	# Load dictionary of file types
	f = open (templatesDirectory + "/en/data/types.json", "r")						#Get the file types/mime types information
	types = json.load(f)
	f.close()
	print ("file types-mime types loaded")


	webpaths = []     # As we find web content, add here so we skip files and folders within

	# Check for empty directory and write default content if empty
	try:
		if len(os.listdir(mediaDirectory) ) == 0:
			print("Directory is empty")								#If the main directory has no data create one file to iindex
			f = open(mediaDirectory + "/connectbox.txt", "a")
			f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
			f.close()
	except:
			print("Directory is empty")								#Do the same as above for errors
			os.system("mkdir " + mediaDirectory)
			f = open(mediaDirectory + "/connectbox.txt", "w")
			f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
			f.close()

	language = "en"  # By default but it will be overwritten if there are other language directories on the USB
	directoryType = "" # By default we don't have a directory type (language, folder, folders, singular, etc.


	print("Check mediaDirectory for at least one language")


	##########################################################################
	#  Check mediaDirectory for at least one language directory.  If one exists, then only process language folders
	##########################################################################

	doesRootContainLanguage = (next(os.walk(mediaDirectory))[1])
	y = 0
	while ((y < len(doesRootContainLanguage) and (len(doesRootContainLanguage) > 0))):
		lang = doesRootContainLanguage[y]
		print ("lang is now: "+lang)
		try:
			print ("lang is: ",languageCodes[lang]['english'])

			if len(lang) > 3: 								#Were making hard spaces on the proported language
				print("checking language " + lang + " is NOT a valid language and will be removed from the list")
				doesRootContainLanguage.remove(lang)
				if y > 0: y -= 1

			elif (languageCodes[lang]):
				print("checking language " + lang + " as a valide language",languageCodes[lang])
				y +=1
				pass

			else:
				print ("We don't know what happened but well remove " + lang + " from the language list")
				doesRootContainLanguage.remove(lang)
				if y > 0: y -= 1
		except:
			doesRootContainLanguage.remove(lang)
			if y > 0: y -= 1
			print ("We just removed " + lang + " from doesRootContainLanguage, language not found!")
			logging.info("We just removed " + lang + " from doesRootContainLanguage, language not found!")

		if y > len(doesRootContainLanguage):
			y = y-1

	print("doesRootContainLanguage is now: ",doesRootContainLanguage)
	if len(doesRootContainLanguage)>0:
	  	print ("Root Directory Contains Languages so we skip all root level folders that aren't languages: " + json.dumps(doesRootContainLanguage))


	if os.path.isfile(os.path.join(mediaDirectory, ".indexed.idx")): indexed_before = True
	else: indexed_before = False


	print("validate language directories and/or look for .language file")
	####################################################################################################
	# We are going to check for file forced language .language then we'll chekc for extended directories
	####################################################################################################
	for path,dirs,files in os.walk(mediaDirectory):								# Walk all files/directories on the data set

		thisDirectory = os.path.basename(os.path.normpath(path))
		if ((thisDirectory == "content") and (mediaDirectory == path)):
			continue

		files = [f for f in files if not f[0] == '_']							#normalize files
		dirs[:] = [d for d in dirs if not d[0] == '_']							#normalize directories
		files = [f for f in files if not f[0] == '.']
		dirs[:] = [d for d in dirs if not d[0] == '.']


#		print ("Working on " + mediaDirectory + "/" + thisDirectory + " Path is: " + path)

		try:												#Check for languages by ISO codes in the root directory
			if (((mediaDirectory + '/' + thisDirectory) == path) and (thisDirectory in doesRootContainLanguage)):
				print ('	Found Language in doesRootContainLanguage ')
				language = thisDirectory
#				logging.info ('Found a language directory in the root content folder ' + language + ' which is ' +  json.dumps(languageCodes[thisDirectory]))
				NoISOCodes = 0
				directoryType = 'language'
				print("        Found language: ", thisDirectory)
				continue									#The base is a language so this is not complex directory as its a lanaguage folder.

			elif ((mediaDirectory + "/" + thisDirectory) == path) and (language == "en"):
				if os.path.isfile(mediaDirectory + "/.language"):				#We dont' have a directory with a language name so see if we have a default language file
					print ("	Root Directory has .language file")
					file = open(mediaDirectory + "/.language")
					lineCounter = 0
					for line in file:
						lineCounter+=1
						if (lineCounter == 1):
							language = line.strip()
					if ( json.dumps(languageCodes[language])):
						print ('	Found Language: ' + language)
						logging.info ("Found a .language folder containing a valid .language in th root contents " + language + " which is " + json.dumps(languageCodes[language]))
						directoryType = "language"
						NoISOCodes = 1
						if len(doesRootContainLanguage)>0:
							print ("Ok were sticking to a single language based on .language file of "+language)
							doesRootContainLanguage = []
						break
				else:										#Ok we don't have a valid language in the language file so we default to /en
#					print ("	Ok were in language folder content anad changing to language = 'en'")
					language = "en"
					directoryType = ""
					NoISOCodes = 1

			else:
#				print("we didn't find the language")
				directoryType = ""
				continue
		except:
			if os.path.isfile(mediaDirectory + "/.language"):
				print ("	Root Directory has .language file")
				file = open(mediaDirectory + "/.language")
				lineCounter = 0
				for line in file:
					lineCounter+=1
					if (lineCounter == 1):
						language = line.strip()
				if ( json.dumps(languageCodes[language])):
					print ('	Found Language: ' + language)
					logging.info ("Found a .language folder containing a valid .language in th root contents " + language + " which is " + json.dumps(languageCodes[language]))
					directoryType = "language"
					NoISOCodes = 1
					if len(doesRootContainLanguage)>0:
						print ("Ok were sticking to a single language based on .language file of "+language)
						doesRootContainLanguage = []
					break
			elif language == "en":
				directoryType = ""								#No language so we go on to check for complex structures.
				if (((mediaDirectory + "/" + thisDirectory) == path) and (len(doesRootContainLanguage) >0)):
					if thisDirectory in doesRootContainLanguage:
						doesRootContainLanguage.remove(thisDirectory)
					if len(doesRootContainLanguage)>0:
						continue        						#Skip this non language directory
			else:
				pass										# We will process this directory as its either non root or no languages in root.


		print ("** finished on the languages check, now looking at extended directories **")

		##########################################################################
		# Check for Complex file structure with multiple directories
		##########################################################################


		# The following code checks for dirs matching the complex_lst

		x = 0 													#Complex_lst index
		z = 0		  											#Flag for forcing quick continue
		match = ""
		while ((x < len(complex_lst)) and (len(dirs)>1) and (directoryType != 'language') and (z == 0)):	#This directories with no files
			if ((str(path).find(str(complex_lst[x])) >=0)):
				match = path										#This path is in the list of complex_directories
				z = 1											#This is our continue flag for the outer loop
				break											#Stop this while loop
			else:
				x +=1											#Lets see if there are more to check
		if ((match == "") and (directoryType != "language") and (z == 0)):					#This path is not in the complex_lst
			if ((len(dirs) > 0) and (len(files) <= 2) and (mediaDirectory + '/' + thisDirectory) == path):	#Ok we may have a root directory extended path
				if ("index.html" in files):
					print("FOUND MY INDEX.HTML FILE")
					print("since this is root directory starting path it needs to go in the complex list")
					complex_lst.append(path)
					try:
						f = open(comsFileName, "w", encoding='utf-8')					#ndicate were dealing with complex directories
						f.write('Highly Complex' + chr(10) + 'Filesystem')
						f.close()
					except:
						pass
					print("Added complex root directory "+str(path))
					### We leave math alogne and z alone ###
					#This is our continue flag for the outer loop
			else:
				for d in dirs:										#Now lets check the directories under the path
					for pathname, dirname, filename in os.walk(os.path.join(path,d)):
						if ((len(dirname) > 0) and (len(filename) <= 2)):			#This looks like a complex directory we need to add to the list
							if ('index.html' in filename) and (len(filename == 1)):
								print("FOUND MY INDEX/HTML FILE")
								pass
							elif ('Start_Here.htm' in filenames):
								pass
							else:
								continue
						else: continue								# We don't have the right files in the directory so its not a viable complex struture

						print("ÖK we found a starting path tha needs to go into the complex list")
						complex_lst.append(path)						#While the subdirectory is complex this shows the path is also.
						try:
							f = open(comsFileName, "w", encoding='utf-8')				#ndicate were dealing with complex directories
							f.write('Highly Complex' + chr(10) + 'Filesystem')
							f.close()
						except:
							pass

						print("Added complex root directory "+str(path))
						z = 1									#This is our continue flag for the outer loop
						break

	if len(complex_lst)>0:											#If we have complex directories then lets save the list off
		f = open(complex_dir, "w", encoding='utf-8')
		json.dump(complex_lst, f)
		f.close()

	print("We have a total of " + str(len(complex_lst)) + " complex directories heads to process")

	##################################################################################################
	# This is where we process complex directories into HTML file directories
	##################################################################################################

	for path in complex_lst:										#Now we have a full list of complex directories
		process_dir(path, path, "recursive", indexed_before )						#process the complex directory into HTML code

	print("Finished the complex directory recursion")
	if len(complex_lst)>0: os.system("touch " + (os.path.join(mediaDirectory, ".indexed.idx")))		#Write the file that says we have done the indexing at least once.

	try:
		f = open(comsFileName, "w", encoding='utf-8')								#now that were done lets go back to our general indexing status on the screen
		f.write("Indexing USB")
		f.close()
	except:
		pass

	##########################################################################
	#  Main Loop content loop
	##########################################################################
	for path,dirs,files in os.walk(mediaDirectory):								#This is our main content analysis loop now for data

		thisDirectory = os.path.basename(os.path.normpath(path))
		print ("====================================================")
		print ("Evaluating Directory: " + thisDirectory)

		shortPath = path.replace(mediaDirectory + '/d','')
		# These next two lines ignore directories and files that start with .
		files = [f for f in files if not f[0] == '_']							#Normalize files again
		dirs[:] = [d for d in dirs if not d[0] == '_']							#Normalize directories again
		files = [f for f in files if not f[0] == '.']
		dirs[:] = [d for d in dirs if not d[0] == '.']
		files.sort()											#Sort files

		directoryType = ''  	# Always start a directory with unknown
		skipWebPath = False    # By Defaults								#Flag to indicate skippiing of web paths



		##########################################################################
		#  See if this directory is language folder or content
		##########################################################################

#		print ('	Checking For Language Folder with: '+ thisDirectory)
		try:
			if (os.path.isdir(mediaDirectory + '/' + thisDirectory) and ((mediaDirectory + '/' + thisDirectory) == path) and (thisDirectory in doesRootContainLanguage)):
				print ("	Directory is a valid language directory since it is in the root of the USB, "+thisDirectory)
#				print ('	Found Language: ' + json.dumps(languageCodes[thisDirectory]))
				language = thisDirectory
#				logging.info ('Found a language directory in the root content folder ' + language + ' which is ' +  json.dumps(languageCodes[thisDirectory]))
				directoryType = "language"
				NoISOCodes = 0
#				print("         this is the language: ", language)				#We have found a language and set the directoryType

		except:												#We had an error so we jsut use the /en we setup before
#			print ('	NOT a Language: ' + thisDirectory)
			pass

		##########################################################################
		#  IF directory is not a language but we are ignoring non language root folders
		##########################################################################

		if (path == mediaDirectory and directoryType != "language" and doesRootContainLanguage):
			print ('	Skipping because directory is not a lanugage: ' + thisDirectory)
			continue  										#Skip any directory without a language ISO code that is in root with other language directories

		##########################################################################
		#  New language set up
		##########################################################################

		# See if the language already exists in the directory, if not make and populate a directory from the template
		if (not os.path.exists(contentDirectory + "/" + language)):   					#If this language already exsists skip creating it.
			print("Doing new language setup " + language + " **********************************")
			print ("	Creating Directory: " + contentDirectory + "/" + language)
			shutil.copytree(templatesDirectory + '/en', contentDirectory + "/" + language)
			os.system ("chown -R www-data.www-data " + contentDirectory + "/" + language)
			# Load the main.json template and populate the mains for that language.
			f = open (templatesDirectory + "/en/data/main.json")					#load the language with the base directories
			mains[language] = json.load(f)
			f.close()

		try:
			f = open(comsFileName, "w", encoding='utf-8')							#Output to the display that were indexing this data
			f.write('Indexing USB')
			f.close()
		except:
			pass


		###########################################################################
		# Check this path as a subpath of one main path already handled in extended
		###########################################################################
		x = 0
		y = 1												#Set y to 1 so we get through next test section if there are no extended paths.
		for testPath in complex_lst:									#Were looking at our complex_lst of paths one at a time
			y = (str(path).find(testPath))								#Does this path have our current complex_lst path?
			if (y >= 0):
				print ("Complex_lst found path in testpath, at : "+str(y))			#Any match is grounds for ignorning unless its index.html in the root.
				try:
					d = str(path)[(y+len(testPath)):]					#See if we have any subpaths after this path
					print("ok remainder of string is: "+d)
				except:
					d = ""
					print ("Hit our exception in the complex_lst test loop")
					y = 0
				if (d.find("/") == -1):								#by looking for a / in the tail of the path if not there then
					print ("This directory is a major directory of a complex one.  skip it except for index.htm*")
					webpaths.append(path)							#we found a subpath so make sure we get the path  in the webpaths list
					if ("index.html" in files): directoryType = 'folders'
					y = 1									# continue flag for testing for web elements
					break									# stop looking in the complex_lst
				else:	#we start with y>0
					directoryType = ""							# were a blank directory
					y = 0
					break									# This path is an extension of the complex_lst path
			else:											# Ok we didn't find this  complex_lst[x] in this path
				y = 1										# we want to continue since we need to check for web elements

		yy = y												# Were not a major directory in a complex one.
		y = 1
		print ("Ok we need to check if this is part of a web directory")
		if len(webpaths) > 0:
			print ("Testing for webpaths in this path", path, " : ",webpaths)
			for d in webpaths:
				x = path.find(d)
				if x >= 0:
					print ("Found webpath in path", x," : ",path[x:])
					y = 0									# non continue flag testing for web elements
					break									# We stop here since its a minor directory
				else:  continue									# Ok this is not our path keep going
			if ((x < 0) and (os.path.isfile(path + "/index.htm"))):					# if we didn't find our path in webpaths but we did find index.htm in the path then  we add
				webpaths.append(path)								# since we found our path in the with index.thm we change the state of continue on next set
				directoryType = "html"								# were a blank directory
				y = 1										# Since we added the path lets set our continue flag to not-continue

		print ("our evaluation of testing for web elements is finished we have go forward at: "+str(y)+ " , current directoryType is: " + directoryType + "yy: "+str(yy))

		if ((yy == 1) and (y == 0)): y = 0								# if we have go forward on extended but not web then we don't go forward.
		elif ((yy == 0) and (y == 1)): y = 0								# if we have go forward on webdirectory but not on extended directory we don't go forward
		else: y = 1


		##########################################################################
		#  If this directory contains index.html then treat as web content  (DO NOT AFFECT Y)
		##########################################################################

		if (((os.path.isfile(path + "/index.html")) or (str(files).find('index.htm') >= 0)) and ( y > 0)):	#we have inidex.html and our move forward flag y

			print ("	" + path + " is web content")
			# Make a symlink to the file on USB to display the content
#			print ("	WebPath: Writing symlink to /html folder")
			os.system ("ln -s '" + path + "' " + contentDirectory + "/" + language + "/html/")
			x = 0
#			print ("directoryType: ",directoryType)
			subpath = path.replace(mediaDirectory, "")
			print ("subpath is now: "+subpath)

			if not((os.path.isfile(mediaDirectory + "/" + (".webarchive-" + language + "-" + subpath + ".zip").replace("/","-").replace('--','-'))) or (os.path.isfile(mediaDirectory + '/.NoWebcompress'))):

				try:
					f = open(comsFileName, "w", encoding='utf-8')						#Update the display to show were zipping
					f.write('Creating ZIP'+chr(10)+"File")
					f.close()
				except:
					pass

				logging.info ("Trying to archive a web file set for " + thisDirectory)
				try:
					print ("	WebPath: Creating web archive zip file on USB for: ",subpath)
					x = 1   									#Set a flag that were creating an archive
					shutil.make_archive(mediaDirectory + "/" + (".webarchive-" + language + "-" + subpath).replace("/","-").replace('--','-'), 'zip', (path))
					SkipArchive = 1
					logging.info ("succeeded in finishing the zip file for .webarchvie-" + language + "-" + subpath.replace("/","-").replace("--","-")+".zip")
#					print ("succeeded in finishing the zip file for .webarchvie-" + language + "-" + subpath.replace("/","-").replace("--","-")+".zip")
				except:
					print ("	Error making web archive ")
					logging.info ("Failled to finishing the zip file for .webarchvie-" + language + "-" + subpath.replace("/","-").replace("--","-")+".zip")
					x = 0 	 									#Clear our archive flag
			else:
				print(("webarchive already exsists /.webarchive-" + language + '-' + subpath + ".zip").replace("/", "-").replace("--","-") + "or .Nowebarchive file in root")
				x = 1  											#set our archive flag
			# Re-write the display as indexing since it may have changed.
			try:
				f = open(comsFileName, "w", encoding='utf-8')
				f.write('Indexing USB')
				f.close()
			except:
				pass

			if x>0: os.system (("ln -s '"+ mediaDirectory + "/.webarchive-" + language + "-" + subpath.replace("/","-") + ".zip'  '" + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'").replace("--","-"))
			else: print ("No webarchve is available!!")

			dirs = []
			webpaths.append(path)
			if directoryType != 'folders':  directoryType = "html"						#if this is a complex folder we keep the folders icon otherwise
															#we treat it as a regular html directory


		print ("Directory Type is: ", directoryType)

		##########################################################################
		#  See if this directory is skipped because it resides within a webPath for a web site content such as ./images or ./js
		##########################################################################

		for testPath in webpaths:
			if ((path.find(testPath) != -1) and (not('folder' in directoryType)) and (not((os.path.isfile(path + "/index.html")) or (str(files).find('index.htm') >= 0)) or (y <= 0))):	#we will have testpath in path for 
															#for folder in directoryType or complexx folder, or an index.htm type file
				print ("	Skipping web path: " + path)
				skipWebPath = True
		if (skipWebPath):
			continue


		##########################################################################
		#  If this directory contains AndroidManifest.xml then treat as Android App
		##########################################################################

		if (os.path.isfile(path + "/AndroidManifest.xml")):
			print ("	" + path + " is Android App")
			# See if the language already exists in the directory, if not make and populate a directory from the template
			# Make a symlink to the file on USB to display the content
#			print ("	WebPath: Writing symlink to /html folder")
			os.system ("ln -s '" + path + "'  " + contentDirectory + "/" + language + "/html/")
#			print ("    Path is equal to: " + path)
			print("    Looking for: " + mediaDirectory + "/" + (".webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))


			if (not os.path.isfile(mediaDirectory + "/" + (".webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))):

				try:
					f = open(comsFileName, "w", encoding='utf-8')
					f.write('Creating ZIP'+chr(10)+"File")
					f.close()
				except:
					pass

				SkipArchive = 1

				logging.info ("Trying to archive an Android XML file set for " + thisDirectory)
				try:
					print ("	WebPath: Creating web archive zip file on USB at: "+ mediaDirectory + "/.webarchive-" + language + "-" + thisDirectory + ".zip")
					shutil.make_archive(mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory ).replace('--','-'), "zip", (path))
				except:
					print ("	error  making web archive")
				logging.info ("succeeded in finishing the zip file")

				try:
					f = open(comsFileName, "w", encoding='utf-8')
					f.write('Indexing USB')
					f.close()
				except:
					pass

			else: print (" Found it!!")
#			print ("	WebPath: Linking web archive zip")
			os.system ("ln -s '" + mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace("--","-") + "'  '" + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'")
			dirs = []
			webpaths.append(path)
			directoryType = "html"


		#############################################################################################
		#  Finish detecting directoryType (root, language, html, img,  collection, singular, folders)
		#############################################################################################
		if ((path == mediaDirectory) and (not ('folder' in directoryType))):
			directoryType = directoryType + ' root'
		elif (directoryType == '' and len(files) > 2):
			directoryType = directoryType + ' collection'
		elif (directoryType == "" and len(files) <=2):
			directoryType = directoryType + ' singular'
		elif ('folders' in directoryType):
			pass
		elif ('folder' in directoryType):
			pass
		elif ("language" in directoryType):
			pass
		elif ("html" in directoryType):
			pass
		else: directoryType = directoryTpye + ' singular'

		print ("	Processing Directory: " + path)
		print ("	Processing Files According To directoryType = " + directoryType)
		print ("	Processing Files According to language type= "+ language)
		print ("	--------------------------------------------------")



		##########################################################################
		#  If we have a .compress file in the root content folder we zip any directory with multiple items except languages.
		##########################################################################
		if ((('collection' in directoryType) or (len(files) > 1)) and not(language in directoryType) and (os.path.isfile(mediaDirectory + "/" + ".compress")) and (SkipArchive == 0)):
			print("        Looking to create a zip file of directory, thisDirectory:Looking to create a zip file of directory, thisDirectory: "+ thisDirectory, directoryType)
			# Make a symlink to the file on USB to display the content
			x = 0 													#This is a compressed file test flag
			for filename in files:
				if ((pathlib.Path(path + "/" + filename).suffix).lower() in '.zip, .gzip, .zy, .gz, .gzip, .7z, .bz2, .tar'): x = 1  #We found a compressed file
			if (x==0):												#Were ok to go forward with creating a compressed file of this directory
				print ("	Path: Writing symlink to /html folder")
				os.system ("ln -s '" + path + "' '" + contentDirectory + "/" + language + "/html/" + thisDirectory + "'")
				print ("        Path is equal to: " + path)

				if doesRootContainLanguage:
					print ("looking at: " + mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))
					if not os.path.isfile(mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-')):
						logging.info ("trying to create a zip file of " + mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")

						try:
							f = open(comsFileName, "w", encoding='utf-8')					#Update the display for creating a zip
							f.write('Creating ZIP'+chr(10)+"File")
							f.close()
						except:
							pass

						try:
							print ("	Path: Creating archive zip file on USB")
							shutil.make_archive(mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
							print ("	Path: Linking archive zip")
							os.system ('ln -s '+ mediaDirectory + "/" + language + "/" + thisDirectory +  "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
							logging.info ("succeeded in finishing the zip file")
						except:
							print ("	error  making archive")

						try:
							f = open(comsFileName, "w", encoding='utf-8')					#Update the display with Indexing status
							f.write('Indexing USB')
							f.close()
						except:
							pass
				else:
					print ("looking at: " + mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")
					if not os.path.isfile(mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip"):
						logging.info ("trying to create a zip file of " + mediaDirectory + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")

						try:
							f = open(comsFileName, "w", encoding='utf-8')					#Update the display for creating a zip
							f.write('Creating ZIP'+chr(10)+"File")
							f.close()
						except:
							pass

						try:
							print ("	Path: Creating archive zip file on USB")
							shutil.make_archive(mediaDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
							print ("	Path: Linking web archive zip")
							os.system ('ln -s '+ mediaDirectory + "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
							logging.info ("succeeded in finishing the zip file")
						except:
							print ("	error  making archive")

						try:
							f = open(comsFileName, "w", encoding='utf-8')					#Update the ddisplay for Indexing
							f.write('Indexing USB')
							f.close()
						except:
							pass

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
			fullFilename = path + "/" + filename									# Example /media/usb0/content/video.mp4
			shortName = pathlib.Path(path + "/" + filename).stem							# Example  video      (ALSO, slug is a term used in the BoltCMS mediabuilder that I'm adapting here)
			relativePath = path.replace(mediaDirectory + '/','')
			slug = (os.path.basename(fullFilename).replace('.','-')).replace('--','-')				# Example  video.mp4
			extension = (pathlib.Path(path + "/" + filename).suffix).lower()					# Example  .mp4
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
			if ("collection" in directoryType):
				print ("** Starting a collection: Loading Collection and Episode JSON **")
				if ('collection' not in locals() and 'collection' not in globals()):
					f = open (templatesDirectory + "/en/data/item.json")
					collection = json.load(f);
					f.close()
					collection["episodes"] = [];
					collection['image'] = 'blank.gif'							#default value but may be changed
				f = open (templatesDirectory + "/en/data/episode.json");
				content = json.load(f);
				f.close()
				content['image'] = 'blank.gif'									#default value but may be changed

			else:    #Singular, folders, root
				print ("	Loading Item JSON")
				f = open (templatesDirectory + "/en/data/item.json");
				content = json.load(f);
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
				elif ('folders' in directoryType):
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

			# Look for user generateed  thumbnail.  If there is one, use it.
			if (((content["image"] == 'blank.gif') or (content['image'] == "")) and (os.path.isfile(mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"))):
				print ("	Found Thumbnail" +  mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png")
				content["image"] =  slug + ".png"
				os.system ('ln -s "'+ mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png"' + '  "' + contentDirectory + '/' + language + '/images/' + slug + '.png"')
				print ("	Thumbnail link complete at: " + mediaDirectory + "/" +  content["image"])
				if ('collection' in locals() or 'collection' in globals()):
					if (collection['image'] == 'blank.gif'): collection['image'] = content['image']

			if content['image'] == "": content['image'] = 'blank.gif'

			# if this is an image, we use the image as the thumbnail
			if ((content["mimeType"] == "image") and (content["image"] == 'blank.gif')):  				#Since image is same as thumbnail we set thumbnail to image
				content["image"] = filename

				if ('collection' in locals() or 'collection' in globals()):
					if ((mediaDirectory + '/' + thisDirectory) == path):					#This means were a root directory and file
						if (collection['image'] == 'blank.gif'): collection['image'] = slug + ".png"
					elif (collection['image'] == 'blank.gif'): collection['image'] = 'images.png'

				try:
					if os.path.getsize(path + "/" + filename) > 100:					#image is large enough to be usable.
						os.system ("ln -s '" + fullFilename + "'  " + contentDirectory + "/" + language + "/images/")
					else:
						print (str(os.path.getsize(path + "/" + filename)) + " is the size we got for the image " + path + "/" + filename)
						content['image'] = 'images.png'
				except:
					print (" Ok we had an error tryuging to ge the size of " + path + "/" + filename)
					os.system ("ln -s '" + fullFilename + "'  " + contentDirectory + "/" + language + "/images/")
				if ('collection' in locals() or 'collection' in globals()) and collection['image'] == 'blank.gif': collection['image'] = "images.png"


			# If this is a video, we can probably make a thumbnail
			if ((content["mediaType"] == 'video') and (content["image"] == 'blank.gif')):

				try:
					if not (os.path.isfile(mediaDirectory + "/.thumbnail-" + language +  "-" + slug + ".png")):
						print ("	Attempting to make a thumbnail for the video")
						os.system("ffmpeg -y  -i '" + fullFilename + "' -an -ss 00:00:15 -vframes 1 '" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png'  >/dev/null 2>&1")
					if os.path.isfile(mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png'):
						content["ímage"] = slug + ".png"
						print ("        We found the thumbnail")
					try:
						if os.path.getsize( mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png") > 100:		#image is large enough to be usable.
							os.system ('ln -s "' + mediaDirectory +  '/.thumbnail-' + language + '-' + slug + '.png' + '"  "' + contentDirectory + '/' + language + '/images/' +  slug + '.png"')
							content["image"] =  slug + ".png"
						else:
							print ("        Image was too small to use!!!!!!!")
							content["image"] = 'video.png'
					except:
						print ("had an error getting size of video !!!!!!!!" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png")
						content['image'] = 'video.png'
				except:
					print ("Something whent wrong with the ffmpeg or elsewhere")
					content['image'] = 'video.png'
																# if its not a video & not an image
				if ('collection' in locals() or 'collection' in globals()) and (collection['image'] == 'blank.gif' or collection['image'] != 'video.png'):
					if content['image'] != 'video.png': collection['image'] = content['image']
					else: collection['image'] = "video.png"

			# if this is an audio file, we can probably get an image from the mp3
			if ((content["mediaType"] == 'audio') and (content["image"] == 'blank.gif')):
				print("        Were looking for " + ".thumbnail-" + language + "-" + slug + ".png")
				if not os.path.isfile( mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"):
					try:
						os.system("ffmpeg -y -i '" + fullFilename + "' -an -c:v copy '" + mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png'  >/dev/null 2>&1")
						if os.path.isfile(mediaDirectory + "./thumbnail-" + language + "-" + slug + ".png"):
							content["image"]= slug + ".png"
							if (os.path.getsize( mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png') > 100):
								print("mp3 thumbnail image created")
								os.system ('ln -s "' + mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png' + '"  "' + contentDirectory + '/' + language + '/images/' + slug + '.png"')
								if os.path.isfile(mediaDirectory + '/.thumbnail-' + language + '-' + slug + ".png"):
									print ("	Thumbnail image link complete at: " + mediaDirectory + "/.thumbnail-"+ language + "-" + slug + ".png")
								else:
									print ("       Thumbnail image did not get linked...or created.  ?????? What to do????? ")
									fail
							else:
								print ("NO mp3 thumbnail created")
								fail
					except: content["image"] = "sound.png"
				if ('collection' in locals() or 'collection' in globals()) and (collection['image'] == 'blank.gif' or collection['image'] != "sound.png"): collection['image'] = "sound.png"

			##########################################################################
			# Done with thumbnail creation and linkage
			##########################################################################

			if ('collection' in locals() or 'collection' in globals()):
				if (content["mediaType"] in 'audio'):  collection['image'] = 'sound.png'
				elif ((content["mediaType"] in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar') and (collection['image'] == 'blank.gif')):  collection['image'] = 'zip.png'
				elif ((content["mediaType"] in 'document, text, docx, xlsx, pptx') and (collection['image'] == 'blank.gif')):  collection['image'] = 'book.png'
				elif ((content['mediaType'] in 'epub') and (collection['image'] == 'blank.gif')): collection ['image'] = 'epub.png'
				elif ((content['mediaType'] in 'pdf') and (collection['image'] == 'blank.gif')): collection['image'] = 'pdf.png'
				elif ((content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg') and (collection['image'] == 'blank.gif')): collection['image'] = 'images.png'
				elif (content['mediaType'] in 'application') :
					collection['image'] = 'apps.png'
					content['title'] = content['title'] + extension
			else:
				if (content["mediaType"] in 'audio'):  content['image'] = 'sound.png'
				elif (content["mediaType"] in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar'):  content['image'] = 'zip.png'
				elif (content["mediaType"] in 'document, text, docx, xlsx, pptx'):  content['image'] = 'book.png'
				elif (content['mediaType'] in 'epub'): content ['image'] = 'epub.png'
				elif (content['mediaType'] in 'pdf') : content['image'] = 'pdf.png'
				elif (content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg'):
					if ((content['image'] == "") or (content['image'] == 'blank.gif')):
						 content['image'] = 'images.png'
				elif (content['mediaType'] == 'application') :
					content['image'] = 'apps.png'
					content['title'] = content['title'] + extension

			##########################################################################
			#  Compiling Collection or Single
			##########################################################################
			if ( 'collection' in directoryType):
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
				elif ((collection['mediaType'] != content['mediaType']) and (collection['image'] == 'book.png')):
					print (" Replacing collection content type with new value: " + content['mediaType'])
					collection['mediaType'] = content['mediaType']
					collection['image'] = content['image']

				collection["episodes"].append(content)
				with open(contentDirectory + "/" + language + "/data/" + collection['slug'] + ".json", 'w', encoding='utf-8') as f:
					json.dump(collection, f, ensure_ascii=False, indent=4)
					print("** Wrote out the collection data structure: "+collection['slug']+" ***")
				f.close()
			else:
				print ("	Item completed.  Writing item.json")
				# Since there's no episodes, just copy content into item
				# Write the item.json
				with open(contentDirectory + "/" + language + "/data/" + slug + ".json", 'w', encoding='utf-8') as f:
					print ("** Writing single element to item.json based on slug "+slug+" then this is appended to mains **")
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
		if (('collection' in locals() or 'collection' in globals()) and ("collection" in directoryType)):
			print ("	No More Episodes / Wrap up Collection for " + thisDirectory + " by adding it to mains[language]['content'] ")
			# slug.json has already been saved so we don't need to do that.  Just write the collection to the main.json
			print ("***  appending the collection to mains now ***")
			mains[language]["content"].append(collection)
			del collection
		# END DIRECTORY LOOP

	try:
		os.system("rm "+complex_dir)
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

		try:
			x = os.system("rm " + comsFileName)
			x = os.waitstatus_to_exitcode(x)
			while x!=0:
				x = os.system("rm " + comsFileName)
				x = os.waitstatus_to_exitcode(x)
				time.sleep(1)
		except:
			pass											#Clear the display

			try:
				os.system('rm '+ ComplexDir)
			except:
				pass

			sys.exit()

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

	try:
		os.system('rm '+ ComplexDir)
	except:
		pass

	try:
		x = os.system("rm " + comsFileName)
		x = os.waitstatus_to_exitcode(x)
		while x!=0:
			x = os.system("rm " + comsFileName)
			x = os.waitstatus_to_exitcode(x)
			time.sleep(1)
	except:
		pass											#Clear the display

	print ("DONE")
	sys.exit()


if __name__ == '__main__' :

	try:
		f = open(comsFileName, "r", encoding = "utf-8")
		print(" Ok the comsFileName file is present. we can't try to load since system is doing something else")
		logging.info(" Skipped mmmiLoader.py since complex_dir file was present")
		sys.exit()
	except:
		pass

	print ("Ok now we will start the loader")

	mmiloader_code()
