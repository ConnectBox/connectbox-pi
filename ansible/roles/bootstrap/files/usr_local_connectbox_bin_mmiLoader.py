#!/usr/bin/python3
#  Loads content from USB and creates the JSON / file structure for enhanced media interface


import json
import os
import pathlib
import shlex
import shutil
import mimetypes
import logging
import subprocess
import sys
import time
#import ffmpeg

def update_display(message):
	"""Write a status message to the display coordination file.

	The ConnectBox UI polls /tmp/creating_menus.txt to show a progress overlay
	on the device screen while indexing is running.  Writing to this file is
	best-effort; if the write fails (e.g. the filesystem is read-only or the
	directory does not exist) the error is silently swallowed so that indexing
	continues uninterrupted.

	Parameters
	----------
	message : str
	    The human-readable status string to display (e.g. 'Indexing USB').
	    A newline character (chr(10)) may be embedded to force a line break
	    on the device display.

	Returns
	-------
	None
	"""
	try:
		with open("/tmp/creating_menus.txt", "w", encoding='utf-8') as f:
			f.write(message)
	except Exception as e:
		logging.debug(f"Ignored exception: {e}")

def run_cmd(cmd):
	"""Execute a shell command, logging failures but never raising an exception.

	Uses subprocess.run with shell=True so that shell features such as
	piping, redirection, and command substitution work as expected.  The
	check=True flag means a non-zero exit code raises CalledProcessError,
	which is caught here so that a single failing command does not abort the
	entire indexing run — a best-effort approach appropriate for operations
	such as creating symlinks that may already exist.

	Parameters
	----------
	cmd : str
	    The full shell command string to execute.

	Returns
	-------
	None
	"""
	try:
		subprocess.run(cmd, shell=True, check=True)
	except subprocess.CalledProcessError as e:
		logging.error(f"Command failed: {cmd}")
		print(f"    *** run_cmd FAILED (exit {e.returncode}): {cmd}")


def is_blank_thumbnail(path):
	"""Return True if the image is too uniform to be a useful thumbnail.

	Resizes to 64x64 before analysis so this runs fast on low-power hardware.
	Rejects frames that are nearly any single colour (black title cards, white
	fades, solid-colour overlays) by requiring sufficient contrast (std dev >= 20).
	Also rejects frames that are almost entirely dark (mean < 20) or blown-out
	(mean > 235) even if a handful of pixels differ.

	Parameters
	----------
	path : str
	    Absolute path to the candidate thumbnail image file.

	Returns
	-------
	bool
	    True  — the image is blank/uniform and should be discarded.
	    False — the image has enough visual content to be a useful thumbnail,
	            OR PIL is unavailable / the image is unreadable (fail-open so
	            we never block thumbnail creation due to missing PIL).
	"""
	try:
		from PIL import Image
		img = Image.open(path).convert('L').resize((64, 64))
		pixels = list(img.getdata())
		mean = sum(pixels) / len(pixels)
		if mean < 20 or mean > 235:
			return True
		variance = sum((p - mean) ** 2 for p in pixels) / len(pixels)
		std_dev = variance ** 0.5
		return std_dev < 20  # too uniform — nearly one solid colour
	except Exception:
		return False  # if PIL unavailable or image unreadable, accept the frame


def mmiloader_code():
	"""Primary entry point: scan USB content and build the enhanced media interface index.

	This function performs the complete indexing pipeline for the ConnectBox
	enhanced media interface.  It is designed to run at boot (or on USB insert)
	and must handle a wide variety of USB content layouts gracefully, including:

	  * Single-language flat content (all files directly in /media/usb0/content)
	  * Multi-language layouts (ISO-code subdirectories such as 'en', 'fa', 'bos')
	  * Regional language variants (e.g. 'zh-CN', 'pt-BR')
	  * Web/HTML content trees (detected by the presence of index.html)
	  * Android app bundles (detected by AndroidManifest.xml)
	  * Complex nested directory structures (multiple sub-directories, few files)

	High-level pipeline
	-------------------
	1.  Single-instance guard — prevent duplicate runs by inspecting /proc.
	2.  saved.zip fast path — if a saved.zip index cache exists on the USB,
	    unzip it and exit immediately rather than re-indexing.
	3.  Language detection — walk the USB root to find ISO-code directories
	    and/or a .language marker file that declares the active language.
	4.  Complex-directory detection — identify web/app bundles that need to
	    be treated as opaque HTML trees rather than media-file directories.
	5.  Main content loop — walk every directory, determine its directoryType,
	    generate thumbnails via ffmpeg, create symlinks into the web-server
	    content tree, and accumulate JSON metadata.
	6.  Wrap-up — write main.json, interface.json, and languages.json for each
	    language, then compress the entire content tree into saved.zip on the
	    USB for fast loading on next insert.

	Key path constants (set inside this function)
	----------------------------------------------
	mediaDirectory    : /media/usb0/content           — USB content root
	templatesDirectory: /var/www/enhanced/…/templates  — JSON/HTML skeletons
	contentDirectory  : /var/www/enhanced/…/content    — web-server asset root
	zipFileName       : mediaDirectory/saved.zip       — compressed index cache

	Parameters
	----------
	None — all configuration is derived from well-known filesystem paths.

	Returns
	-------
	None
	    The function calls sys.exit() at natural termination points; it only
	    returns normally if the single-instance guard fires and no work is done.
	"""

	# -------------------------------------------------------------------------
	# Single-instance guard: exit if another mmiLoader Python process is already running.
	# We check /proc directly rather than pgrep -f because pgrep matches shell processes
	# whose argv contains "mmiLoader.py" as a -c argument (e.g. the sh launched by
	# os.system()), causing false positives that prevent mmiLoader from ever running.
	# -------------------------------------------------------------------------
	try:
		my_pid = os.getpid()
		running_pids = []
		import glob
		for cmdline_path in glob.glob('/proc/*/cmdline'):
			try:
				pid = int(cmdline_path.split('/')[2])
				if pid == my_pid:
					continue
				with open(cmdline_path, 'rb') as _f:
					args = _f.read().split(b'\x00')
				# argv[0] must be a python interpreter, argv[1] must be our script
				if (len(args) >= 2
						and b'python' in args[0]
						and b'mmiLoader.py' in args[1]):
					running_pids.append(pid)
			except Exception:
				pass
		if running_pids:
			print("mmiLoader.py already running (pid " + str(running_pids) + "), exiting")
			logging.info("mmiLoader.py already running, skipping duplicate run")
			return
	except Exception:
		pass  # If /proc unavailable, continue

	# -------------------------------------------------------------------------
	# Path and state variable initialisation.
	# All directory constants are defined here so they are easy to adjust for
	# alternative deployments without hunting through the rest of the code.
	# -------------------------------------------------------------------------
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

	mains = {}        # This object contains all the data to construct each main.json at the end.  We add as we go along
	logging.info("Starting a run of mmiLoader.py to index the data contents and create the user interface")

	# Clear the comsFileName directory so we dont have a screen on

	try:
		os.remove(comsFileName)										#Always starat with display off, no leftover elements
	except Exception as e:
		logging.debug(f"Ignored exception: {e}")
		pass

	update_display('Loading USB')

	# Guard: exit immediately if USB is not mounted — prevents using root-FS files
	if not os.path.ismount(mediaDirectory.split('/content')[0]):
		print("USB not mounted at startup, exiting cleanly")
		sys.exit()

	##########################################################################
	#  Fast-path: saved.zip detected — restore and exit without re-indexing.
	#
	#  saved.zip is written at the end of a full indexing run and contains the
	#  entire contentDirectory tree (JSON metadata + symlinks).  When the same
	#  USB key is reinserted the zip lets us skip minutes of ffmpeg work.
	#
	#  We distinguish "same USB key" from "different USB key" by caching the
	#  zip file's mtime in /tmp/.saved_zip_mtime:
	#    • Same mtime  → use -n (no-overwrite) for speed; existing files kept.
	#    • Different mtime → wipe contentDirectory first so stale content from
	#      the previous key cannot leak into the new interface.
	##########################################################################

	print ("	Check for saved.zip")
	if (os.path.isfile(os.path.join(mediaDirectory, "saved.zip"))):							#Check for a quick index file for creating the data structures.
		print ("	Found saved.zip.  Unzipping and restoring to " + contentDirectory)
		print (" ")
		print ("****If you want to reload the USB, delete the file saved.zip from the USB drive.")

		os.makedirs(contentDirectory, mode=0o755, exist_ok=True)
		update_display('Unzipping USB')

		# Compare saved.zip mtime to marker written after last successful unzip.
		# Same mtime = same USB key: skip files already on disk (-n) for speed.
		# Different mtime = different USB key: wipe first so old content doesn't persist.
		mtime_marker = "/tmp/.saved_zip_mtime"
		current_mtime = str(os.path.getmtime(zipFileName))
		try:
			with open(mtime_marker) as _f:
				cached_mtime = _f.read().strip()
		except Exception:
			cached_mtime = ""

		if cached_mtime == current_mtime:
			print("	Same USB key detected — skipping files already present")
			run_cmd("(cd " + contentDirectory + " && unzip -n " + zipFileName + ")")
		else:
			print("	New or changed USB key — full extract")
			shutil.rmtree(contentDirectory, ignore_errors=True)
			os.makedirs(contentDirectory, mode=0o755, exist_ok=True)
			run_cmd("(cd " + contentDirectory + " && unzip " + zipFileName + ")")
			try:
				with open(mtime_marker, "w") as _f:
					_f.write(current_mtime)
			except Exception:
				pass
		print ("DONE")
		time.sleep(3)
		try:
			os.remove(comsFileName)
		except Exception:
			pass											#Clear the display

		exit(0)												#We finished up with restoring the data for this USB stick. exit the app.

	##########################################################################
	#  Full indexing path: no saved.zip present.
	#  Wipe any stale contentDirectory and rebuild it from the USB contents.
	#  We copy the English template tree first because 'en' is the fallback
	#  language for all content that has no language directory on the USB.
	##########################################################################

	print ("Creating content Directory")
	update_display('Indexing USB')
	shutil.rmtree(contentDirectory, ignore_errors=True)							#Wipe any old content before full index
	os.makedirs(contentDirectory, mode=0o755, exist_ok=True)						#Create a new content directory to store our data in

	print ("Copying the templates to the main contentDirectory")
	shutil.copytree(templatesDirectory + '/en', contentDirectory + '/en', dirs_exist_ok=True)		#Copy the templates to an /en language file for starters.
	shutil.copy(templatesDirectory + '/footer.html', contentDirectory)					#Get the html footer
	print ("copyied templates for en and footer")


	f = open (templatesDirectory + "/en/data/main.json", "r")						#Get the main data structure
	mains["en"] = json.load(f)										#load it for /en language
	f.close()
	# Guard: if the USB was removed while we were starting up, exit before writing anything to mediaDirectory
	if not os.path.ismount(mediaDirectory.split('/content')[0]):
		print("USB no longer mounted before index write, exiting cleanly")
		sys.exit()

	print ("going to get the language codes now")

	# Retrieve language codes
	f = open(templatesDirectory + '/languageCodes.json', "r")						#Get the master language list
	languageCodes = json.load(f)
	f.close()
	print ("language codes loaded")


	# Retrieve brand.j2
	f = open('/usr/local/connectbox/brand.j2', "r")								#Get the current brand information
	brand = json.load(f)
	f.close()
	print ("brand Aquired")

	# -------------------------------------------------------------------------
	# Sanity-check the brand configuration.
	# brand.j2 is maintained by the administrator; it may be incomplete or
	# contain placeholder values.  We fall back to the device hostname for the
	# brand name and a known-good default logo path so the interface is always
	# renderable even on a fresh or misconfigured device.
	# -------------------------------------------------------------------------
	if not brand.get('Brand') or len(brand['Brand']) < 5:
		try:
			brand['Brand'] = subprocess.check_output(['hostname'], text=True).strip()
		except Exception as e:
			logging.error(f"Could not read hostname: {e}")
			brand['Brand'] = 'ConnectBox'
		logging.warning("Brand name missing or too short, defaulting to hostname")
	else:
		print("Custom Branding: " + brand['Brand'])
	if not brand.get('Logo') or len(brand['Logo']) < 5:
		brand['Logo'] = "imgs/logo.png"  # Default logo
		logging.warning("Logo missing or too short, using default")
	else:
		print("Custom Logo: " + brand['Logo'])

	print ("Building Content For " + brand['Brand'])

	# -------------------------------------------------------------------------
	# Inject the brand name and logo into the interface.json template.
	# interface.json is served to the front-end app and controls the header
	# area of the enhanced media interface (title bar text and logo image).
	# enhancedInterfaceLogo overrides Logo when a separate hi-res logo is
	# provided specifically for the enhanced interface.
	# -------------------------------------------------------------------------
	# Insert Brand and Logo into the interface template.  We will write this at the end to each language
	f = open (templatesDirectory + "/en/data/interface.json", "r")   # We will always place USB content in EN language which is default
	interface = json.load(f)
	f.close()
	interface["APP_NAME"] = brand["Brand"]

	if brand.get("enhancedInterfaceLogo", "") != "" :
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

	# -------------------------------------------------------------------------
	# Bootstrap guard: if the USB content directory is completely empty, write
	# a placeholder text file so that the indexer always has at least one item
	# to process.  This prevents the interface from rendering an empty library
	# and gives the user a visible hint to add content.
	# -------------------------------------------------------------------------
	# Check for empty directory and write default content if empty
	try:
		if len(os.listdir(mediaDirectory) ) == 0:
			print("Directory is empty")								#If the main directory has no data create one file to iindex
			f = open(mediaDirectory + "/connectbox.txt", "a")
			f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
			f.close()
	except Exception as e:
			print("Directory is empty or inaccessible")
			run_cmd("mkdir " + mediaDirectory)
			if not os.path.isdir(mediaDirectory):
				print("Failed to create mediaDirectory (I/O error?), exiting cleanly")
				sys.exit()
			try:
				f = open(mediaDirectory + "/connectbox.txt", "w")
				f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
				f.close()
			except Exception as e2:
				print(f"Failed to write to mediaDirectory: {e2}, exiting cleanly")
				sys.exit()

	language = "en"  # By default but it will be overwritten if there are other language directories on the USB
	directoryType = "" # By default we don't have a directory type (language, folder, folders, singular, etc.


	print("Check mediaDirectory for at least one language")


	##########################################################################
	#  Detect language directories at the USB root.
	#
	#  The ConnectBox supports multi-language USB layouts where the top-level
	#  directories are named with ISO language codes (e.g. 'en', 'fa', 'bos',
	#  'zh-CN').  This block collects all root-level directory names, then
	#  filters them against the master languageCodes lookup:
	#    • Exact ISO matches are kept as-is.
	#    • Regional variants (e.g. 'zh-CN') are resolved to their base code
	#      and aliased in languageCodes so downstream lookups succeed.
	#    • Anything that is not a recognised language code is removed from the
	#      list — those directories will be processed as normal content folders.
	#
	#  Result: doesRootContainLanguage holds only the validated language codes.
	#  If this list is non-empty, the main content loop will SKIP any root-level
	#  directory that is not in this list, enforcing a language-partitioned layout.
	##########################################################################

	doesRootContainLanguage = (next(os.walk(mediaDirectory))[1])
	y = 0
	while ((y < len(doesRootContainLanguage) and (len(doesRootContainLanguage) > 0))):
		lang = doesRootContainLanguage[y]
		print ("lang is now: "+lang)
		try:
			print ("lang is: ",languageCodes[lang]['english'])

			if len(lang) > 3: 								#Check for regional variant (e.g. zh-CN, pt-BR)
				base_lang = lang.split('-')[0] if '-' in lang else ''
				if base_lang and base_lang in languageCodes:
					# Alias regional variant so all subsequent languageCodes[lang] lookups work
					languageCodes[lang] = languageCodes[base_lang]
					print("checking language " + lang + " as valid regional variant of " + base_lang)
					y += 1
				else:
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
		except Exception as e:
			# Check if this is a regional variant (e.g. zh-CN, pt-BR) before discarding
			base_lang = lang.split('-')[0] if '-' in lang else ''
			if base_lang and base_lang in languageCodes:
				languageCodes[lang] = languageCodes[base_lang]
				print("checking language " + lang + " as valid regional variant of " + base_lang)
				y += 1
			else:
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
	#  Pre-pass: determine the active language mode before the main content loop.
	#
	#  Three possible outcomes:
	#  1. A root-level directory matches a known ISO code  →  directoryType = 'language',
	#     language is set to that code, NoISOCodes = 0 (full multi-lang mode).
	#  2. A .language file exists at the USB root  →  directoryType = 'language',
	#     language is set to the code in that file, NoISOCodes = 1 (single-lang
	#     override: ignores any language-named directories already discovered).
	#  3. Neither  →  directoryType = "", language = "en" (default English mode).
	#
	#  We use os.walk to iterate but only care about the root level; 'continue'
	#  is used liberally to skip deeper paths without processing them here.
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
		except Exception as e:
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
		#  Complex directory detection pass.
		#
		#  A "complex" directory is one that contains a self-contained web/app
		#  bundle — typically a directory tree with an index.html or Start_Here.htm
		#  at its root and sub-directories for assets (js, css, images, etc.).
		#  These should be served as an opaque HTML tree rather than having their
		#  individual files indexed as separate media items.
		#
		#  Detection logic:
		#  1. If the current path already appears in complex_lst (or is a sub-path
		#     of a known complex directory), skip further checking — it has already
		#     been classified (z = 1 acts as a short-circuit flag).
		#  2. For root-level directories with no files (or ≤ 2 files) and at least
		#     one sub-directory, we recurse into each sub-directory.  If a
		#     sub-directory has sub-directories itself but only an index.html (or
		#     Start_Here.htm) file, it qualifies as a complex head and its parent
		#     is added to complex_lst.
		#  3. The root path itself is also checked: if it has sub-dirs and an
		#     index.html directly, it is added directly to complex_lst.
		#
		#  complex_lst is persisted to /tmp/Complex_lst as JSON so that the
		#  recursive processing step (process_dir calls below) can work from the
		#  same list without re-walking the USB tree.
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
					update_display('Highly Complex' + chr(10) + 'Filesystem')
					print("Added complex root directory "+str(path))
					### We leave math alogne and z alone ###
					#This is our continue flag for the outer loop
			else:
				for d in dirs:										#Now lets check the directories under the path
					for pathname, dirname, filename in os.walk(os.path.join(path,d)):
						if ((len(dirname) > 0) and (len(filename) <= 2)):			#This looks like a complex directory we need to add to the list
							if ('index.html' in filename) and (len(filename) == 1):
								print("FOUND MY INDEX/HTML FILE")
								pass
							elif ('Start_Here.htm' in filename):
								pass
							else:
								continue
						else: continue								# We don't have the right files in the directory so its not a viable complex struture

						print("ÖK we found a starting path tha needs to go into the complex list")
						complex_lst.append(path)						#While the subdirectory is complex this shows the path is also.
						update_display('Highly Complex' + chr(10) + 'Filesystem')

						print("Added complex root directory "+str(path))
						z = 1									#This is our continue flag for the outer loop
						break

	# Persist the complex directory list so the recursive HTML processor can read it
	if len(complex_lst)>0:											#If we have complex directories then lets save the list off
		f = open(complex_dir, "w", encoding='utf-8')
		json.dump(complex_lst, f)
		f.close()

	print("We have a total of " + str(len(complex_lst)) + " complex directories heads to process")

	##################################################################################################
	#  Process complex (HTML-tree) directories.
	#
	#  Each entry in complex_lst is a self-contained web/app bundle root.
	#  process_dir() is called with mode="recursive" so it copies (or symlinks)
	#  the entire sub-tree into the web-server content area and generates an
	#  HTML entry for the enhanced interface — rather than indexing individual
	#  media files inside the bundle.
	#
	#  After processing, we touch .indexed.idx on the USB to record that at
	#  least one full index pass has completed.  This marker is read back on
	#  subsequent runs (indexed_before flag) so that process_dir() can decide
	#  whether to re-generate thumbnails or skip already-completed work.
	##################################################################################################

	for path in complex_lst:										#Now we have a full list of complex directories
		process_dir(path, path, "recursive", indexed_before )						#process the complex directory into HTML code

	print("Finished the complex directory recursion")
	if len(complex_lst)>0: run_cmd("touch " + (os.path.join(mediaDirectory, ".indexed.idx")))		#Write the file that says we have done the indexing at least once.

	update_display("Indexing USB")

	##########################################################################
	#  Main content indexing loop.
	#
	#  os.walk visits every directory under mediaDirectory.  For each directory
	#  we:
	#    1. Check the USB is still mounted (exit cleanly if ejected mid-run).
	#    2. Determine the directoryType (language, root, collection, singular,
	#       html, folders) by inspecting the path, its files, and the presence
	#       of special marker files (index.html, AndroidManifest.xml, .compress).
	#    3. Skip directories that are sub-paths of already-classified web trees
	#       (webpaths) or complex HTML bundles (complex_lst).
	#    4. For each file in the directory:
	#         a. Resolve the MIME type.
	#         b. Generate or locate a thumbnail (via ffmpeg for video/audio,
	#            or directly for images).
	#         c. Build the JSON metadata object (item.json / episode.json).
	#         d. Symlink the file into the web-server content tree.
	#    5. After all files in a directory are processed, if it was a
	#       'collection', append the completed collection object to mains.
	##########################################################################
	for path,dirs,files in os.walk(mediaDirectory):								#This is our main content analysis loop now for data

		# Mount check on every iteration: if the USB is ejected mid-run we
		# must not continue writing to the root filesystem.
		if not os.path.ismount(mediaDirectory.split('/content')[0]):
			print("USB unmounted mid-run, aborting")
			logging.warning("USB unmounted during indexing, exiting without saved.zip")
			sys.exit(1)

		thisDirectory = os.path.basename(os.path.normpath(path))
		print ("====================================================")
		print ("Evaluating Directory: " + thisDirectory)

		shortPath = path.replace(mediaDirectory + '/','')							#Relative path from media root
		# These next two lines ignore directories and files that start with .
		files = [f for f in files if not f[0] == '_']							#Normalize files again
		dirs[:] = [d for d in dirs if not d[0] == '_']							#Normalize directories again
		files = [f for f in files if not f[0] == '.']
		dirs[:] = [d for d in dirs if not d[0] == '.']
		files.sort()											#Sort files

		directoryType = ''  	# Always start a directory with unknown
		skipWebPath = False    # By Defaults								#Flag to indicate skippiing of web paths



		##########################################################################
		#  Language classification for this directory.
		#
		#  We re-check whether the current directory is a known language root so
		#  that the 'language' variable is correctly set before we process any
		#  files.  This matters for multi-language USB layouts: content found
		#  under /fa must be tagged with language='fa', not carried over from the
		#  previous iteration.  The try/except swallows KeyError from languageCodes
		#  lookups when the directory name is not a language code at all.
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

		except Exception as e: #We had an error so we jsut use the /en we setup before
#			print ('	NOT a Language: ' + thisDirectory)
			pass

		##########################################################################
		#  Skip non-language root directories when language partitioning is active.
		#
		#  If doesRootContainLanguage is non-empty, the USB uses a language-
		#  partitioned layout.  Any root-level directory that was not recognised as
		#  a language code must be ignored; its files belong to the language folder
		#  that contains them, not to a separate top-level category.
		##########################################################################

		if (path == mediaDirectory and directoryType != "language" and doesRootContainLanguage):
			print ('	Skipping because directory is not a lanugage: ' + thisDirectory)
			continue  										#Skip any directory without a language ISO code that is in root with other language directories

		##########################################################################
		#  First-time language setup.
		#
		#  When a language is encountered for the first time (i.e. its content
		#  directory tree has not yet been created), we copy the English template
		#  tree into a new language-named subdirectory and seed mains[language]
		#  with the default main.json structure.  This ensures that every
		#  language has the full set of required directories (data/, images/,
		#  media/, html/, zip/) before any files are written into them.
		#  We check for the data/ subdirectory specifically because the language
		#  dir itself may have been partially created in a previous failed run.
		##########################################################################

		# See if the language already exists in the directory, if not make and populate a directory from the template
		if (not os.path.exists(contentDirectory + "/" + language + "/data")):				#Check for data/ specifically — language dir may exist but be incomplete
			print("Doing new language setup " + language + " **********************************")
			print ("	Creating Directory: " + contentDirectory + "/" + language)
			shutil.copytree(templatesDirectory + '/en', contentDirectory + "/" + language, dirs_exist_ok=True)
			run_cmd ("chown -R www-data.www-data " + contentDirectory + "/" + language)
			# Load the main.json template and populate the mains for that language.
			if language not in mains:
				f = open (templatesDirectory + "/en/data/main.json")				#load the language with the base directories
				mains[language] = json.load(f)
				f.close()

		update_display('Indexing USB')


		###########################################################################
		#  Complex-directory exclusion check.
		#
		#  Directories that are sub-paths of a complex HTML bundle (entries in
		#  complex_lst) have already been processed by process_dir().  We must
		#  not re-index them here as individual media files, so we set y=1 to
		#  indicate "skip this directory in the main loop" and break early.
		#
		#  The variable 'yy' captures whether this path is a MAJOR directory of
		#  a complex bundle (i.e. the bundle root itself, not a sub-directory).
		#  Major directories need their index.html entry created; sub-directories
		#  (where d contains a '/') are fully skipped (y=0).
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
				except Exception as e:
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
		# -------------------------------------------------------------------------
		# webpaths exclusion check.
		#
		# webpaths accumulates every directory that has been classified as an HTML
		# or web-archive tree.  Sub-directories inside such trees must not be
		# indexed individually — their files are part of the archive that was
		# already created for the parent.  We check whether the current path is
		# a sub-path of any entry in webpaths and set y=0 to trigger a skip.
		#
		# Exception: if the current path itself has an index.htm, we add it to
		# webpaths so its own archive can be created (handles nested web sites
		# where each subdirectory is itself a standalone web page).
		# -------------------------------------------------------------------------
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

		# -------------------------------------------------------------------------
		# Combine the two skip signals (complex-bundle exclusion and web-path
		# exclusion) into a single go/no-go flag.  BOTH must say "go" (y==1,
		# yy==1) for processing to continue; a single "skip" from either check
		# causes the directory to be skipped entirely.
		# -------------------------------------------------------------------------
		if (yy == 1) and (y == 1): y = 1								# both checks say go forward — process this directory
		else: y = 0											# either check said skip — do not process


		##########################################################################
		#  Web content detection: index.html present.
		#
		#  If a directory contains index.html (or any index.htm* file) and the
		#  go/no-go flag is set, the directory is an HTML website that should be
		#  served as a single item with a ZIP download, not as a list of files.
		#
		#  Steps:
		#  1. Create a symlink into the web-server html/ tree so the browser can
		#     serve the site directly.
		#  2. Create (or reuse) a .webarchive-<lang>-<subpath>.zip on the USB so
		#     users can download the site for offline use.  The ZIP is skipped if
		#     a .NoWebcompress marker file exists in the USB root.
		#  3. Symlink the ZIP into the web-server html/ tree.
		#  4. Mark dirs=[] to prevent os.walk from descending further — the inner
		#     files are part of the web archive and must not be individually indexed.
		##########################################################################

		if (((os.path.isfile(path + "/index.html")) or (str(files).find('index.htm') >= 0)) and ( y > 0)):	#we have inidex.html and our move forward flag y

			print ("	" + path + " is web content")
			# Make a symlink to the file on USB to display the content
#			print ("	WebPath: Writing symlink to /html folder")
			run_cmd ("ln -s '" + path + "' " + contentDirectory + "/" + language + "/html/")
			x = 0
#			print ("directoryType: ",directoryType)
			subpath = path.replace(mediaDirectory, "")
			print ("subpath is now: "+subpath)

			if not((os.path.isfile(mediaDirectory + "/" + (".webarchive-" + language + "-" + subpath + ".zip").replace("/","-").replace('--','-'))) or (os.path.isfile(mediaDirectory + '/.NoWebcompress'))):

				update_display('Creating ZIP'+chr(10)+"File")

				logging.info ("Trying to archive a web file set for " + thisDirectory)
				try:
					print ("	WebPath: Creating web archive zip file on USB for: ",subpath)
					x = 1   									#Set a flag that were creating an archive
					shutil.make_archive(mediaDirectory + "/" + (".webarchive-" + language + "-" + subpath).replace("/","-").replace('--','-'), 'zip', (path))
					SkipArchive = 1
					logging.info ("succeeded in finishing the zip file for .webarchvie-" + language + "-" + subpath.replace("/","-").replace("--","-")+".zip")
#					print ("succeeded in finishing the zip file for .webarchvie-" + language + "-" + subpath.replace("/","-").replace("--","-")+".zip")
				except Exception as e:
					print ("	Error making web archive ")
					logging.info ("Failled to finishing the zip file for .webarchvie-" + language + "-" + subpath.replace("/","-").replace("--","-")+".zip")
					x = 0 	 									#Clear our archive flag
			else:
				print(("webarchive already exsists /.webarchive-" + language + '-' + subpath + ".zip").replace("/", "-").replace("--","-") + "or .Nowebarchive file in root")
				x = 1  											#set our archive flag
			# Re-write the display as indexing since it may have changed.
			update_display('Indexing USB')

			if x>0: run_cmd (("ln -s '"+ mediaDirectory + "/.webarchive-" + language + "-" + subpath.replace("/","-") + ".zip'  '" + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'").replace("--","-"))
			else: print ("No webarchve is available!!")

			dirs = []
			webpaths.append(path)
			if directoryType != 'folders':  directoryType = "html"						#if this is a complex folder we keep the folders icon otherwise
																#we treat it as a regular html directory


		print ("Directory Type is: ", directoryType)

		##########################################################################
		#  Web sub-directory skip.
		#
		#  Now that webpaths is fully updated (including any newly added path from
		#  the index.html check above), do a final pass to confirm this path is not
		#  a sub-directory of a web tree.  If it is, set skipWebPath=True and
		#  'continue' to the next os.walk iteration.  We must not process the
		#  individual JS/CSS/image files inside a web archive as media items.
		##########################################################################

		for testPath in webpaths:
			if ((path.find(testPath) != -1) and (not('folder' in directoryType)) and (not((os.path.isfile(path + "/index.html")) or (str(files).find('index.htm') >= 0)) or (y <= 0))):	#we will have testpath in path for
																#for folder in directoryType or complexx folder, or an index.htm type file
				print ("	Skipping web path: " + path)
				skipWebPath = True
		if (skipWebPath):
			continue


		##########################################################################
		#  Android app bundle detection: AndroidManifest.xml present.
		#
		#  An Android app distributed as a directory (rather than a single APK)
		#  contains AndroidManifest.xml at its root.  We treat it identically to
		#  a web tree: symlink the directory into html/, create a zip archive for
		#  download, and prevent os.walk from descending into sub-directories.
		#  The ZIP is named .webarchive-<lang>-<dirname>.zip for consistency with
		#  the HTML web-archive naming scheme.
		##########################################################################

		if (os.path.isfile(path + "/AndroidManifest.xml")):
			print ("	" + path + " is Android App")
			# See if the language already exists in the directory, if not make and populate a directory from the template
			# Make a symlink to the file on USB to display the content
#			print ("	WebPath: Writing symlink to /html folder")
			run_cmd ("ln -s '" + path + "'  " + contentDirectory + "/" + language + "/html/")
#			print ("    Path is equal to: " + path)
			print("    Looking for: " + mediaDirectory + "/" + (".webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))


			if (not os.path.isfile(mediaDirectory + "/" + (".webarchive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))):

				update_display('Creating ZIP'+chr(10)+"File")

				SkipArchive = 1

				logging.info ("Trying to archive an Android XML file set for " + thisDirectory)
				try:
					print ("	WebPath: Creating web archive zip file on USB at: "+ mediaDirectory + "/.webarchive-" + language + "-" + thisDirectory + ".zip")
					shutil.make_archive(mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory ).replace('--','-'), "zip", (path))
				except Exception as e:
					print ("	error  making web archive")
				logging.info ("succeeded in finishing the zip file")

				update_display('Indexing USB')

			else: print (" Found it!!")
#			print ("	WebPath: Linking web archive zip")
			run_cmd ("ln -s '" + mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory + ".zip").replace("--","-") + "'  '" + contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip'")
			dirs = []
			webpaths.append(path)
			directoryType = "html"


		#############################################################################################
		#  Final directoryType classification.
		#
		#  At this point the directoryType may still be '' if no special marker was
		#  detected.  We assign a concrete type based on the directory's position in
		#  the tree and file count:
		#    'root'       — this IS the mediaDirectory (top level)
		#    'collection' — more than 2 files: treated as a grouped series (album,
		#                   podcast, etc.) so files become episodes in a collection
		#    'singular'   — 1-2 files: treated as a standalone item
		#  Types already set (language, html, folders, folder) are left unchanged.
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
		else: directoryType = directoryType + ' singular'

		print ("	Processing Directory: " + path)
		print ("	Processing Files According To directoryType = " + directoryType)
		print ("	Processing Files According to language type= "+ language)
		print ("	--------------------------------------------------")



		##########################################################################
		#  .compress mode: create a downloadable ZIP of the directory.
		#
		#  If the file /media/usb0/content/.compress exists, any directory that
		#  contains more than one media file is eligible for ZIP packaging so
		#  users can download all files in the directory in one tap.
		#
		#  We skip this step if:
		#    • The directory is a language root (would create a ZIP of all content)
		#    • The directory already contains a compressed file (.zip, .gz, etc.)
		#      — we don't want to double-zip already-compressed content
		#    • SkipArchive is set (a web or Android archive was already created)
		#
		#  The resulting archive is stored on the USB itself so it persists across
		#  runs and can be served for download.  A symlink is placed in the
		#  web-server's zip/ directory so the interface can link to it.
		##########################################################################
		if ((('collection' in directoryType) or (len(files) > 1)) and not(language in directoryType) and (os.path.isfile(mediaDirectory + "/" + ".compress")) and (SkipArchive == 0)):
			print("        Looking to create a zip file of directory, thisDirectory:Looking to create a zip file of directory, thisDirectory: "+ thisDirectory, directoryType)
			# Make a symlink to the file on USB to display the content
			x = 0 													#This is a compressed file test flag
			for filename in files:
				if ((pathlib.Path(path + "/" + filename).suffix).lower() in '.zip, .gzip, .zy, .gz, .gzip, .7z, .bz2, .tar'): x = 1  #We found a compressed file
			if (x==0):												#Were ok to go forward with creating a compressed file of this directory
				print ("	Path: Writing symlink to /html folder")
				run_cmd ("ln -s '" + path + "' '" + contentDirectory + "/" + language + "/html/" + thisDirectory + "'")
				print ("        Path is equal to: " + path)

				if doesRootContainLanguage:
					print ("looking at: " + mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-'))
					if not os.path.isfile(mediaDirectory + "/" + language + "/" + thisDirectory + ("/archive-" + language + "-" + thisDirectory + ".zip").replace('--','-')):
						logging.info ("trying to create a zip file of " + mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")

						update_display('Creating ZIP'+chr(10)+"File")

						try:
							print ("	Path: Creating archive zip file on USB")
							shutil.make_archive(mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
							print ("	Path: Linking archive zip")
							run_cmd ('ln -s '+ mediaDirectory + "/" + language + "/" + thisDirectory +  "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
							logging.info ("succeeded in finishing the zip file")
						except Exception as e:
							print ("	error  making archive")

						update_display('Indexing USB')
				else:
					print ("looking at: " + mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")
					if not os.path.isfile(mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip"):
						logging.info ("trying to create a zip file of " + mediaDirectory + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory + ".zip")

						update_display('Creating ZIP'+chr(10)+"File")

						try:
							print ("	Path: Creating archive zip file on USB")
							shutil.make_archive(mediaDirectory + "/archive-" + language + "-" + thisDirectory, 'zip', path)
							print ("	Path: Linking web archive zip")
							run_cmd ('ln -s '+ mediaDirectory + "/archive-" + language + "-" + thisDirectory + '.zip  ' + contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip")
							logging.info ("succeeded in finishing the zip file")
						except Exception as e:
							print ("	error  making archive")

						update_display('Indexing USB')

				if (str(files).find("archive-" + language + "-" + thisDirectory + '.zip') < 0): files.append( "archive-" + language + "-" + thisDirectory + '.zip')
			else:
				print("files in directory contain .zip extensions Ignoring data compresssion request.")
				logging.info("Directory: " + mediaDirectory + " contains a Compressed file so we won't try to zip it for easy download")


		###########################################################################
		#  Per-file processing loop.
		#
		#  Iterate over every file in the current directory.  For each file we:
		#    1. Skip files that belong to web archives (only index.html and
		#       AndroidManifest.xml are processed within web paths).
		#    2. Determine the file extension and look it up in types.json.
		#    3. Build a JSON content/episode object from the appropriate template.
		#    4. Resolve a thumbnail image (user-supplied, auto-generated from video
		#       via ffmpeg, extracted from audio ID3 tags, or a type-default icon).
		#    5. Write the content JSON to contentDirectory and create a media symlink.
		#    6. Append the item to mains[language] (singular) or to the collection's
		#       episodes list (collection directoryType).
		##########################################################################

		for filename in files:
			print ("	--------------------------------------------------")
			print ("	Processing File: " + filename)
			print ("	Processing according to language " + language)

			##########################################################################
			#  File pre-screening.
			#
			#  Skip files that should not be individually indexed:
			#    • Files inside a webpath that are not the entry-point (index.html /
			#      AndroidManifest.xml) — they are already bundled in a web archive.
			#    • Files with no extension or an extension not present in types.json
			#      — we have no way to render them in the interface.
			##########################################################################

			# Skip all files in a web path not named index.html because we just build an item for the index
			if (path in webpaths and ((filename != 'index.htm') and (filename != 'index.html') and (filename != 'AndroidManifest.xml'))):
				print ("	Webpath file " + filename + " is not index or AndrodManifest so skip")
				continue

			# Get certain data about the file and path
			fullFilename = path + "/" + filename									# Example /media/usb0/content/video.mp4
			shortName = pathlib.Path(path + "/" + filename).stem							# Example  video      (ALSO, slug is a term used in the BoltCMS mediabuilder that I'm adapting here)
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
			#  JSON template selection: collection vs. singular.
			#
			#  A 'collection' directory (>2 files) uses the item.json template for
			#  the parent container and episode.json for each individual file, so
			#  the interface can display them as an expandable series (e.g. a folder
			#  of podcast episodes grouped under one tile).
			#
			#  A singular/root/language/html directory uses item.json for each file
			#  directly — each file becomes its own top-level tile.
			#
			#  'collection' is created once (first file in the directory) and then
			#  reused for subsequent files via the locals()/globals() check.
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
			#  Web content entry-point override.
			#
			#  For index.html and AndroidManifest.xml the 'file' we expose to the
			#  interface is actually the ZIP archive of the entire site/app — the
			#  individual HTML/XML file is not useful on its own.  We override:
			#    • slug  → the parent directory name (the site/app identifier)
			#    • mimeType → application/zip (the downloadable archive)
			#    • filename → slug + ".zip"
			#    • image → a type-appropriate icon (www.png, app.png, folders.png)
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
			#  MIME type resolution (three-tier fallback).
			#
			#  1. Already set (e.g. overridden to application/zip for web content).
			#  2. types.json lookup — the project-curated mapping of extensions to
			#     MIME types, preferred because it handles ConnectBox-specific types
			#     and edge cases the standard library does not know about.
			#  3. Python mimetypes library — system-level MIME detection.
			#  4. Final fallback: application/octet-stream (binary download).
			##########################################################################

			print ("	Determining Mimetype of " + extension)
			if (content["mimeType"]):
				print ("	mimeType already determined to be " + content["mimeType"])
			elif ("mimeType" in types[extension]):
				content["mimeType"] = types[extension]["mimeType"]
				print ("	mimetypes types.json says: " + content["mimeType"])
			elif (mimetypes.guess_type(fullFilename)[0] is not None):
				content["mimeType"] = mimetypes.guess_type(fullFilename)[0]
				print ("	mimetypes modules says: " + content["mimeType"])
			else:
				content["mimeType"] = "application/octet-stream"
				print ("	Default mimetype: " + content["mimeType"])
				if 'collection' in locals(): collection['image'] = 'apps.png'

			print("        Media Type is: "+ content["mediaType"])

			##########################################################################
			#  Thumbnail resolution (priority order).
			#
			#  ConnectBox thumbnails are stored on the USB with the naming convention
			#  .thumbnail-<lang>-<slug>.png (hidden files so they don't appear as
			#  content items).  Resolution priority:
			#
			#  1. User-supplied .thumbnail-<lang>-<slug>.png on the USB root.
			#     These are hand-crafted and always preferred over auto-generated ones.
			#  2. For image files: the image itself IS the thumbnail.  We symlink it
			#     into the images/ directory rather than copying.
			#  3. For video files: ffmpeg extracts a frame at multiple time offsets
			#     (15s, 30s, 1m, 2m, 3m) and is_blank_thumbnail() rejects solid-
			#     colour frames (black leader, white fade) until a usable frame is
			#     found.  The result is cached as .thumbnail-<lang>-<slug>.png on the
			#     USB so subsequent runs skip ffmpeg entirely.
			#  4. For audio files: ffmpeg extracts embedded cover art (-c:v copy).
			#     Falls back to sound.png if no embedded art exists.
			#  5. Default type icons (video.png, sound.png, book.png, etc.) when no
			#     media-specific thumbnail can be obtained.
			##########################################################################

			# Look for user generateed  thumbnail.  If there is one, use it.
			if (((content["image"] == 'blank.gif') or (content['image'] == "")) and (os.path.isfile(mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"))):
				print ("	Found Thumbnail" +  mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png")
				content["image"] =  slug + ".png"
				shutil.copy(mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png', contentDirectory + '/' + language + '/images/' + slug + '.png')
				print ("	Thumbnail copy complete at: " + contentDirectory + '/' + language + '/images/' + slug + '.png')
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
						run_cmd ("ln -s '" + fullFilename + "'  " + contentDirectory + "/" + language + "/images/")
					else:
						print (str(os.path.getsize(path + "/" + filename)) + " is the size we got for the image " + path + "/" + filename)
						content['image'] = 'images.png'
				except Exception as e:
					print (" Ok we had an error tryuging to ge the size of " + path + "/" + filename)
					run_cmd ("ln -s '" + fullFilename + "'  " + contentDirectory + "/" + language + "/images/")
				if ('collection' in locals() or 'collection' in globals()) and collection['image'] == 'blank.gif': collection['image'] = "images.png"


			# If this is a video, we can probably make a thumbnail
			if ((content["mediaType"] == 'video') and (content["image"] == 'blank.gif')):

				# Try multiple time offsets because the first few seconds of a video
				# are often a black leader or title card.  is_blank_thumbnail() validates
				# that the extracted frame has enough visual content before accepting it.
				# The thumbnail is cached on the USB so this expensive ffmpeg pass only
				# runs once per file even across multiple mmiLoader invocations.
				try:
					thumb_path = mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"
					if not os.path.isfile(thumb_path):
						print ("	Attempting to make a thumbnail for the video")
						for ts in ["00:00:15", "00:00:30", "00:01:00", "00:02:00", "00:03:00"]:
							run_cmd("/usr/bin/ffmpeg -y -i " + shlex.quote(fullFilename) + " -an -ss " + ts + " -vframes 1 " + shlex.quote(thumb_path) + " >/dev/null 2>&1")
							if os.path.isfile(thumb_path) and os.path.getsize(thumb_path) > 100:
								if not is_blank_thumbnail(thumb_path):
									print("	Thumbnail extracted at " + ts)
									break
								print("	Frame at " + ts + " is blank or uniform, trying next time point")
								os.remove(thumb_path)
					if os.path.isfile(thumb_path):
						content["image"] = slug + ".png"
						print ("        We found the thumbnail")
					try:
						if os.path.getsize(thumb_path) > 100:
							shutil.copy(thumb_path, contentDirectory + '/' + language + '/images/' + slug + '.png')
							content["image"] = slug + ".png"
						else:
							print ("        Image was too small to use!!!!!!!")
							content["image"] = 'video.png'
					except Exception as e:
						print ("had an error getting size of video !!!!!!!!" + thumb_path)
						content['image'] = 'video.png'
				except Exception as e:
					print ("Something whent wrong with the ffmpeg or elsewhere")
					content['image'] = 'video.png'
																# if its not a video & not an image
				if ('collection' in locals() or 'collection' in globals()) and (collection['image'] == 'blank.gif' or collection['image'] != 'video.png'):
					if content['image'] != 'video.png': collection['image'] = content['image']
					else: collection['image'] = "video.png"

			# if this is an audio file, we can probably get an image from the mp3
			if ((content["mediaType"] == 'audio') and (content["image"] == 'blank.gif')):
				# Use ffmpeg to extract embedded cover art from the audio file's ID3/APE
				# tags (-c:v copy streams the video (cover art) stream without re-encoding).
				# If no embedded art exists, ffmpeg exits non-zero and the thumbnail file
				# is not created, so we fall back to the generic sound.png icon.
				print("        Were looking for " + ".thumbnail-" + language + "-" + slug + ".png")
				if not os.path.isfile( mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"):
					try:
						run_cmd("/usr/bin/ffmpeg -y -i " + shlex.quote(fullFilename) + " -an -c:v copy " + shlex.quote(mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png") + "  >/dev/null 2>&1")
						if os.path.isfile(mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"):
							content["image"]= slug + ".png"
							if (os.path.getsize( mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png') > 100):
								print("mp3 thumbnail image created")
								shutil.copy(mediaDirectory + '/.thumbnail-' + language + '-' + slug + '.png', contentDirectory + '/' + language + '/images/' + slug + '.png')
								if os.path.isfile(contentDirectory + '/' + language + '/images/' + slug + '.png'):
									print ("	Thumbnail image copy complete at: " + contentDirectory + '/' + language + '/images/' + slug + '.png')
								else:
									print ("       Thumbnail image did not get linked...or created.  ?????? What to do????? ")
									raise Exception("fail")
							else:
								print ("NO mp3 thumbnail created")
								raise Exception("fail")
					except Exception as e: content["image"] = "sound.png"
				if ('collection' in locals() or 'collection' in globals()) and (collection['image'] == 'blank.gif' or collection['image'] != "sound.png"): collection['image'] = "sound.png"

			##########################################################################
			# Thumbnail resolution complete.
			##########################################################################

			# -------------------------------------------------------------------------
			# Default icon fallback for each media type.
			#
			# If no specific thumbnail was resolved (image is still blank.gif), assign
			# a type-appropriate default icon.  These icons are shipped with the
			# enhanced interface templates and provide a recognisable visual cue in the
			# library grid even when no artwork is available.
			# -------------------------------------------------------------------------
			if ('collection' in locals() or 'collection' in globals()):
				if (content["mediaType"] in 'audio'):  collection['image'] = 'sound.png'
				elif ((content["mediaType"] in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar') and (collection['image'] == 'blank.gif')):  collection['image'] = 'zip.png'
				elif ((content["mediaType"] in 'document, text, docx, xlsx, pptx, h5p, epub') and (collection['image'] == 'blank.gif')):  collection['image'] = 'book.png'
				elif ((content['mediaType'] in 'epub') and (collection['image'] == 'blank.gif')): collection ['image'] = 'epub.png'
				elif ((content['mediaType'] in 'pdf') and (collection['image'] == 'blank.gif')): collection['image'] = 'pdf.png'
				elif ((content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg') and (collection['image'] == 'blank.gif')): collection['image'] = 'images.png'
				elif (content['mediaType'] in 'application') :
					collection['image'] = 'apps.png'
					content['title'] = content['title'] + extension
			else:
				if (content["mediaType"] in 'audio'):  content['image'] = 'sound.png'
				elif (content["mediaType"] in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar'):  content['image'] = 'zip.png'
				elif (content["mediaType"] in 'document, text, docx, xlsx, pptx, h5p, epub'):  content['image'] = 'book.png'
				elif (content['mediaType'] in 'epub'): content ['image'] = 'epub.png'
				elif (content['mediaType'] in 'pdf') : content['image'] = 'pdf.png'
				elif (content['mediaType'] in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg'):
					if ((content['image'] == "") or (content['image'] == 'blank.gif')):
						 content['image'] = 'images.png'
				elif (content['mediaType'] == 'application') :
					content['image'] = 'apps.png'
					content['title'] = content['title'] + extension

			##########################################################################
			#  Compile the JSON output: collection episode or standalone item.
			#
			#  Collection mode: append this file's content object to the collection's
			#  'episodes' list and rewrite the collection JSON file after every episode
			#  so that a partial run (e.g. interrupted by USB eject) leaves a usable
			#  (though incomplete) collection on disk.  The collection is not added to
			#  mains[language] until the directory loop ends (after all episodes are
			#  processed) to avoid writing a partial entry to main.json.
			#
			#  Singular mode: write a standalone item JSON file named by slug and
			#  immediately append its content object to mains[language]["content"]
			#  so it appears as a top-level tile in the interface.
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
			# Make a symlink to the file on USB to display the content.
			# Skip html/xml entry-point files — the directory itself is already
			# exposed via html/ and the zip archive; symlinking index.html or
			# AndroidManifest.xml into media/ produces a broken link that doesn't
			# serve correctly and pollutes the media directory.
			if not (path in webpaths and ('.htm' in extension or extension == '.xml')):
				print ("	Creating symlink for the content")
				run_cmd ('ln -s "' + fullFilename + '" "' + contentDirectory + '/' + language + '/media/"')
				print ("	Symlink: " + contentDirectory + '/' + language + '/media/' + filename)

			print ("	COMPLETE: Based on file type " + fullFilename + " added to enhanced interface for language " + language)
			# END FILE LOOP


		# -------------------------------------------------------------------------
		# Post-directory collection finalisation.
		#
		# Once all files in a 'collection' directory have been processed, append
		# the completed collection object to mains[language]["content"] so it
		# appears as a single tile in the interface grid.  Then delete the local
		# 'collection' variable so the next directory starts fresh — without this
		# del, the collection object would bleed over into the next directory's
		# file processing loop via the locals() check.
		# -------------------------------------------------------------------------
		if (('collection' in locals() or 'collection' in globals()) and ("collection" in directoryType)):
			print ("	No More Episodes / Wrap up Collection for " + thisDirectory + " by adding it to mains[language]['content'] ")
			# slug.json has already been saved so we don't need to do that.  Just write the collection to the main.json
			print ("***  appending the collection to mains now ***")
			mains[language]["content"].append(collection)
			del collection
		# END DIRECTORY LOOP

	try:
		if os.path.isfile(complex_dir):
			os.remove(complex_dir)
	except Exception as e:
		logging.debug(f"Ignored exception: {e}")

	##########################################################################
	#  Wrap-up: write final JSON files and create saved.zip.
	#
	#  At this point all content has been indexed and symlinked.  We now:
	#    1. Create base-code symlinks for regional language variants (e.g.
	#       'zh' → 'zh-CN') because the media interface strips hyphen suffixes
	#       when constructing asset paths.
	#    2. For each language that produced at least one content item:
	#         a. Write main.json (the full content index for that language).
	#         b. Write interface.json (brand/logo settings for that language).
	#         c. Build an entry for languages.json (code + native name label).
	#    3. Determine the default language (English if present, otherwise first).
	#    4. Write languages.json so the interface knows which languages are
	#       available and which to load on first visit.
	#    5. Compress the entire contentDirectory into saved.zip on the USB so
	#       future insertions of the same USB key skip the full indexing run.
	##########################################################################
	print ("*************************************************")
	print ("Completing Final Compilation of languages and items")

	# For regional variant language dirs (e.g. zh-CN), create a base-code symlink (e.g. zh -> zh-CN)
	# The media interface strips the hyphen suffix when constructing content paths.
	for lang_dir in os.listdir(contentDirectory):
		if '-' in lang_dir and os.path.isdir(contentDirectory + '/' + lang_dir):
			base = lang_dir.split('-')[0]
			base_path = contentDirectory + '/' + base
			if not os.path.exists(base_path):
				os.symlink(contentDirectory + '/' + lang_dir, base_path)
				print("Created symlink " + base + " -> " + lang_dir + " for media interface")

	# Now go through each language that we found and processed and write the interface.json and main.json for each
	languageJson = []
	for language in mains:
		# Skip languages that ended up with no content (e.g. a language directory
		# that contained only unsupported file types).  Remove the template copy
		# for 'en' specifically so an empty English directory doesn't appear in the
		# interface when the USB uses a non-English single-language layout.
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
		# Prefer the native-script name (e.g. "فارسی" for Farsi) over the English
		# name so the language picker is readable to native speakers of that language.
		try:
			languageJsonObject["text"] = languageCodes[language]["native"][0]
		except Exception as e:
			languageJsonObject ["text"] = languageCodes[language]["english"][0]

		languageJson.append(languageJsonObject)

	# -------------------------------------------------------------------------
	# Safety exit: if no language produced any content, nothing useful was
	# indexed.  Clear the display file and exit without writing saved.zip so
	# that the next USB insert triggers a full re-index rather than restoring
	# an empty archive.
	# -------------------------------------------------------------------------
	if (len(languageJson) == 0):
		print ("No valid content found on the USB.  Exiting")

		try:
			os.remove(comsFileName)
		except Exception:
			pass											#Clear the display

		try:
			run_cmd('rm '+ complex_dir)
		except Exception as e:
			logging.debug(f"Ignored exception: {e}")
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
	# Only write saved.zip if the USB is still mounted (guard against root-FS pollution)
	if not os.path.ismount(mediaDirectory.split('/content')[0]):
		print("USB no longer mounted, skipping saved.zip creation")
		sys.exit()
	run_cmd ("(cd " + contentDirectory + " && zip --symlinks -r " + zipFileName + " *)")
	# Cache the new saved.zip mtime so the next insert can detect whether it is the
	# same USB key and skip unnecessary file extraction work.
	try:
		with open("/tmp/.saved_zip_mtime", "w") as _f:
			_f.write(str(os.path.getmtime(zipFileName)))
	except Exception:
		pass
	logging.info("Finished mmiLoader.py run successfully to create the user interface and index the data contents")

	try:
		if os.path.isfile(complex_dir):
			os.remove(complex_dir)
	except Exception as e:
		logging.debug(f"Ignored exception: {e}")

	try:
		os.remove(comsFileName)
	except Exception:
		pass											#Clear the display

	print ("DONE")
	sys.exit()


if __name__ == '__main__' :

	print ("Ok now we will start the loader")

	try:
		mmiloader_code()
	finally:
		# Ensure the display overlay is always cleared on exit, even if the
		# indexer crashed or was killed, so the device does not get stuck
		# showing a "Loading USB" screen indefinitely.
		try:
			os.remove("/tmp/creating_menus.txt")
		except Exception:
			pass
