#!/usr/bin/python3
#  Loads content from USB and creates the JSON / file structure for enhanced media interface


import json
import os
import pathlib
import re
import shutil
import mimetypes
import logging
import subprocess
import sys
import time
import shlex
import signal
from indexer import *


# ── Signal / display helpers ──────────────────────────────────────────────────

def update_display(message):
	# OLED font only supports latin-1; non-ASCII chars crash the hat service.
	# Wraps long text at the last word boundary within 15 chars (128px / 8px-per-char).
	try:
		safe = message.encode('ascii', 'replace').decode('ascii')
		if '\n' not in safe and len(safe) > 15:
			wrap_at = safe.rfind(' ', 0, 16)
			if wrap_at <= 0:
				wrap_at = 15
			safe = safe[:wrap_at].rstrip() + '\n' + safe[wrap_at:].lstrip()[:15]
		with open("/tmp/creating_menus.txt", "w", encoding='utf-8') as f:
			f.write(safe)
	except Exception as e:
		logging.debug(f"Ignored exception: {e}")


_shutdown_requested = False


def _sigterm_handler(signum, frame):
	# Called when systemd stops the service (e.g. USB removed).
	global _shutdown_requested
	print("Received SIGTERM -- USB removed or service stopped, exiting cleanly")
	_shutdown_requested = True
	try:
		os.remove("/tmp/creating_menus.txt")
	except Exception:
		pass


signal.signal(signal.SIGTERM, _sigterm_handler)


def usb_is_present():
	# Returns False if USB has been removed or a shutdown was requested.
	# Called at the top of every directory/file loop iteration.
	if _shutdown_requested:
		return False
	return os.path.ismount("/media/usb0")


def run_cmd(cmd):
	try:
		subprocess.run(cmd, shell=True, check=True)
	except subprocess.CalledProcessError as e:
		logging.error(f"Command failed: {cmd}")


# ── Thumbnail helpers ─────────────────────────────────────────────────────────

def is_unusable_frame(png_path):
	# Return True if the frame is predominantly black OR predominantly white.
	# Black check: 98% of pixels below luma 32 (blackframe filter).
	# White check: invert the image then run the same test (bright pixels become dark).
	# Returns False on any error so the frame is treated as usable rather than discarded.
	try:
		r1 = subprocess.run(
			"ffmpeg -i " + shlex.quote(png_path) + " -vf blackframe=98:32 -f null - 2>&1",
			shell=True, capture_output=True, text=True, timeout=15
		)
		if "blackframe" in r1.stdout or "blackframe" in r1.stderr:
			print("    Frame is predominantly black -- skipping")
			return True
		r2 = subprocess.run(
			"ffmpeg -i " + shlex.quote(png_path) + " -vf negate,blackframe=98:32 -f null - 2>&1",
			shell=True, capture_output=True, text=True, timeout=15
		)
		if "blackframe" in r2.stdout or "blackframe" in r2.stderr:
			print("    Frame is predominantly white -- skipping")
			return True
		return False
	except Exception:
		return False


def extract_video_thumbnail(video_path, output_path):
	# Try progressive seek points until a non-black thumbnail frame is found.
	# Seeks at 1s, 5s, 15s, 30s, 60s.  Returns True if a usable frame was written.
	seek_times = ["00:00:01", "00:00:05", "00:00:15", "00:00:30", "00:01:00"]
	for seek in seek_times:
		try:
			subprocess.run(
				"ffmpeg -y -ss " + seek + " -i " + shlex.quote(video_path) + " -an -vframes 1 " + shlex.quote(output_path) + " >/dev/null 2>&1",
				shell=True, check=True
			)
		except subprocess.CalledProcessError:
			pass
		if os.path.isfile(output_path) and os.path.getsize(output_path) > 100:
			if not is_unusable_frame(output_path):
				print("    Good thumbnail frame at seek " + seek)
				return True
			print("    Black frame at seek " + seek + " -- trying later...")
		else:
			print("    No usable frame at seek " + seek + " -- video may be shorter")
	print("    Could not extract a non-black thumbnail for this video")
	return False


# ── Phase 1: Startup ──────────────────────────────────────────────────────────

def initialize_run(comsFileName):
	"""
	Prepare the system for a fresh index run.

	Drops kernel page/slab/inode caches to free maximum RAM before the heavy
	ffmpeg thumbnail pass runs.  Removes any leftover OLED display file so the
	screen starts blank, then writes the initial 'Indexing USB' status.

	Called exactly once at the top of mmiloader_code() before any file I/O.
	"""
	run_cmd("sync && echo 3 | sudo tee /proc/sys/vm/drop_caches")
	try:
		os.remove(comsFileName)
	except Exception:
		pass
	update_display('Indexing USB')


def restore_from_saved_zip(mediaDirectory, contentDirectory, templatesDirectory, comsFileName):
	"""
	Check for a saved.zip in the USB content directory or the USB root.

	saved.zip is the fast path: the previous full index run pre-computed all
	thumbnails, JSON indexes, and symlinks.  If the zip exists and its mtime
	matches the marker written at the end of the previous run, there is nothing
	new to index.  Unzipping it restores the content directory in seconds.

	Search order:
	  1. <mediaDirectory>/saved.zip  (content subdirectory on USB)
	  2. <usb_root>/saved.zip        (root of USB, alternative placement)

	After unzipping, fills in any missing template directories (en/, footer.html)
	so the interface is never partially broken.  Clears the OLED display file
	and returns True so the caller (mmiloader_code) can exit immediately.

	Returns False when no zip is present and a full index run is required.
	Deleting saved.zip from the USB forces a full re-index on next insert.
	"""
	print("	Check for saved.zip")
	usb_root = os.path.dirname(mediaDirectory.rstrip('/'))
	for zp in [os.path.join(mediaDirectory, "saved.zip"), os.path.join(usb_root, "saved.zip")]:
		if not os.path.isfile(zp):
			continue
		print("	Found saved.zip at " + zp + ". Unzipping and restoring to " + contentDirectory)
		print(" ")
		print("****If you want to reload the USB, delete the file saved.zip from the USB drive.")
		if not os.path.exists(contentDirectory):
			os.mkdir(contentDirectory, mode=0o755)
		update_display("Restoring from Backup...")
		run_cmd(f"cd {shlex.quote(contentDirectory)} && unzip {shlex.quote(zp)}")
		if not os.path.exists(contentDirectory + "/en"):
			shutil.copytree(templatesDirectory + "/en", contentDirectory + "/en")
		if not os.path.exists(contentDirectory + "/footer.html"):
			shutil.copy(templatesDirectory + "/footer.html", contentDirectory)
		print("DONE")
		time.sleep(3)
		try:
			os.remove(comsFileName)
		except Exception:
			pass
		return True
	return False


def setup_fresh_content_dir(mediaDirectory, contentDirectory, templatesDirectory):
	"""
	Remove any previously generated content directory and create a clean one
	seeded with the English template tree and footer.html.

	Always called before a full re-index (i.e. when restore_from_saved_zip
	returned False).  Removes the old directory first so stale symlinks or JSON
	files from a previous USB do not leak into the new index.

	Also ensures the media directory itself exists and is not completely empty.
	If it is empty, writes a placeholder connectbox.txt so the downstream walk
	always has at least one entry to process.

	Sets mediaDirectory permissions to 755 so mmiLoader can read any USB
	content regardless of how it was written by the original author.
	"""
	print("Creating content Directory")
	update_display('Indexing USB')
	try:
		os.mkdir(contentDirectory, mode=0o755)
	except Exception:
		run_cmd(f"rm -rf {shlex.quote(contentDirectory)}")
		os.mkdir(contentDirectory, mode=0o755)

	print("Copying the templates to the main contentDirectory")
	shutil.copytree(templatesDirectory + '/en', contentDirectory + '/en')
	shutil.copy(templatesDirectory + '/footer.html', contentDirectory)
	print("copied templates for en and footer")

	try:
		if len(os.listdir(mediaDirectory)) == 0:
			print("Directory is empty")
			with open(mediaDirectory + "/connectbox.txt", "a") as f:
				f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
	except Exception as e:
		print("Content directory issue: " + str(e))
		try:
			run_cmd("mkdir " + mediaDirectory)
			with open(mediaDirectory + "/connectbox.txt", "w") as f:
				f.write("<h2>Media Directory is Empty</h2> Please refer to the administration guide!")
		except Exception:
			print("Could not create fallback connectbox.txt -- skipping")

	run_cmd(f"chmod -R 755 {shlex.quote(mediaDirectory)}")


def load_config(templatesDirectory):
	"""
	Load all static configuration needed before the index walk begins.

	Reads five files from the templates directory and /usr/local/connectbox:
	  - brand.j2         : device branding (name, logo, enhanced logo)
	  - languageCodes.json: full ISO 639-1/IETF code table used for validation
	  - types.json       : file extension to mediaType/mimeType/icon mappings
	  - interface.json   : Angular UI strings template
	  - main.json        : per-language content list template

	Applies sanity checks to the brand record:
	  - Brand name shorter than 5 chars falls back to the system hostname.
	  - Missing or short Logo falls back to 'imgs/logo.png'.

	Populates interface['APP_NAME'] and interface['APP_LOGO'] from the brand
	record here so the same interface dict can be written verbatim to every
	language content directory at the end of the run without reopening files.

	Returns a dict with keys:
	  brand, languageCodes, types, interface, main_template
	"""
	print("going to get the language codes now")
	with open(templatesDirectory + '/languageCodes.json') as f:
		languageCodes = json.load(f)
	print("language codes loaded")

	with open('/usr/local/connectbox/brand.j2') as f:
		brand = json.load(f)
	print("brand Acquired")

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
		brand['Logo'] = "imgs/logo.png"
		logging.warning("Logo missing or too short, using default")
	else:
		print("Custom Logo: " + brand['Logo'])

	print("Building Content For " + brand['Brand'])

	with open(templatesDirectory + "/en/data/interface.json") as f:
		interface = json.load(f)
	interface["APP_NAME"] = brand["Brand"]
	if brand.get("enhancedInterfaceLogo"):
		interface["APP_LOGO"] = brand["enhancedInterfaceLogo"]
	else:
		interface["APP_LOGO"] = brand["Logo"]
	print("Brand applied")

	with open(templatesDirectory + "/en/data/types.json") as f:
		types = json.load(f)
	print("file types-mime types loaded")

	with open(templatesDirectory + "/en/data/main.json") as f:
		main_template = json.load(f)
	print("main.json loaded")

	return {
		'brand': brand,
		'languageCodes': languageCodes,
		'types': types,
		'interface': interface,
		'main_template': main_template,
	}


# ── Phase 2: Language detection ───────────────────────────────────────────────

def detect_language_dirs(mediaDirectory, languageCodes):
	"""
	Determine the default language and valid language directories at the USB
	content root.  This is called once before the main walk.

	Phase 1 — validate ISO code directory names:
	  Inspect immediate children of mediaDirectory.  Accept a directory name if
	  it appears in languageCodes (regional tags like 'zh-CN' fall back to base
	  code 'zh' for lookup).  Reject names longer than 3 characters that do not
	  contain '-' (e.g. 'media', 'docs' are not language codes).

	Phase 2 — check for a .language file:
	  If no valid language directories were found in Phase 1, read the first
	  line of <mediaDirectory>/.language as the default language code.  This
	  lets USB authors declare a language without creating ISO-named folders.

	Returns (doesRootContainLanguage, language, NoISOCodes):
	  doesRootContainLanguage — list of confirmed ISO language dir names
	  language                — effective default ('en' or from .language file)
	  NoISOCodes              — 1 if language came from .language file, 0 otherwise
	"""
	print("Check mediaDirectory for at least one language")
	language = "en"
	NoISOCodes = 1

	try:
		candidates = list(next(os.walk(mediaDirectory))[1])
	except (StopIteration, OSError):
		candidates = []

	doesRootContainLanguage = []
	for lang in candidates:
		try:
			base_lang = lang.split('-')[0]
			lookup = lang if lang in languageCodes else (base_lang if base_lang in languageCodes else None)
			if lookup is None:
				print(f"Removed '{lang}' from language candidates: not a known language code")
				continue
			if len(lang) > 3 and '-' not in lang:
				print(f"Rejecting '{lang}': too long and not a regional tag")
				continue
			doesRootContainLanguage.append(lang)
			language = lang
			NoISOCodes = 0
		except Exception as e:
			print(f"Removed '{lang}' from language candidates: {e}")

	if doesRootContainLanguage:
		print("doesRootContainLanguage is now:", doesRootContainLanguage)
		print("Root Directory Contains Languages so we skip all root level folders that aren't languages: " + json.dumps(doesRootContainLanguage))
		return doesRootContainLanguage, language, NoISOCodes

	# Phase 2: no ISO-named dirs found — check for .language file
	language = "en"
	language_file = os.path.join(mediaDirectory, ".language")
	if os.path.isfile(language_file):
		print("	Root Directory has .language file")
		try:
			with open(language_file) as f:
				lang = f.readline().strip()
			lang_key = lang if lang in languageCodes else lang.split('-')[0]
			if json.dumps(languageCodes[lang_key]):
				print(f"	Found Language from .language file: {lang}")
				logging.info(f"Found valid .language: {lang}")
				language = lang
				NoISOCodes = 1
		except Exception as e:
			print(f"Could not read .language file: {e}")
			language = "en"

	return doesRootContainLanguage, language, NoISOCodes


def find_complex_dirs(mediaDirectory, doesRootContainLanguage):
	"""
	First-pass walk to identify 'complex' directory roots — directories that act
	as containers of subdirectories rather than direct stores of media files.

	Complex directories are rendered as HTML file-browser pages (via indexer's
	process_dir) instead of being indexed as media collections in main.json.

	A root-level directory (direct child of mediaDirectory) is complex when:
	  - It has subdirectories but no content files (pure container), OR
	  - It already has an index.html from a previous indexer run.

	For non-root directories: if no content files are present but subdirectories
	exist, the directory is also marked complex.

	Language directories (names in doesRootContainLanguage) are never treated as
	complex — they are skipped so their contents are indexed normally as
	language-partitioned content.

	Returns a list of absolute paths to complex directory roots.  These are later
	passed to process_dir() and excluded from the main content walk.
	"""
	complex_lst = []

	for path, dirs, files in os.walk(mediaDirectory):
		if not usb_is_present():
			print("USB removed during language scan -- stopping")
			return complex_lst

		thisDirectory = os.path.basename(os.path.normpath(path))

		# Skip the mediaDirectory root itself — it is never a complex entry
		if path == mediaDirectory:
			continue

		files = [f for f in files if f[0] not in ('_', '.')]
		dirs[:] = [d for d in dirs if d[0] not in ('_', '.')]

		is_root_child = (path == mediaDirectory + '/' + thisDirectory)

		# Only examine immediate children of mediaDirectory in this first pass.
		# Deeper subdirectories are handled by detect_language_complex_dir during
		# the main content walk, matching the original first-pass walk behaviour.
		if not is_root_child:
			continue

		# Language dirs are not complex roots — skip them entirely
		if thisDirectory in doesRootContainLanguage:
			print("Found Language in doesRootContainLanguage: " + thisDirectory)
			continue

		# Already in a known complex subtree — skip
		if any(str(path).find(c) >= 0 for c in complex_lst):
			continue

		# No files + has dirs → pure container (classic complex structure)
		if len(dirs) > 0 and len(files) == 0:
			complex_lst.append(path)
			update_display('Highly Complex' + chr(10) + 'Filesystem')
			print("Added complex root directory (no files, subdirs only): " + str(path))
		# Has an index.html from a prior indexer run → still complex
		elif "index.html" in files:
			complex_lst.append(path)
			update_display('Highly Complex' + chr(10) + 'Filesystem')
			print("Added complex root directory (has index.html): " + str(path))
		else:
			# Check if any immediate subdir itself has subdirs (deeper nesting)
			for d in dirs:
				for _, subdirs, _ in os.walk(os.path.join(path, d)):
					if subdirs:
						complex_lst.append(path)
						update_display('Highly Complex' + chr(10) + 'Filesystem')
						print("Added complex root directory: " + str(path))
					break

	return complex_lst


# ── Phase 3: Per-language setup ───────────────────────────────────────────────

def ensure_language_dir(language, contentDirectory, templatesDirectory, mains, main_template):
	"""
	Create the content output directory for a language if it does not already
	exist, and initialise the mains accumulator for that language.

	Called the first time a new language is encountered during the main walk.
	Copies the entire English template tree to the new language directory so
	that all required JSON and asset files are present before any content items
	are written.

	For regional language tags like 'zh-CN', also creates a symlink from the
	base code directory (e.g. 'zh') to the full tag directory.  The frontend
	normalises URLs to the base code, so without this symlink content would
	resolve to a 404.

	Sets ownership to www-data so nginx can serve the generated files.
	"""
	if os.path.exists(contentDirectory + "/" + language):
		return
	print("Doing new language setup " + language + " **********************************")
	print("	Creating Directory: " + contentDirectory + "/" + language)
	shutil.copytree(templatesDirectory + '/en', contentDirectory + "/" + language)
	run_cmd(f"chown -R www-data.www-data {shlex.quote(contentDirectory + '/' + language)}")
	if '-' in language:
		base_link = contentDirectory + '/' + language.split('-')[0]
		if not os.path.exists(base_link):
			os.symlink(contentDirectory + '/' + language, base_link)
	with open(templatesDirectory + "/en/data/main.json") as f:
		mains[language] = json.load(f)


# ── Phase 4: Directory classification helpers ─────────────────────────────────

def get_folder_art(files, types):
	"""
	Scan a directory's file list to find the best folder art image.

	Priority order for directoryImage (the per-item thumbnail sentinel):
	  1. Explicit folder art filenames: folder.png, folder.jpg, cover.jpg,
	     album.art.jpg, front.jpg  (these win regardless of position in list)
	  2. Any .png / .jpg / .gif file that does not start with '.thumbnail'

	collectionCoverImage is the icon shown on the collection card.  It starts
	from directoryImage but falls back to a media-type icon (sound.png,
	video.png, pdf.png) when no explicit folder art was found.

	Returns (directoryImage, collectionCoverImage).
	directoryImage == 'blank.gif' means no folder art was found; per-item
	thumbnail logic uses this as the sentinel value to decide whether to
	extract/link a thumbnail.
	"""
	directoryImage = 'blank.gif'
	for f in files:
		if f.lower() in ['folder.png', 'folder.jpg', 'cover.jpg', 'album.art.jpg', 'front.jpg', 'index.jpg']:
			directoryImage = f
			break
		if ((".png" in f) or (".jpg" in f) or (".gif" in f)) and not f.startswith(".thumbnail"):
			directoryImage = f

	collectionCoverImage = directoryImage
	if collectionCoverImage == 'blank.gif':
		for f in files:
			ext = os.path.splitext(f)[1].lower()
			if ext in types:
				mType = types[ext]["mediaType"]
				if mType == 'audio':
					collectionCoverImage = 'sound.png'
					break
				if mType == 'video':
					collectionCoverImage = 'video.png'
					break
		if collectionCoverImage == 'blank.gif':
			collectionCoverImage = 'pdf.png'

	return directoryImage, collectionCoverImage


def detect_language_complex_dir(path, dirs, files, language, mediaDirectory, doesRootContainLanguage,
								directoryType, complex_lst, contentDirectory, templatesDirectory, mains, main_template):
	"""
	Detect complex directories that sit one level inside a language root.

	The first-pass walk (find_complex_dirs) only sees root-level directories.
	When a USB uses language subdirectories (e.g. fa/, ar/), complex dirs live
	one level deeper (e.g. fa/Complex Directory/) and are invisible to the first
	pass.  This function is called for each directory during the main content
	walk and catches them.

	A direct child of the language root with no content files but with
	subdirectories is a complex container.  process_dir() generates an
	index.html for it and for each of its immediate subdirectories that do not
	already have one.  The path is then added to complex_lst so that its
	children are suppressed from the root display.

	Returns (directoryType, complex_lst, files) — files is refreshed to include
	the newly generated index.html so later checks see an accurate file list.
	"""
	language_root_path = os.path.join(mediaDirectory, language)
	is_direct_child_of_lang_root = (os.path.dirname(path) == language_root_path)
	non_index_files = [f for f in files if f.lower() != 'index.html']

	if (doesRootContainLanguage and
			directoryType not in ('language', 'folders') and
			is_direct_child_of_lang_root and
			len(non_index_files) == 0 and len(dirs) > 0 and
			path not in complex_lst):
		print("Detected language-level complex directory: " + path)
		complex_lst.append(path)
		process_dir(path, path, "")
		for subdir in dirs:
			subdir_path = os.path.join(path, subdir)
			if not os.path.isfile(os.path.join(subdir_path, "index.html")):
				process_dir(subdir_path, subdir_path, "recursive")
		files = [f for f in os.listdir(path) if not f.startswith('.')]
		directoryType = 'folders'
		update_display('Complex' + chr(10) + 'Folder')

	return directoryType, complex_lst, files


def classify_in_complex_lst(path, complex_lst, files, directoryType, webpaths):
	"""
	Determine whether the current path is a member of (or a subpath of) a
	previously detected complex directory.

	Returns (go_forward, webpaths, directoryType):
	  go_forward == 1  : this path is not inside a complex dir, continue processing
	  go_forward == 0  : this path is a subpath of a complex dir, skip it

	When a path is the direct root of a complex entry (no further path separator
	after the complex root), it is added to webpaths and directoryType is set to
	'folders' if index.html is present.

	When a path is a deeper subpath of a complex entry (e.g. complex_root/subdir),
	go_forward is set to 0 and directoryType is cleared so the main loop skips it.
	"""
	go_forward = 1
	yy = 1

	for testPath in complex_lst:
		y = str(path).find(testPath)
		if y >= 0:
			print("Complex_lst found path in testpath, at : " + str(y))
			try:
				d = str(path)[(y + len(testPath)):]
				print("ok remainder of string is: " + d)
			except Exception:
				d = ""
				print("Hit our exception in the complex_lst test loop")
				yy = 0
				break
			if d.find("/") == -1:
				# Direct root of a complex entry
				print("This directory is a major directory of a complex one.  skip it except for index.htm*")
				webpaths.append(path)
				if "index.html" in files:
					directoryType = 'folders'
				yy = 1
				break
			else:
				# Deeper subpath of a complex entry
				directoryType = ""
				yy = 0
				break
		else:
			yy = 1

	go_forward = yy
	return go_forward, webpaths, directoryType


def check_webpath_skip(path, webpaths, directoryType):
	"""
	Determine whether the current path should be skipped because it is a
	subdirectory within an already-processed web content directory (e.g. a
	js/ or images/ folder inside a web app that has an index.html).

	go_forward is set to 0 when:
	  - The path is found as a subpath of a known webpath, AND
	  - The directory is not itself a 'folder' type (complex containers are exempt), AND
	  - The directory does not have its own index.html (top-level web apps are exempt)

	Also handles the case where index.htm exists in a non-webpath directory:
	adds it to webpaths and sets directoryType to 'html'.

	Returns (go_forward, webpaths, directoryType).
	"""
	go_forward = 1
	if not webpaths:
		return go_forward, webpaths, directoryType

	x = -1
	print("Testing for webpaths in this path", path, " : ", webpaths)
	for d in webpaths:
		x = path.find(d)
		if x >= 0 and path != d:
			print("Found webpath in path", x, " : ", path[x:])
			go_forward = 0
			break
		else:
			continue

	if x < 0 and os.path.isfile(path + "/index.htm"):
		webpaths.append(path)
		directoryType = "html"
		go_forward = 1

	return go_forward, webpaths, directoryType


def handle_web_content(path, thisDirectory, language, dirs, files, contentDirectory, mediaDirectory,
						webpaths, directoryType, SkipArchive):
	"""
	Process a directory that contains an index.html or index.htm (or a single
	HTML file), treating it as a self-contained web application.

	Actions taken:
	  1. Symlink the directory into <contentDirectory>/<language>/html/ so the
	     web server can serve it.
	  2. Create a .webarchive-<lang>-<subpath>.zip on the USB if one does not
	     already exist and a .NoWebcompress flag file is absent.  The zip lets
	     users download the whole web app for offline use.
	  3. Symlink the zip into <contentDirectory>/<language>/html/<dir>.zip.

	Language root directories are excluded: they can mix HTML with other media
	types and must not have their non-HTML files suppressed.

	Returns (directoryType, webpaths, dirs, SkipArchive).
	dirs is cleared (set to []) to prevent os.walk from descending into web app
	subdirectories (js/, css/, images/, etc.).
	"""
	is_language_root = (path == mediaDirectory + '/' + language)
	html_files_in_dir = [f for f in files if f.lower().endswith('.html') or f.lower().endswith('.htm')]
	has_web_index = os.path.isfile(path + "/index.html") or any(f.lower() in ('index.htm', 'index.html') for f in files)
	single_html_file = not has_web_index and len(html_files_in_dir) == 1

	if is_language_root or (not has_web_index and not single_html_file):
		return directoryType, webpaths, dirs, SkipArchive

	print("	" + path + " is web content")
	run_cmd(f"ln -s {shlex.quote(path)} {shlex.quote(contentDirectory + '/' + language + '/html/')}")

	x = 0
	subpath = path.replace(mediaDirectory, "")
	print("subpath is now: " + subpath)

	archive_name = (".webarchive-" + language + "-" + subpath + ".zip").replace("/", "-").replace('--', '-')
	if not os.path.isfile(mediaDirectory + "/" + archive_name) and not os.path.isfile(mediaDirectory + '/.NoWebcompress'):
		update_display('Creating ZIP' + chr(10) + "File")
		logging.info("Trying to archive a web file set for " + thisDirectory)
		try:
			print("	WebPath: Creating web archive zip file on USB for: ", subpath)
			x = 1
			shutil.make_archive(
				mediaDirectory + "/" + (".webarchive-" + language + "-" + subpath).replace("/", "-").replace('--', '-'),
				'zip', path
			)
			SkipArchive = 1
			logging.info("succeeded in finishing the zip file for " + archive_name)
		except Exception:
			print("	Error making web archive")
			x = 0
	else:
		print(("webarchive already exists " + archive_name + " or .NoWebcompress in root"))
		x = 1

	update_display('Indexing USB')

	if x > 0:
		zip_src = (mediaDirectory + "/.webarchive-" + language + "-" + subpath.replace("/", "-")).replace("--", "-") + ".zip"
		zip_dst = (contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip").replace("--", "-")
		run_cmd(f"ln -s {shlex.quote(zip_src)} {shlex.quote(zip_dst)}")
	else:
		print("No webarchive is available!!")

	if directoryType != 'language' and directoryType != 'folders':
		dirs[:] = []

	if not is_language_root:
		webpaths.append(path)

	if directoryType != 'folders' and directoryType != 'language':
		directoryType = "html"

	return directoryType, webpaths, dirs, SkipArchive


def handle_android_content(path, thisDirectory, language, dirs, files, contentDirectory, mediaDirectory,
							webpaths, directoryType):
	"""
	Process a directory that contains AndroidManifest.xml, treating it as an
	Android application package.

	Mirrors the web content handler: symlinks the directory into the html/
	output directory, creates a .webarchive zip on the USB for download, and
	symlinks the zip into the language html/ output.

	Returns (directoryType, webpaths, dirs) with dirs cleared to prevent
	os.walk from descending into the app's internal structure.
	"""
	if not os.path.isfile(path + "/AndroidManifest.xml"):
		return directoryType, webpaths, dirs

	print("	" + path + " is Android App")
	run_cmd(f"ln -s {shlex.quote(path)} {shlex.quote(contentDirectory + '/' + language + '/html/')}")
	print("    Looking for: " + mediaDirectory + "/" + (".webarchive-" + language + "-" + thisDirectory + ".zip").replace('--', '-'))

	archive_path = mediaDirectory + "/" + (".webarchive-" + language + "-" + thisDirectory + ".zip").replace('--', '-')
	if not os.path.isfile(archive_path):
		update_display('Creating ZIP' + chr(10) + "File")
		logging.info("Trying to archive an Android XML file set for " + thisDirectory)
		try:
			print("	WebPath: Creating web archive zip file on USB at: " + archive_path)
			shutil.make_archive(
				mediaDirectory + ("/.webarchive-" + language + "-" + thisDirectory).replace('--', '-'),
				"zip", path
			)
		except Exception:
			print("	error making web archive")
		logging.info("succeeded in finishing the zip file")
		update_display('Indexing USB')
	else:
		print(" Found it!!")

	zip_src = (mediaDirectory + "/.webarchive-" + language + "-" + thisDirectory + ".zip").replace("--", "-")
	zip_dst = (contentDirectory + "/" + language + "/html/" + thisDirectory + ".zip").replace("--", "-")
	run_cmd(f"ln -s {shlex.quote(zip_src)} {shlex.quote(zip_dst)}")
	dirs[:] = []
	webpaths.append(path)
	directoryType = "html"

	return directoryType, webpaths, dirs


def classify_directory_type(path, mediaDirectory, language, directoryType, files, directoryImage):
	"""
	Assign the final directoryType label for a directory that has not already
	been fully classified by earlier checks (language, html, folders).

	Classification rules (evaluated in priority order):
	  'root'       — path is the mediaDirectory itself
	  'collection' — unlabelled dir with more than 2 files (multiple items)
	  'singular'   — unlabelled dir with 2 or fewer files (one item)
	  html type    — web content dirs get directoryImage reset to avoid
	                 broken image symlinks from web app assets being used as
	                 folder art (they are never placed in images/)

	Existing labels ('language', 'folders', 'folder', 'html') pass through
	unchanged.

	Returns (directoryType, directoryImage, collectionCoverImage_override).
	collectionCoverImage_override is 'www.png' for html dirs, else None.
	"""
	cover_override = None

	if (path == mediaDirectory) and ('folder' not in directoryType):
		directoryType = directoryType + ' root'
	elif directoryType == '' and len(files) > 2:
		directoryType = directoryType + ' collection'
	elif directoryType == "" and len(files) <= 2:
		directoryType = directoryType + ' singular'
	elif 'folders' in directoryType:
		pass
	elif 'folder' in directoryType:
		pass
	elif "language" in directoryType:
		pass
	elif "html" in directoryType:
		# For web content dirs with no known folder art, fall back to www.png.
		# When folder art exists (e.g. index.jpg set by get_folder_art), preserve
		# directoryImage so the caller can symlink it into images/ and use it as
		# the card thumbnail.
		if directoryImage == 'blank.gif':
			cover_override = 'www.png'
	else:
		directoryType = directoryType + ' singular'

	return directoryType, directoryImage, cover_override


def handle_compress_dir(path, thisDirectory, language, files, mediaDirectory, contentDirectory,
						directoryType, doesRootContainLanguage, SkipArchive):
	"""
	If the USB root contains a .compress flag file, create a downloadable zip
	archive of collection directories (dirs with more than one media file).

	Skip if:
	  - The directory is a language root (language in directoryType).
	  - SkipArchive is set (a prior archive operation already ran).
	  - The directory already contains a compressed file (.zip, .gz, etc.).

	Creates the archive on the USB and symlinks it into the language zip/
	output directory.  Appends the archive filename to the files list so it
	appears in the content index as a downloadable item.

	Returns the updated files list.
	"""
	if not (('collection' in directoryType or len(files) > 1) and
			language not in directoryType and
			os.path.isfile(mediaDirectory + "/.compress") and
			SkipArchive == 0):
		return files

	print("Looking to create a zip file of directory: " + thisDirectory, directoryType)
	x = 0
	for filename in files:
		if (pathlib.Path(path + "/" + filename).suffix).lower() in '.zip, .gzip, .zy, .gz, .gzip, .7z, .bz2, .tar':
			x = 1
	if x == 1:
		print("files in directory contain .zip extensions Ignoring data compression request.")
		logging.info("Directory: " + mediaDirectory + " contains a Compressed file so we won't try to zip it")
		return files

	run_cmd(f"ln -s {shlex.quote(path)} {shlex.quote(contentDirectory + '/' + language + '/html/' + thisDirectory)}")
	print("Path is equal to: " + path)

	if doesRootContainLanguage:
		archive_base = mediaDirectory + "/" + language + "/" + thisDirectory + "/archive-" + language + "-" + thisDirectory
		archive_zip = (archive_base + ".zip").replace('--', '-')
		print("looking at: " + archive_zip)
		if not os.path.isfile(archive_zip):
			logging.info("trying to create a zip file of " + archive_zip)
			update_display('Creating ZIP' + chr(10) + "File")
			try:
				print("Path: Creating archive zip file on USB")
				shutil.make_archive(archive_base.replace('--', '-'), 'zip', path)
				zip_path = archive_zip
				zip_link = (contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip").replace("--", "-")
				run_cmd(f"ln -s {shlex.quote(zip_path)} {shlex.quote(zip_link)}")
				logging.info("succeeded in finishing the zip file")
			except Exception:
				print("error making archive")
			update_display('Indexing USB')
	else:
		archive_zip = (mediaDirectory + "/archive-" + language + "-" + thisDirectory + ".zip").replace('--', '-')
		print("looking at: " + archive_zip)
		if not os.path.isfile(archive_zip):
			logging.info("trying to create a zip file of " + mediaDirectory + "/" + thisDirectory)
			update_display('Creating ZIP' + chr(10) + "File")
			try:
				print("Path: Creating archive zip file on USB")
				shutil.make_archive(
					(mediaDirectory + "/archive-" + language + "-" + thisDirectory).replace('--', '-'),
					'zip', path
				)
				zip_path = archive_zip
				zip_link = (contentDirectory + "/" + language + "/zip/" + thisDirectory + ".zip").replace("--", "-")
				run_cmd(f"ln -s {shlex.quote(zip_path)} {shlex.quote(zip_link)}")
				logging.info("succeeded in finishing the zip file")
			except Exception:
				print("error making archive")
			update_display('Indexing USB')

	archive_entry = ("archive-" + language + "-" + thisDirectory + '.zip').replace('--', '-')
	if archive_entry not in files:
		files.append(archive_entry)

	return files


# ── Phase 5: Per-file processing ─────────────────────────────────────────────

def apply_thumbnails(content, filename, fullFilename, slug, language, mediaDirectory,
					contentDirectory, img_name, directoryImage, types):
	"""
	Attempt to attach a thumbnail image to a content item.  Tries sources in
	priority order and stops at the first usable result:

	  1. Pre-cached hidden thumbnail on USB (.thumbnail-<lang>-<slug>.png):
	     Written by a previous run; avoids re-running ffmpeg.
	  2. Image files: the file itself is the thumbnail.
	  3. Video files: extract a frame with ffmpeg, trying seek points at 1s,
	     5s, 15s, 30s, 60s.  Skips predominantly black or white frames.
	     Caches the result as .thumbnail-<lang>-<slug>.png on the USB.
	  4. Audio files: extract embedded album art with ffmpeg.  Caches the art
	     as .thumbnail-<lang>-<slug>.png on the USB.

	In all cases where a thumbnail file is produced, a symlink is placed in
	<contentDirectory>/<language>/images/ so the frontend can load it by URL.

	content['image'] is updated to the thumbnail filename or a media-type icon
	fallback.  Returns the updated content dict.
	"""
	# 1. Pre-cached thumbnail on USB
	thumb_path_on_usb = mediaDirectory + "/.thumbnail-" + language + "-" + slug + ".png"
	if ((content["image"] == directoryImage or content['image'] == "") and
			os.path.isfile(thumb_path_on_usb)):
		print("	Found Thumbnail " + thumb_path_on_usb)
		content["image"] = img_name
		thumb_dst = contentDirectory + '/' + language + '/images/' + img_name
		run_cmd(f"ln -s {shlex.quote(thumb_path_on_usb)} {shlex.quote(thumb_dst)}")
		print("	Thumbnail link complete at: " + mediaDirectory + "/" + content["image"])

	if content['image'] == "":
		content['image'] = directoryImage

	# 2. Image files use themselves as the thumbnail
	if content["mediaType"] == "image" and content["image"] == directoryImage:
		content["image"] = filename
		try:
			if os.path.getsize(fullFilename) > 100:
				run_cmd(f"ln -s {shlex.quote(fullFilename)} {shlex.quote(contentDirectory + '/' + language + '/images/')}")
			else:
				print(str(os.path.getsize(fullFilename)) + " is the size we got for the image " + fullFilename)
				content['image'] = 'images.png'
		except Exception:
			print("Error getting size of " + fullFilename)
			run_cmd(f"ln -s {shlex.quote(fullFilename)} {shlex.quote(contentDirectory + '/' + language + '/images/')}")

	# 3. Video: extract a non-black frame with ffmpeg
	if content["mediaType"] == 'video' and content["image"] == directoryImage:
		try:
			needs_extract = (
				not os.path.isfile(thumb_path_on_usb) or
				os.path.getsize(thumb_path_on_usb) <= 10240 or
				is_unusable_frame(thumb_path_on_usb)
			)
			if needs_extract:
				print("	Attempting to extract a non-black thumbnail for the video")
				if os.path.isfile(thumb_path_on_usb):
					os.remove(thumb_path_on_usb)
				extract_video_thumbnail(fullFilename, thumb_path_on_usb)
			if os.path.isfile(thumb_path_on_usb) and os.path.getsize(thumb_path_on_usb) > 100:
				thumb_dst = contentDirectory + "/" + language + "/images/" + img_name
				run_cmd("ln -s " + shlex.quote(thumb_path_on_usb) + " " + shlex.quote(thumb_dst))
				content["image"] = img_name
				print("        Thumbnail linked: " + img_name)
			else:
				# Keep folder art when extraction fails; only use generic icon when no art exists
				content["image"] = directoryImage if directoryImage != 'blank.gif' else "video.png"
		except Exception:
			print("Something went wrong extracting video thumbnail")
			content["image"] = directoryImage if directoryImage != 'blank.gif' else "video.png"

	# 4. Audio: extract embedded album art with ffmpeg
	if content["mediaType"] == 'audio' and content["image"] == directoryImage:
		print("        Looking for " + ".thumbnail-" + language + "-" + slug + ".png")
		if not os.path.isfile(thumb_path_on_usb):
			try:
				run_cmd(f"ffmpeg -y -i {shlex.quote(fullFilename)} -an -c:v copy {shlex.quote(thumb_path_on_usb)} >/dev/null 2>&1")
				if os.path.isfile(thumb_path_on_usb) and os.path.getsize(thumb_path_on_usb) > 100:
					print("mp3 thumbnail image created")
					content["image"] = img_name
					thumb_dst = contentDirectory + '/' + language + '/images/' + img_name
					run_cmd(f"ln -s {shlex.quote(thumb_path_on_usb)} {shlex.quote(thumb_dst)}")
					print("	Thumbnail image link complete at: " + thumb_path_on_usb)
				else:
					print("NO mp3 thumbnail created")
					raise Exception("fail")
			except Exception:
				content["image"] = directoryImage  # will be overwritten by fallback below

	return content


def apply_fallback_image(content, collection, extension, types, directoryImage):
	"""
	Apply a media-type-appropriate fallback icon to content and collection when
	no thumbnail was produced by apply_thumbnails.

	Called after all thumbnail attempts are exhausted.  Uses the mediaType
	string from content to select an icon from the well-known set (sound.png,
	video.png, zip.png, epub.png, doc.png, sheet.png, pdf.png, images.png,
	apps.png, www.png).

	For collection items both content['image'] and collection['image'] are
	updated: the collection card icon is set to the most appropriate type icon
	for the items it contains.

	Returns (content, collection) with images updated.  collection may be None
	for singular items.
	"""
	def _icon_for_content(content, extension, types, directoryImage):
		mt = content["mediaType"]
		img = content["image"]
		if mt == 'audio':
			# Only replace with icon when no folder art — preserve folder art as episode image
			if img == 'blank.gif': content['image'] = 'sound.png'
		elif mt == 'video':
			# Only replace with icon when no folder art — preserve folder art as episode image
			if img == 'blank.gif': content['image'] = 'video.png'
		elif mt in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar':
			if img == directoryImage: content['image'] = 'zip.png'
		elif mt in 'epub':
			if img == directoryImage: content['image'] = 'epub.png'
		elif mt in 'document, text, docx, xlsx, pptx, h5p':
			if img == directoryImage:
				if extension in ('.doc', '.docx'): content['image'] = 'doc.png'
				elif extension in ('.xls', '.xlsx', '.pptx'): content['image'] = 'sheet.png'
				else: content['image'] = 'pdf.png'
		elif mt in 'pdf':
			if img == directoryImage: content['image'] = 'pdf.png'
		elif mt in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg':
			if img in ("", directoryImage):
				content['image'] = directoryImage if directoryImage != 'blank.gif' else 'images.png'
		elif mt == 'application':
			if img == directoryImage: content['image'] = 'apps.png'
			content['title'] = content['title'] + extension
		return content

	if collection is not None:
		mt = content["mediaType"]
		cimg = collection['image']
		if mt == 'audio':
			if cimg == 'blank.gif': collection['image'] = 'sound.png'
		elif mt == 'video':
			if cimg == directoryImage or cimg != 'video.png': collection['image'] = content['image'] if content['image'] != 'video.png' else 'video.png'
		elif mt in 'zip, gzip, gz, xz, 7z, bz2, 7zip, tar':
			if cimg == directoryImage: collection['image'] = 'zip.png'
		elif mt in 'epub':
			if cimg == directoryImage: collection['image'] = 'epub.png'
		elif mt in 'document, text, docx, xlsx, pptx, h5p':
			if cimg in (directoryImage, 'pdf.png'):
				if extension in ('.doc', '.docx'): collection['image'] = 'doc.png'
				elif extension in ('.xls', '.xlsx', '.pptx'): collection['image'] = 'sheet.png'
				else: collection['image'] = 'pdf.png'
		elif mt in 'pdf':
			if cimg == directoryImage: collection['image'] = 'pdf.png'
		elif mt in 'image, img, tif, tiff, wbmp, ico, jng, bmp, svg, svgz, webp, png, jpg':
			if cimg == directoryImage: collection['image'] = 'images.png'
		elif mt == 'application':
			if cimg == directoryImage: collection['image'] = 'apps.png'
			content['title'] = content['title'] + extension

		content = _icon_for_content(content, extension, types, directoryImage)
	else:
		content = _icon_for_content(content, extension, types, directoryImage)

	return content, collection


def process_file_entry(filename, path, thisDirectory, language, directoryType, directoryImage,
						collectionCoverImage, types, templatesDirectory, mediaDirectory, contentDirectory,
						webpaths, collection):
	"""
	Process a single media file and return the content dict ready for inclusion
	in main.json (singular) or as an episode in a collection.

	Steps:
	  1. Skip files in webpaths unless they are index.html / AndroidManifest.xml.
	  2. Derive slug, img_name, extension from the filename and path.
	  3. Skip files with missing or unsupported extensions.
	  4. Load the item.json or episode.json template depending on directoryType.
	  5. Populate content fields: filename, mediaType, slug, title, mimeType.
	  6. Apply special handling for HTML and XML (web/Android) index files.
	  7. Resolve mimeType via types.json, then python mimetypes, then fallback.
	  8. Call apply_thumbnails() to attach the best available thumbnail.
	  9. Call apply_fallback_image() to set a media-type icon if no thumbnail.
	 10. For collections: initialise collection on first episode, update its
	     image and metadata, append episode, write slug.json.
	    For singular items: write slug.json and append to mains.

	Returns (content, collection).  collection is None for singular dirs.
	Symlinks the source file into <contentDirectory>/<language>/media/.
	"""
	# Skip non-index files inside webpath directories
	if (path in webpaths and
			filename not in ('index.htm', 'index.html', 'AndroidManifest.xml')):
		print("	Webpath file " + filename + " is not index or AndroidManifest so skip")
		return None, collection

	fullFilename = path + "/" + filename
	shortName = pathlib.Path(fullFilename).stem
	slug = (os.path.basename(fullFilename).replace('.', '-')).replace('--', '-')
	# Strip all non-URL-safe characters from the image filename; slug itself stays
	# unchanged since it is used for routing and data file names.
	img_name = re.sub(r'[^\w\-]', '_', slug) + ".png"
	extension = (pathlib.Path(fullFilename).suffix).lower()
	print("  Slug is now: " + slug)

	if not extension:
		print("		Skipping: Extension null: " + fullFilename)
		return None, collection
	if extension not in types:
		print("		Skipping: Extension not supported: " + fullFilename)
		return None, collection

	# Load item or episode template
	if "collection" in directoryType:
		print("** Starting a collection: Loading Collection and Episode JSON **")
		if collection is None:
			with open(templatesDirectory + "/en/data/item.json") as f:
				collection = json.load(f)
			collection["episodes"] = []
			collection['image'] = collectionCoverImage
		with open(templatesDirectory + "/en/data/episode.json") as f:
			content = json.load(f)
		content['image'] = directoryImage
	else:
		print("	Loading Item JSON")
		with open(templatesDirectory + "/en/data/item.json") as f:
			content = json.load(f)
		content['image'] = directoryImage

	# Populate core fields
	if filename != 'AndroidManifest.xml':
		content["filename"] = filename
	else:
		content["filename"] = thisDirectory
	content["mediaType"] = types[extension]["mediaType"]
	content["slug"] = slug
	content["title"] = shortName
	content["mimeType"] = types[extension].get("mimeType", "")

	# Web/Android index file handling
	if '.htm' in extension and path not in webpaths:
		print("	Skipping standalone html in non-webpath dir: " + filename)
		return None, collection

	if '.htm' in extension or extension == ".xml":
		print("	Handling index.html/AndroidManifest.xml for webpath")
		slug = os.path.basename(os.path.normpath(path))
		content["slug"] = slug
		content["mimeType"] = "application/zip"
		content["title"] = os.path.basename(os.path.normpath(path))
		content["filename"] = slug + ".zip"
		if '.htm' in extension and directoryType != 'folders' and content['image'] == 'blank.gif':
			content['image'] = "www.png"
		elif '.htm' in extension and content['image'] not in ('blank.gif', 'www.png', 'app.png', 'folder.png'):
			# Folder art found (covers both html and folders directoryType) —
			# symlink it into images/ so the frontend card thumbnail resolves.
			folder_art_src = path + "/" + content['image']
			if os.path.isfile(folder_art_src):
				img_dst = contentDirectory + '/' + language + '/images/' + content['image']
				if not os.path.exists(img_dst):
					run_cmd(f"ln -s {shlex.quote(folder_art_src)} {shlex.quote(img_dst)}")
		elif extension == '.xml' and content['image'] == 'blank.gif':
			content['image'] = "app.png"
		elif 'folders' in directoryType and content['image'] == 'blank.gif':
			content['image'] = 'folder.png'
		if "collection" in directoryType and collection is not None:
			if '.htm' in extension and collection['image'] == 'blank.gif':
				collection['image'] = "www.png"
			elif extension == '.xml' and collection['image'] == 'blank.gif':
				collection['image'] = "app.png"

	# Mime type resolution
	print("	Determining Mimetype of " + extension)
	if content["mimeType"]:
		print("	mimeType already determined to be " + content["mimeType"])
	elif types[extension].get("mimeType"):
		content["mimeType"] = types[extension]["mimeType"]
		print("	mimetypes types.json says: " + content["mimeType"])
	elif mimetypes.guess_type(fullFilename)[0] is not None:
		content["mimeType"] = mimetypes.guess_type(fullFilename)[0]
		print("	mimetypes module says: " + content["mimeType"])
	else:
		content["mimeType"] = "application/octet-stream"
		print("	Default mimetype: " + content["mimeType"])

	print("        Media Type is: " + content["mediaType"])

	# Thumbnail
	content = apply_thumbnails(
		content, filename, fullFilename, slug, language, mediaDirectory,
		contentDirectory, img_name, directoryImage, types
	)

	# Sync collection cover image from thumbnail results (video special case)
	if collection is not None and content["mediaType"] == 'video':
		if collection['image'] == directoryImage or collection['image'] != 'video.png':
			collection['image'] = content['image'] if content['image'] != 'video.png' else 'video.png'

	# Audio collection cover
	if collection is not None and content["mediaType"] == 'audio' and collection['image'] == directoryImage:
		if directoryImage != 'blank.gif':
			collection['image'] = directoryImage
		else:
			collection['image'] = 'sound.png'
	if collection is None and content["mediaType"] == 'audio' and content['image'] == directoryImage:
		if directoryImage != 'blank.gif':
			content['image'] = directoryImage
		else:
			content['image'] = 'sound.png'

	# Fallback images
	content, collection = apply_fallback_image(content, collection, extension, types, directoryImage)

	# Compile into collection or singular item
	if "collection" in directoryType:
		print("	Adding Episode to collection.json")
		if len(collection["episodes"]) == 0:
			collection['title'] = os.path.basename(os.path.normpath(path))
			collection['slug'] = 'collection-' + collection['title']
			collection['mediaType'] = content['mediaType']
			collection['mimeType'] = content['mimeType']
			if content["image"] == types[extension]["image"]:
				collection['image'] = content['image']
			elif content['image'] != "blank.gif" and collection['image'] in ('pdf.png', 'blank.gif'):
				collection['image'] = content['image']
		elif collection['mediaType'] == "application" and content['mediaType'] != "application":
			print("  Replacing collection content type with: " + content['mediaType'])
			collection['mediaType'] = content['mediaType']
		elif collection['mediaType'] != content['mediaType'] and collection['image'] == 'book.png':
			print(" Replacing collection content type with: " + content['mediaType'])
			collection['mediaType'] = content['mediaType']
			collection['image'] = content['image']

		collection["episodes"].append(content)
		with open(contentDirectory + "/" + language + "/data/" + collection['slug'] + ".json", 'w', encoding='utf-8') as f:
			json.dump(collection, f, ensure_ascii=False, indent=4)
		print("** Wrote out the collection data structure: " + collection['slug'] + " ***")
	else:
		print("	Item completed.  Writing item.json")
		with open(contentDirectory + "/" + language + "/data/" + slug + ".json", 'w', encoding='utf-8') as f:
			json.dump(content, f, ensure_ascii=False, indent=4)

	# Symlink the media file
	print("	Creating symlink for the content")
	run_cmd(f"ln -s {shlex.quote(fullFilename)} {shlex.quote(contentDirectory + '/' + language + '/media/')}")
	print("	Symlink: " + contentDirectory + '/' + language + '/media/' + filename)
	print("	COMPLETE: " + fullFilename + " added for language " + language)

	return content, collection


def process_directory_files(path, dirs, files, language, directoryType, directoryImage, collectionCoverImage,
							webpaths, types, templatesDirectory, mediaDirectory, contentDirectory, mains):
	"""
	Process all content files within a single directory during the main walk.

	Iterates over the filtered file list, calling process_file_entry() for each
	file.  Accumulates episodes into a collection dict when directoryType is
	'collection'; for all other types, appends each item directly to
	mains[language]['content'].

	collection is scoped to this function and initialised to None.  It is
	returned only if directoryType is 'collection' and at least one episode was
	added.  The caller is responsible for appending the returned collection to
	mains[language]['content'] after the directory is fully processed — this
	ensures the collection is always finalised even if the last file caused an
	early return.

	Returns the finalised collection dict, or None for non-collection directories.
	"""
	collection = None

	for filename in files:
		update_display("Processing: " + filename)
		if not usb_is_present():
			print("USB removed during file processing -- stopping")
			return collection

		print("	--------------------------------------------------")
		print("	Processing File: " + filename)
		print("	Processing according to language " + language)

		thisDirectory = os.path.basename(os.path.normpath(path))
		content, collection = process_file_entry(
			filename, path, thisDirectory, language, directoryType, directoryImage, collectionCoverImage,
			types, templatesDirectory, mediaDirectory, contentDirectory, webpaths, collection
		)

		if content is None:
			continue

		if "collection" not in directoryType:
			mains[language]["content"].append(content)

	return collection


# ── Phase 6: Output finalisation ─────────────────────────────────────────────

def finalize_output(mains, languageCodes, contentDirectory, interface, mediaDirectory,
					zipFileName, comsFileName, complex_dir):
	"""
	Write all accumulated JSON output files and create saved.zip on the USB.

	For each language that has at least one content item:
	  - Writes <contentDirectory>/<language>/data/main.json
	  - Writes <contentDirectory>/<language>/data/interface.json
	  - Adds a languages.json entry (codes, native text, default flag)

	The 'en' directory is never deleted even if it has no content items: the
	Angular frontend always needs en/data/interface.json as a UI strings
	fallback.

	After all JSON files are written, creates saved.zip from the entire
	contentDirectory tree (including symlinks via --symlinks) so the next USB
	insert can skip the full re-index.

	Clears the OLED display file on completion.
	"""
	print("*************************************************")
	print("Completing Final Compilation of languages and items")

	languageJson = []
	for language in mains:
		if len(mains[language]["content"]) == 0:
			print("Skipping Empty Content for language:" + language)
			continue
		print("Writing main.json for " + language)
		with open(contentDirectory + "/" + language + "/data/main.json", 'w', encoding='utf-8') as f:
			json.dump(mains[language], f, ensure_ascii=False, indent=4)
		print("Writing interface.json for " + language)
		with open(contentDirectory + "/" + language + "/data/interface.json", 'w', encoding='utf-8') as f:
			json.dump(interface, f, ensure_ascii=False, indent=4)

		languageJsonObject = {}
		languageJsonObject["codes"] = [language.split('-')[0] if '-' in language else language]
		lang_key = language if language in languageCodes else language.split('-')[0]
		try:
			languageJsonObject["text"] = languageCodes[lang_key]["native"][0]
		except Exception:
			languageJsonObject["text"] = languageCodes[lang_key]["english"][0]
		languageJson.append(languageJsonObject)

	if len(languageJson) == 0:
		print("No valid content found on the USB.  Exiting")
		try:
			os.remove(comsFileName)
		except Exception:
			pass
		try:
			run_cmd(f"rm -f {shlex.quote(complex_dir)}")
		except Exception:
			pass
		sys.exit()

	# Mark default language (prefer 'en', else first found)
	hasDefault = 0
	for record in languageJson:
		if record["codes"][0] == "en":
			hasDefault = 1
			record["default"] = True
	if hasDefault == 0:
		languageJson[0]["default"] = True

	print("Writing languages.json")
	with open(contentDirectory + "/languages.json", 'w', encoding='utf-8') as f:
		json.dump(languageJson, f, ensure_ascii=False, indent=4)

	if not usb_is_present():
		print("USB removed before saving zip -- skipping zip write")
		return
	print("Copying Metadata to Zip File On USB")
	run_cmd(f"cd {shlex.quote(contentDirectory)} && zip --symlinks -r {shlex.quote(zipFileName)} *")
	logging.info("Finished mmiLoader.py run successfully")

	try:
		run_cmd('rm ' + complex_dir)
	except Exception:
		pass
	try:
		os.remove(comsFileName)
	except Exception:
		pass
	print("DONE")


# ── Orchestrator ──────────────────────────────────────────────────────────────

def mmiloader_code():
	"""
	Top-level orchestrator for the USB content indexing pipeline.

	Coordinates the following phases in order:
	  1.  initialize_run        — drop caches, clear OLED display
	  2.  restore_from_saved_zip — fast path: unzip and exit if zip present
	  3.  setup_fresh_content_dir — create clean content directory from templates
	  4.  load_config           — read brand, language codes, types, interface
	  5.  detect_language_dirs  — identify ISO language folders or .language file
	  6.  find_complex_dirs     — identify folder-of-folder complex roots
	  7.  process complex dirs  — generate indexer HTML for each complex root
	  8.  Main content walk     — for each directory:
	        a. skip / classify using language and complex membership
	        b. ensure_language_dir for new languages
	        c. detect language-level complex dirs
	        d. handle web / Android content
	        e. classify directory type
	        f. handle .compress zip creation
	        g. process_directory_files → collect items / collection
	        h. append finalized collection to mains
	  9.  finalize_output       — write JSON files and saved.zip
	"""
	# Constants
	mediaDirectory    = "/media/usb0/content"
	templatesDirectory = "/var/www/enhanced/content/www/assets/templates"
	contentDirectory  = "/var/www/enhanced/content/www/assets/content"
	zipFileName       = mediaDirectory + '/saved.zip'
	comsFileName      = "/tmp/creating_menus.txt"
	complex_dir       = "/tmp/Complex_lst"
	SkipArchive       = 0

	print("loader: Starting...")
	mimetypes.init()
	logging.info("Starting a run of mmiLoader.py")

	# Phase 1
	initialize_run(comsFileName)

	# Remove old content dir before checking for zip so we start clean
	try:
		run_cmd("rm -r " + contentDirectory)
	except Exception:
		pass

	# Phase 2: fast path
	if restore_from_saved_zip(mediaDirectory, contentDirectory, templatesDirectory, comsFileName):
		exit(0)

	# Phase 3: fresh content directory
	setup_fresh_content_dir(mediaDirectory, contentDirectory, templatesDirectory)

	# Phase 4: configuration
	config = load_config(templatesDirectory)
	languageCodes = config['languageCodes']
	types         = config['types']
	interface     = config['interface']
	main_template = config['main_template']

	# Phase 5: language detection
	doesRootContainLanguage, language, NoISOCodes = detect_language_dirs(mediaDirectory, languageCodes)

	# Initialise mains with English template; additional languages are added by ensure_language_dir
	mains = {}
	with open(templatesDirectory + "/en/data/main.json") as f:
		mains["en"] = json.load(f)

	webpaths = []

	# Phase 6: complex directory detection
	complex_lst = find_complex_dirs(mediaDirectory, doesRootContainLanguage)

	if complex_lst:
		with open(complex_dir, "w", encoding='utf-8') as f:
			json.dump(complex_lst, f)
	print("We have a total of " + str(len(complex_lst)) + " complex directories heads to process")

	# Phase 7: generate HTML indexes for complex directories
	for path in complex_lst:
		process_dir(path, path, "recursive")
	print("Finished the complex directory recursion")
	if complex_lst:
		run_cmd("touch " + os.path.join(mediaDirectory, ".indexed.idx"))

	update_display("Indexing USB")

	indexed_before = os.path.isfile(os.path.join(mediaDirectory, ".indexed.idx"))

	# Phase 8: main content walk
	for path, dirs, files in os.walk(mediaDirectory):
		thisDirectory = os.path.basename(os.path.normpath(path))
		if not usb_is_present():
			print("USB removed during content index -- stopping")
			return

		print("====================================================")
		print("Evaluating Directory: " + thisDirectory)

		files = [f for f in files if f[0] not in ('_', '.')]
		dirs[:] = [d for d in dirs if d[0] not in ('_', '.')]
		files.sort()

		directoryType = ''
		directoryImage = 'blank.gif'

		# Detect language for this directory
		try:
			if (os.path.isdir(mediaDirectory + '/' + thisDirectory) and
					(mediaDirectory + '/' + thisDirectory) == path and
					thisDirectory in doesRootContainLanguage):
				print("	Directory is a valid language directory: " + thisDirectory)
				language = thisDirectory
				directoryType = "language"
		except Exception:
			pass

		# Skip non-language root dirs when language dirs exist
		if path == mediaDirectory and directoryType != "language" and doesRootContainLanguage:
			print('	Skipping because directory is not a language: ' + thisDirectory)
			continue

		# Set up new language directory if this is the first time we see it
		ensure_language_dir(language, contentDirectory, templatesDirectory, mains, main_template)
		update_display('Indexing USB')

		# Phase 8a: detect language-level complex dirs (missed by first pass)
		directoryType, complex_lst, files = detect_language_complex_dir(
			path, dirs, files, language, mediaDirectory, doesRootContainLanguage,
			directoryType, complex_lst, contentDirectory, templatesDirectory, mains, main_template
		)

		# Phase 8b: check if this path is in or under a complex entry
		go_forward_complex, webpaths, directoryType = classify_in_complex_lst(
			path, complex_lst, files, directoryType, webpaths
		)

		go_forward_web, webpaths, directoryType = check_webpath_skip(
			path, webpaths, directoryType
		)

		print("our evaluation of testing for web elements is finished we have go forward at: " +
			str(go_forward_web) + " , current directoryType is: " + directoryType +
			" yy: " + str(go_forward_complex))

		# Combine go-forward flags: both must be 1 to process this directory
		if go_forward_complex == 1 and go_forward_web == 1:
			go_forward = 1
		else:
			go_forward = 0

		# Phase 8c: folder art (before web/android detection modifies directoryType)
		directoryImage, collectionCoverImage = get_folder_art(files, types)

		# Phase 8d: web content
		directoryType, webpaths, dirs, SkipArchive = handle_web_content(
			path, thisDirectory, language, dirs, files, contentDirectory, mediaDirectory,
			webpaths, directoryType, SkipArchive
		)

		# Phase 8e: Android content
		directoryType, webpaths, dirs = handle_android_content(
			path, thisDirectory, language, dirs, files, contentDirectory, mediaDirectory,
			webpaths, directoryType
		)

		print("Directory Type is: ", directoryType)

		# Skip web subdirectories (js/, css/, images/ inside a web app)
		skipWebPath = False
		for testPath in webpaths:
			if (path.find(testPath) != -1 and
					not ('folder' in directoryType) and
					not (os.path.isfile(path + "/index.html") or 'index.htm' in str(files)) or
					go_forward <= 0):
				print("	Skipping web path: " + path)
				skipWebPath = True
				break
		if skipWebPath:
			continue

		# Phase 8f: directory type classification
		directoryType, directoryImage, cover_override = classify_directory_type(
			path, mediaDirectory, language, directoryType, files, directoryImage
		)
		if cover_override:
			collectionCoverImage = cover_override

		print("	Processing Directory: " + path)
		print("	Processing Files According To directoryType = " + directoryType)
		print("	Processing Files According to language type= " + language)
		print("	--------------------------------------------------")

		# Phase 8g: .compress zip creation
		files = handle_compress_dir(
			path, thisDirectory, language, files, mediaDirectory, contentDirectory,
			directoryType, doesRootContainLanguage, SkipArchive
		)

		# Phase 8h: process all files in this directory
		collection = process_directory_files(
			path, dirs, files, language, directoryType, directoryImage, collectionCoverImage,
			webpaths, types, templatesDirectory, mediaDirectory, contentDirectory, mains
		)

		# Always finalise collection after directory is fully processed
		if collection is not None and "collection" in directoryType:
			print("	No More Episodes / Wrap up Collection for " + thisDirectory)
			print("***  appending the collection to mains now ***")
			mains[language]["content"].append(collection)

	# Cleanup complex dir temp file
	try:
		run_cmd(f"rm -f {shlex.quote(complex_dir)}")
	except Exception:
		pass

	# Phase 9: write output
	finalize_output(mains, languageCodes, contentDirectory, interface, mediaDirectory,
					zipFileName, comsFileName, complex_dir)
	sys.exit()


if __name__ == '__main__':
	# Single-instance guard: exit if another mmiLoader is already running.
	# Uses /proc/*/cmdline inspection rather than pgrep -f to avoid false
	# positives from the parent shell that launched this script.
	try:
		f = open("/tmp/creating_menus.txt", "r", encoding="utf-8")
		print("Ok the comsFileName file is present. we can't try to load since system is doing something else")
		logging.info("Skipped mmiLoader.py since complex_dir file was present")
		sys.exit()
	except Exception:
		pass

	print("Ok now we will start the loader")
	mmiloader_code()
