#!/usr/bin/env python3
"""
Test harness for mmiLoader.py refactoring.

Creates synthetic USB content trees in a temp directory and drives the
refactored helper functions directly, verifying that the JSON output
(main.json, languages.json, interface.json, slug/*.json) is complete and
correct for each scenario.

Run:  python3 test_mmiLoader.py
"""

import contextlib
import json
import os
import shutil
import sys
import tempfile
import traceback
import types as types_module

# ── Minimal stubs so mmiLoader imports cleanly without real device files ──────

# Stub indexer.process_dir so it doesn't need actual media files
import importlib, unittest.mock

# Patch run_cmd, usb_is_present, update_display, is_unusable_frame,
# extract_video_thumbnail before importing mmiLoader

import unittest.mock as mock

# We'll import individual functions after patching the module-level calls
# by importing the file as a module with sys.path manipulation.

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Stub indexer before mmiLoader imports it
indexer_stub = types_module.ModuleType('indexer')
def _stub_process_dir(top_dir, dest_dir, opts):
	"""Write a minimal index.html so complex dir detection sees it."""
	try:
		with open(os.path.join(dest_dir, 'index.html'), 'w') as f:
			f.write('<html><body>stub</body></html>')
	except Exception as e:
		print(f"  [stub process_dir] {e}")
indexer_stub.process_dir = _stub_process_dir
sys.modules['indexer'] = indexer_stub

# The file on disk is named usr_local_connectbox_bin_mmiLoader.py — load by path
import importlib.util
_loader_path = os.path.join(SCRIPT_DIR, "usr_local_connectbox_bin_mmiLoader.py")
_spec = importlib.util.spec_from_file_location("mmiLoader", _loader_path)
mmiLoader = importlib.util.module_from_spec(_spec)
sys.modules['mmiLoader'] = mmiLoader
_spec.loader.exec_module(mmiLoader)


# ── Test infrastructure ───────────────────────────────────────────────────────

PASS = 0
FAIL = 0
ERRORS = []


def check(label, condition, detail=""):
	global PASS, FAIL
	if condition:
		print(f"  [PASS] {label}")
		PASS += 1
	else:
		print(f"  [FAIL] {label}" + (f": {detail}" if detail else ""))
		FAIL += 1
		ERRORS.append(label + (": " + detail if detail else ""))


def make_templates(base):
	"""
	Create the minimum template directory structure that mmiLoader expects
	under <base>/templates/.

	Writes:
	  templates/en/data/main.json        — empty content list
	  templates/en/data/item.json        — item template
	  templates/en/data/episode.json     — episode template
	  templates/en/data/interface.json   — UI strings template
	  templates/en/data/types.json       — file extension table
	  templates/languageCodes.json       — ISO language code table (subset)
	  templates/footer.html              — placeholder footer
	"""
	tpl = os.path.join(base, "templates")
	tpl_en_data = os.path.join(tpl, "en", "data")
	os.makedirs(tpl_en_data, exist_ok=True)

	main = {"content": [], "version": "1"}
	with open(os.path.join(tpl_en_data, "main.json"), "w") as f:
		json.dump(main, f)

	item = {
		"filename": "", "mediaType": "", "slug": "", "title": "",
		"mimeType": "", "image": "", "description": ""
	}
	with open(os.path.join(tpl_en_data, "item.json"), "w") as f:
		json.dump(item, f)

	episode = {
		"filename": "", "mediaType": "", "slug": "", "title": "",
		"mimeType": "", "image": ""
	}
	with open(os.path.join(tpl_en_data, "episode.json"), "w") as f:
		json.dump(episode, f)

	interface = {"APP_NAME": "ConnectBox", "APP_LOGO": "imgs/logo.png"}
	with open(os.path.join(tpl_en_data, "interface.json"), "w") as f:
		json.dump(interface, f)

	# Minimal types: .mp4 video, .mp3 audio, .pdf document, .jpg image
	types_data = {
		".mp4": {"mediaType": "video",    "mimeType": "video/mp4",       "image": "video.png"},
		".mp3": {"mediaType": "audio",    "mimeType": "audio/mpeg",      "image": "sound.png"},
		".pdf": {"mediaType": "document", "mimeType": "application/pdf", "image": "pdf.png"},
		".jpg": {"mediaType": "image",    "mimeType": "image/jpeg",      "image": "images.png"},
		".png": {"mediaType": "image",    "mimeType": "image/png",       "image": "images.png"},
		".html":{"mediaType": "html",     "mimeType": "text/html",       "image": "www.png"},
		".htm": {"mediaType": "html",     "mimeType": "text/html",       "image": "www.png"},
		".zip": {"mediaType": "zip",      "mimeType": "application/zip", "image": "zip.png"},
	}
	with open(os.path.join(tpl_en_data, "types.json"), "w") as f:
		json.dump(types_data, f)

	lang_codes = {
		"en": {"english": ["English"], "native": ["English"]},
		"fr": {"english": ["French"],  "native": ["Français"]},
		"ar": {"english": ["Arabic"],  "native": ["العربية"]},
		"es": {"english": ["Spanish"], "native": ["Español"]},
		"zh": {"english": ["Chinese"], "native": ["中文"]},
		"fa": {"english": ["Persian"], "native": ["فارسی"]},
	}
	with open(os.path.join(tpl, "languageCodes.json"), "w") as f:
		json.dump(lang_codes, f)

	with open(os.path.join(tpl, "footer.html"), "w") as f:
		f.write("<footer>ConnectBox</footer>")

	return tpl


def make_brand(base):
	"""Write a minimal brand.j2 and return its path."""
	brand = {
		"Brand": "TestBox",
		"Logo": "imgs/logo.png",
		"enhancedInterfaceLogo": ""
	}
	brand_path = os.path.join(base, "brand.j2")
	with open(brand_path, "w") as f:
		json.dump(brand, f)
	return brand_path


def make_content_file(path, name, size=1024):
	"""Create a dummy content file of the given size."""
	with open(os.path.join(path, name), "wb") as f:
		f.write(b'\x00' * size)


def make_content_dir(base):
	"""Create the content output directory."""
	content = os.path.join(base, "content")
	os.makedirs(content, exist_ok=True)
	return content


def patch_mmiloader(tpl_dir, brand_path, media_dir, content_dir):
	"""
	Return a context-manager that patches mmiLoader's device-specific globals
	and external calls for a test run.

	Patches:
	  - run_cmd            → no-op (no real shell commands)
	  - usb_is_present     → always True
	  - update_display     → no-op
	  - is_unusable_frame  → always False (frame is good)
	  - extract_video_thumbnail → returns False (no ffmpeg)
	  - brand.j2 path      → brand_path fixture
	"""
	return mock.patch.multiple(
		'mmiLoader',
		run_cmd=mock.DEFAULT,
		usb_is_present=mock.DEFAULT,
		update_display=mock.DEFAULT,
		is_unusable_frame=mock.DEFAULT,
		extract_video_thumbnail=mock.DEFAULT,
	)


# ── Scenario runners ──────────────────────────────────────────────────────────

def run_scenario(label, media_dir, tpl_dir, brand_path, content_dir, expect_fn):
	"""
	Run detect_language_dirs + find_complex_dirs + the main content walk
	against the given media_dir, then call expect_fn(mains, result_dir) to
	validate the output.
	"""
	print(f"\n{'='*60}")
	print(f"Scenario: {label}")
	print('='*60)

	# Patch external calls (ExitStack for Python 3.7 compatibility)
	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader, 'run_cmd', new=lambda cmd: None))
		stack.enter_context(mock.patch.object(mmiLoader, 'usb_is_present', new=mock.Mock(return_value=True)))
		stack.enter_context(mock.patch.object(mmiLoader, 'update_display', new=lambda msg: None))
		stack.enter_context(mock.patch.object(mmiLoader, 'is_unusable_frame', new=mock.Mock(return_value=False)))
		stack.enter_context(mock.patch.object(mmiLoader, 'extract_video_thumbnail', new=mock.Mock(return_value=False)))
		stack.enter_context(mock.patch('builtins.open', side_effect=_open_router(brand_path, tpl_dir)))

		try:
			# Load config
			config = mmiLoader.load_config(tpl_dir)
			languageCodes = config['languageCodes']
			types = config['types']
			interface = config['interface']
			main_template = config['main_template']

			# Language detection
			doesRootContainLanguage, language, NoISOCodes = mmiLoader.detect_language_dirs(
				media_dir, languageCodes
			)
			print(f"  Language dirs: {doesRootContainLanguage}  default={language}")

			# Complex dir detection
			complex_lst = mmiLoader.find_complex_dirs(media_dir, doesRootContainLanguage)
			print(f"  Complex dirs: {complex_lst}")

			# Initialise mains
			with open(os.path.join(tpl_dir, "en", "data", "main.json")) as f:
				mains = {"en": json.load(f)}

			# Ensure content dir exists with templates
			if os.path.exists(content_dir):
				shutil.rmtree(content_dir)
			shutil.copytree(os.path.join(tpl_dir, "en"), os.path.join(content_dir, "en"))
			shutil.copy(os.path.join(tpl_dir, "footer.html"), content_dir)

			webpaths = []

			# Run indexer for complex dirs
			for cp in complex_lst:
				_stub_process_dir(cp, cp, "recursive")

			# Main walk
			for path, dirs, files in os.walk(media_dir):
				thisDirectory = os.path.basename(os.path.normpath(path))
				files = [f for f in files if f[0] not in ('_', '.')]
				dirs[:] = [d for d in dirs if d[0] not in ('_', '.')]
				files.sort()

				directoryType = ''
				directoryImage = 'blank.gif'

				# Use os.path.join for cross-platform path comparison (Windows uses backslashes)
				try:
					if (os.path.isdir(os.path.join(media_dir, thisDirectory)) and
							os.path.normpath(os.path.join(media_dir, thisDirectory)) == os.path.normpath(path) and
							thisDirectory in doesRootContainLanguage):
						language = thisDirectory
						directoryType = "language"
				except Exception:
					pass

				if os.path.normpath(path) == os.path.normpath(media_dir) and directoryType != "language" and doesRootContainLanguage:
					continue

				mmiLoader.ensure_language_dir(language, content_dir, tpl_dir, mains, main_template)

				directoryType, complex_lst, files = mmiLoader.detect_language_complex_dir(
					path, dirs, files, language, media_dir, doesRootContainLanguage,
					directoryType, complex_lst, content_dir, tpl_dir, mains, main_template
				)

				go_fwd_c, webpaths, directoryType = mmiLoader.classify_in_complex_lst(
					path, complex_lst, files, directoryType, webpaths
				)
				go_fwd_w, webpaths, directoryType = mmiLoader.check_webpath_skip(
					path, webpaths, directoryType
				)

				directoryImage, collectionCoverImage = mmiLoader.get_folder_art(files, types)

				directoryType, webpaths, dirs, SkipArchive = mmiLoader.handle_web_content(
					path, thisDirectory, language, dirs, files, content_dir, media_dir,
					webpaths, directoryType, 0
				)
				directoryType, webpaths, dirs = mmiLoader.handle_android_content(
					path, thisDirectory, language, dirs, files, content_dir, media_dir,
					webpaths, directoryType
				)

				skipWebPath = False
				for testPath in webpaths:
					if path.find(testPath) != -1 and path != testPath and not ('folder' in directoryType):
						skipWebPath = True
						break
				if skipWebPath:
					continue

				directoryType, directoryImage, cover_override = mmiLoader.classify_directory_type(
					path, media_dir, language, directoryType, files, directoryImage
				)
				if cover_override:
					collectionCoverImage = cover_override

				collection = mmiLoader.process_directory_files(
					path, dirs, files, language, directoryType, directoryImage, collectionCoverImage,
					webpaths, types, tpl_dir, media_dir, content_dir, mains
				)

				if collection is not None and "collection" in directoryType:
					mains[language]["content"].append(collection)

			expect_fn(mains, content_dir, doesRootContainLanguage, language)

		except Exception as e:
			print(f"  [ERROR] Exception in scenario: {e}")
			traceback.print_exc()
			ERRORS.append(f"{label}: exception {e}")


def _open_router(brand_path, tpl_dir):
	"""
	Return a side_effect function for mock.patch('builtins.open') that
	redirects brand.j2 reads to the test fixture and passes everything
	else through to the real open().
	"""
	real_open = open

	def _router(path, mode='r', **kwargs):
		if str(path) == '/usr/local/connectbox/brand.j2':
			return real_open(brand_path, mode, **kwargs)
		return real_open(path, mode, **kwargs)

	return _router


# ── Test scenarios ────────────────────────────────────────────────────────────

def scenario_flat_english(base):
	"""
	Scenario 1: Flat English USB — no language dirs, just media files at root.

	Expected: one 'en' language, items for each supported file, no collections.
	"""
	media_dir = os.path.join(base, "media")
	os.makedirs(media_dir)
	make_content_file(media_dir, "video1.mp4")
	make_content_file(media_dir, "audio1.mp3")
	make_content_file(media_dir, "doc1.pdf")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		check("S1: no language dirs detected", len(doesRootContainLanguage) == 0)
		check("S1: default language is en", language == "en")
		check("S1: en mains exists", "en" in mains)
		items = mains["en"]["content"]
		check("S1: 3 items indexed", len(items) == 3, f"got {len(items)}")
		slugs = [i["slug"] for i in items]
		check("S1: video1 indexed",  any("video1" in s for s in slugs))
		check("S1: audio1 indexed",  any("audio1" in s for s in slugs))
		check("S1: doc1 indexed",    any("doc1" in s for s in slugs))
		for item in items:
			check(f"S1: {item['slug']} has mediaType", bool(item.get("mediaType")))
			check(f"S1: {item['slug']} has filename", bool(item.get("filename")))
			check(f"S1: {item['slug']} has image",    bool(item.get("image")))

	run_scenario("Flat English USB", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_language_dirs(base):
	"""
	Scenario 2: Multi-language USB with en/ and fr/ directories.

	Expected: two languages, each with their own items, no cross-contamination.
	"""
	media_dir = os.path.join(base, "media")
	en_dir = os.path.join(media_dir, "en")
	fr_dir = os.path.join(media_dir, "fr")
	os.makedirs(en_dir)
	os.makedirs(fr_dir)
	make_content_file(en_dir, "english_video.mp4")
	make_content_file(en_dir, "english_doc.pdf")
	make_content_file(fr_dir, "french_audio.mp3")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		check("S2: two language dirs detected", len(doesRootContainLanguage) == 2,
			  f"got {doesRootContainLanguage}")
		check("S2: en in language dirs", "en" in doesRootContainLanguage)
		check("S2: fr in language dirs", "fr" in doesRootContainLanguage)
		check("S2: en mains has 2 items", len(mains.get("en", {}).get("content", [])) == 2)
		check("S2: fr mains has 1 item",  len(mains.get("fr", {}).get("content", [])) == 1)
		# No cross-contamination
		en_slugs = [i["slug"] for i in mains.get("en", {}).get("content", [])]
		fr_slugs = [i["slug"] for i in mains.get("fr", {}).get("content", [])]
		check("S2: french file not in en", not any("french" in s for s in en_slugs))
		check("S2: english file not in fr", not any("english" in s for s in fr_slugs))

	run_scenario("Multi-language dirs (en + fr)", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_collection(base):
	"""
	Scenario 3: A directory with 3+ files should produce a collection with episodes.

	Expected: one collection in mains with 3 episodes, all episodes fully populated.
	"""
	media_dir = os.path.join(base, "media")
	album = os.path.join(media_dir, "MyAlbum")
	os.makedirs(album)
	make_content_file(album, "track01.mp3")
	make_content_file(album, "track02.mp3")
	make_content_file(album, "track03.mp3")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		items = mains.get("en", {}).get("content", [])
		check("S3: one collection in mains", len(items) == 1, f"got {len(items)}")
		if items:
			col = items[0]
			check("S3: collection has episodes key", "episodes" in col)
			check("S3: 3 episodes in collection", len(col.get("episodes", [])) == 3,
				  f"got {len(col.get('episodes', []))}")
			check("S3: collection has slug", bool(col.get("slug")))
			check("S3: collection has image", bool(col.get("image")))
			for ep in col.get("episodes", []):
				check(f"S3: episode {ep.get('slug')} has filename", bool(ep.get("filename")))
				check(f"S3: episode {ep.get('slug')} has mediaType", bool(ep.get("mediaType")))

	run_scenario("Collection (3 audio files in subdir)", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_singular(base):
	"""
	Scenario 4: A directory with 1 file should produce a singular item (not a collection).

	Expected: one item in mains, no episodes key.
	"""
	media_dir = os.path.join(base, "media")
	single_dir = os.path.join(media_dir, "SingleDoc")
	os.makedirs(single_dir)
	make_content_file(single_dir, "manual.pdf")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		items = mains.get("en", {}).get("content", [])
		check("S4: one item in mains", len(items) == 1, f"got {len(items)}")
		if items:
			item = items[0]
			check("S4: item is not a collection", "episodes" not in item)
			check("S4: item has filename", bool(item.get("filename")))
			check("S4: item mediaType is document", item.get("mediaType") == "document")

	run_scenario("Singular item (1 PDF in subdir)", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_language_file(base):
	"""
	Scenario 5: No language dirs but a .language file declaring 'fr'.

	Expected: language='fr', content indexed under fr, doesRootContainLanguage=[].
	"""
	media_dir = os.path.join(base, "media")
	os.makedirs(media_dir)
	with open(os.path.join(media_dir, ".language"), "w") as f:
		f.write("fr\n")
	make_content_file(media_dir, "french_video.mp4")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		check("S5: no ISO language dirs", len(doesRootContainLanguage) == 0)
		check("S5: language from .language file is fr", language == "fr",
			  f"got '{language}'")

	run_scenario(".language file declares 'fr'", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_invalid_lang_dirs(base):
	"""
	Scenario 6: Directories named 'media', 'docs', 'content' alongside a real 'en' dir.

	Expected: only 'en' in doesRootContainLanguage; 'media', 'docs', 'content' rejected.
	"""
	media_dir = os.path.join(base, "media")
	os.makedirs(os.path.join(media_dir, "en"))
	os.makedirs(os.path.join(media_dir, "media"))
	os.makedirs(os.path.join(media_dir, "docs"))
	make_content_file(os.path.join(media_dir, "en"), "file.pdf")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		check("S6: only 'en' detected", doesRootContainLanguage == ["en"],
			  f"got {doesRootContainLanguage}")
		check("S6: 'media' rejected", "media" not in doesRootContainLanguage)
		check("S6: 'docs' rejected",  "docs" not in doesRootContainLanguage)

	run_scenario("Invalid dir names alongside en/", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_unsupported_extensions(base):
	"""
	Scenario 7: Mix of supported and unsupported file extensions.

	Expected: only supported extensions (.mp4, .mp3, .pdf) produce items;
	.xyz and no-extension files are silently skipped.
	"""
	media_dir = os.path.join(base, "media")
	os.makedirs(media_dir)
	make_content_file(media_dir, "video.mp4")
	make_content_file(media_dir, "unknown.xyz")
	make_content_file(media_dir, "noextension")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		items = mains.get("en", {}).get("content", [])
		slugs = [i["slug"] for i in items]
		check("S7: video.mp4 indexed",       any("video" in s for s in slugs))
		check("S7: unknown.xyz not indexed",  not any("unknown" in s for s in slugs))
		check("S7: noextension not indexed",  not any("noextension" in s for s in slugs))

	run_scenario("Unsupported file extensions skipped", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_collection_always_finalised(base):
	"""
	Scenario 8: Verify that a collection directory always appends to mains even
	when process_directory_files returns it — the core consistency fix.

	Three files in a subdirectory → collection.  Check mains has exactly 1 entry
	(the collection) not 3 individual items.
	"""
	media_dir = os.path.join(base, "media")
	series = os.path.join(media_dir, "Series")
	os.makedirs(series)
	make_content_file(series, "ep1.mp4")
	make_content_file(series, "ep2.mp4")
	make_content_file(series, "ep3.mp4")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		items = mains.get("en", {}).get("content", [])
		check("S8: exactly 1 entry in mains (collection)", len(items) == 1,
			  f"got {len(items)} — possible collection leakage or missing finalise")
		if items:
			col = items[0]
			check("S8: entry is a collection (has episodes)", "episodes" in col)
			check("S8: 3 episodes present", len(col.get("episodes", [])) == 3)

	run_scenario("Collection always finalised in mains", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_mixed_flat_and_subdir(base):
	"""
	Scenario 9: Files at root AND in a subdirectory.

	Root files form a root-level singular/collection.
	Subdir files form their own collection.
	Expected: root files AND subdir items all appear in mains without cross-contamination.
	"""
	media_dir = os.path.join(base, "media")
	subdir = os.path.join(media_dir, "Series")
	os.makedirs(media_dir)
	os.makedirs(subdir)
	make_content_file(media_dir, "standalone.pdf")
	make_content_file(subdir, "ep1.mp3")
	make_content_file(subdir, "ep2.mp3")
	make_content_file(subdir, "ep3.mp3")

	content_dir = make_content_dir(base)
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	def expect(mains, content_dir, doesRootContainLanguage, language):
		items = mains.get("en", {}).get("content", [])
		# standalone.pdf is singular, Series is a collection → 2 top-level entries
		check("S9: 2 top-level entries in mains", len(items) == 2,
			  f"got {len(items)}: {[i.get('slug') for i in items]}")
		has_singular = any("episodes" not in i for i in items)
		has_collection = any("episodes" in i for i in items)
		check("S9: has singular item", has_singular)
		check("S9: has collection",    has_collection)

	run_scenario("Mixed root file + subdir collection", media_dir, tpl_dir, brand_path, content_dir, expect)


def scenario_load_config(base):
	"""
	Scenario 10: load_config() returns all required keys and populates interface.
	"""
	tpl_dir = make_templates(base)
	brand_path = make_brand(base)

	print(f"\n{'='*60}")
	print("Scenario: load_config() structure")
	print('='*60)

	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader, 'run_cmd', new=lambda cmd: None))
		stack.enter_context(mock.patch('builtins.open', side_effect=_open_router(brand_path, tpl_dir)))
		try:
			config = mmiLoader.load_config(tpl_dir)
			check("S10: brand key present",         "brand" in config)
			check("S10: languageCodes key present",  "languageCodes" in config)
			check("S10: types key present",          "types" in config)
			check("S10: interface key present",      "interface" in config)
			check("S10: main_template key present",  "main_template" in config)
			check("S10: interface has APP_NAME",     "APP_NAME" in config["interface"])
			check("S10: interface has APP_LOGO",     "APP_LOGO" in config["interface"])
			check("S10: brand Brand is TestBox",     config["brand"]["Brand"] == "TestBox")
			check("S10: types has .mp4",             ".mp4" in config["types"])
		except Exception as e:
			print(f"  [ERROR] {e}")
			traceback.print_exc()
			ERRORS.append(f"S10: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def scenario_usb_permissions(base):
	"""
	Scenario 11: make_usb_world_readable / get_mount_fstype.

	File modes are faked through a patched os.lstat and chmod calls are
	recorded instead of applied, so the logic is checked on any OS (Windows
	cannot represent Unix permission bits).  A real directory tree supplies the
	paths that os.walk visits.
	"""
	import stat as st
	print("\n-- Scenario 11: USB permissions on Linux filesystems --")
	usb = os.path.join(base, "usb")
	os.makedirs(os.path.join(usb, "content", "en", "private_dir"))
	for rel in ("content/en/private.mp4", "content/en/public.pdf", "content/en/script.sh",
				"content/en/private_dir/page.html", "content/en/link"):
		with open(os.path.join(usb, *rel.split("/")), "w") as f:
			f.write("x")

	def key(path):
		return os.path.normcase(os.path.normpath(path))

	modes = {
		key(usb):                                         st.S_IFDIR | 0o755,
		key(os.path.join(usb, "content")):                st.S_IFDIR | 0o755,
		key(os.path.join(usb, "content", "en")):          st.S_IFDIR | 0o711,  # traversable, not listable
		key(os.path.join(usb, "content", "en", "private_dir")): st.S_IFDIR | 0o700,
		key(os.path.join(usb, "content", "en", "private.mp4")): st.S_IFREG | 0o600,
		key(os.path.join(usb, "content", "en", "public.pdf")):  st.S_IFREG | 0o644,
		key(os.path.join(usb, "content", "en", "script.sh")):   st.S_IFREG | 0o750,
		key(os.path.join(usb, "content", "en", "private_dir", "page.html")): st.S_IFREG | 0o600,
		key(os.path.join(usb, "content", "en", "link")):  st.S_IFLNK | 0o777,  # symlink — must be skipped
	}
	chmods = {}

	def fake_lstat(path):
		return os.stat_result((modes[key(path)], 0, 0, 1, 0, 0, 0, 0, 0, 0))

	def fake_chmod(path, mode):
		chmods[key(path)] = mode
		modes[key(path)] = st.S_IFMT(modes[key(path)]) | mode

	mounts = os.path.join(base, "mounts")
	def write_mounts(fstype):
		with open(mounts, "w") as f:
			f.write("/dev/mmcblk0p2 / ext4 rw 0 0\n")
			f.write("/dev/sda1 " + usb + " " + fstype + " rw,noexec 0 0\n")

	# get_mount_fstype
	write_mounts("vfat")
	check("S11: fstype vfat detected", mmiLoader.get_mount_fstype(usb, mounts) == "vfat")
	check("S11: unmounted path gives None", mmiLoader.get_mount_fstype("/nowhere", mounts) is None)
	with open(mounts, "a") as f:
		f.write("/dev/sdb " + usb + " ext4 rw 0 0\n")
	check("S11: last (visible) mount wins", mmiLoader.get_mount_fstype(usb, mounts) == "ext4")
	check("S11: missing mounts file gives None",
		mmiLoader.get_mount_fstype(usb, os.path.join(base, "no_such_file")) is None)

	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader.os, "lstat", fake_lstat))
		stack.enter_context(mock.patch.object(mmiLoader.os, "chmod", fake_chmod))
		stack.enter_context(mock.patch.object(mmiLoader, "update_display", lambda m: None))
		present = stack.enter_context(mock.patch.object(mmiLoader, "usb_is_present", return_value=True))

		# FAT-family filesystems are never touched
		for fs in ("vfat", "exfat", "ntfs3", "fuseblk"):
			write_mounts(fs)
			check(f"S11: {fs} USB left alone", mmiLoader.make_usb_world_readable(usb, mounts) == 0 and not chmods)

		# ext4: only entries missing bits are changed
		write_mounts("ext4")
		changed = mmiLoader.make_usb_world_readable(usb, mounts)
		en = os.path.join(usb, "content", "en")
		check("S11: ext4 changed 5 entries", changed == 5, f"changed={changed} {chmods}")
		check("S11: private file -> 0644", chmods.get(key(os.path.join(en, "private.mp4"))) == 0o644)
		check("S11: private dir -> 0755", chmods.get(key(os.path.join(en, "private_dir"))) == 0o755)
		check("S11: traverse-only dir -> 0755", chmods.get(key(en)) == 0o755)
		check("S11: nested private file -> 0644", chmods.get(key(os.path.join(en, "private_dir", "page.html"))) == 0o644)
		check("S11: executable file keeps bits, others get read only",
			chmods.get(key(os.path.join(en, "script.sh"))) == 0o754)
		check("S11: already-readable file untouched", key(os.path.join(en, "public.pdf")) not in chmods)
		check("S11: symlink never chmodded", key(os.path.join(en, "link")) not in chmods)

		# Second insert of the same USB: nothing left to change
		chmods.clear()
		check("S11: re-run changes nothing", mmiLoader.make_usb_world_readable(usb, mounts) == 0 and not chmods)

		# USB pulled out mid-walk: stop without touching anything else
		modes[key(os.path.join(en, "private.mp4"))] = st.S_IFREG | 0o600
		present.return_value = False
		check("S11: removed USB stops the walk", mmiLoader.make_usb_world_readable(usb, mounts) == 0 and not chmods)


def scenario_interface_translations(base):
	"""
	Scenario 12: interface.json translations.

	The MyMemory API is faked (urlopen patched), so this checks code mapping,
	offline fallback, saving and re-using translations, re-translating changed
	English, keeping hand corrections, and the saved.zip refresh — no network.
	"""
	print("\n-- Scenario 12: interface translations --")
	codes = {
		"en": {"english": ["English"]}, "fa": {"english": ["Persian"]}, "per": {"english": ["Persian"]},
		"ar": {"english": ["Arabic"]}, "ara": {"english": ["Arabic"]}, "es": {"english": ["Castilian", "Spanish"]},
		"spa": {"english": ["Castilian", "Spanish"]}, "zh": {"english": ["Chinese"]}, "xyz": {"english": ["Nowhere"]},
	}
	check("S12: per -> fa", mmiLoader.translation_code("per", codes) == "fa")
	check("S12: ara -> ar", mmiLoader.translation_code("ara", codes) == "ar")
	check("S12: spa -> es (multi-name match)", mmiLoader.translation_code("spa", codes) == "es")
	check("S12: zh -> zh-CN", mmiLoader.translation_code("zh", codes) == "zh-CN")
	check("S12: zh-CN kept", mmiLoader.translation_code("zh-CN", codes) == "zh-CN")
	check("S12: unknown 3-letter code kept", mmiLoader.translation_code("xyz", codes) == "xyz")

	types = {".apk": {"mediaType": "application"}, ".mp4": {"mediaType": "video"}, ".zip": {"mediaType": "zip"}}
	english = {
		"APP_NAME": "MyBox", "APP_LOGO": "imgs/logo.png", "LANGUAGE_BUTTON": "Language",
		"MEDIA_TYPE": {"VIDEO": "Video", "PDF": "PDF", "ZIP": "Archive"},
		"MISSING_MEDIA_TEXT": "Line one\nLine two",
	}
	typo = {"MISSING_MEDIA_TEXT": "Were working on it\nSecond line"}
	mmiLoader.complete_interface_strings(typo, {})
	check("S12: 'Were working' typo fixed", typo["MISSING_MEDIA_TEXT"] == "We're working on it\nSecond line", typo["MISSING_MEDIA_TEXT"])
	check("S12: footer/chat strings added", typo.get("FOOTER_CONFIGURATION") == "Configuration" and typo.get("CHAT_MESSAGE") == "Type a message")
	check("S12: per is right-to-left", mmiLoader.is_rtl_language("per", codes))
	check("S12: ara is right-to-left", mmiLoader.is_rtl_language("ara", codes))
	check("S12: es/zh-CN are left-to-right", not mmiLoader.is_rtl_language("es", codes) and not mmiLoader.is_rtl_language("zh-CN", codes))
	mmiLoader.complete_interface_strings(english, types)
	check("S12: missing APPLICATION label added", english["MEDIA_TYPE"].get("APPLICATION") == "App")
	check("S12: existing labels untouched", english["MEDIA_TYPE"]["ZIP"] == "Archive")

	tdir = os.path.join(base, "translations")
	requests = []

	def fake_online(url, timeout=None):
		import urllib.parse as up
		q = up.parse_qs(up.urlparse(url).query)
		text, pair = q["q"][0], q["langpair"][0]
		requests.append((text, pair))
		body = json.dumps({"responseStatus": 200, "responseData": {"translatedText": "[" + pair[3:] + "] " + text + " &amp; co"}})
		return contextlib.closing(types_module.SimpleNamespace(read=lambda: body.encode("utf-8"), close=lambda: None))

	def fake_offline(url, timeout=None):
		requests.append(("OFFLINE", url))
		raise OSError("Network is unreachable")

	def run(lang, opener):
		requests.clear()
		mmiLoader._translation_offline = False
		with mock.patch.object(mmiLoader.urllib.request, "urlopen", opener):
			return mmiLoader.get_interface_for_language(lang, english, codes, tdir)

	check("S12: English returned unchanged", run("en", fake_offline) is english and not requests)

	out = run("per", fake_offline)
	check("S12: offline -> English text", out["LANGUAGE_BUTTON"] == "Language")
	check("S12: offline stops after first failed lookup", len(requests) == 1, str(requests))
	check("S12: offline saves no file", not os.path.exists(os.path.join(tdir, "fa.json")))

	out = run("per", fake_online)
	check("S12: online translates via fa code", out["LANGUAGE_BUTTON"] == "[fa] Language & co", out["LANGUAGE_BUTTON"])
	check("S12: HTML entities decoded", "&amp;" not in out["LANGUAGE_BUTTON"])
	check("S12: nested strings translated", out["MEDIA_TYPE"]["VIDEO"] == "[fa] Video & co")
	check("S12: added APPLICATION label translated", out["MEDIA_TYPE"]["APPLICATION"] == "[fa] App & co")
	check("S12: acronym kept", out["MEDIA_TYPE"]["PDF"] == "PDF")
	check("S12: branding kept", out["APP_NAME"] == "MyBox" and out["APP_LOGO"] == "imgs/logo.png")
	check("S12: line breaks kept", out["MISSING_MEDIA_TEXT"] == "[fa] Line one & co\n[fa] Line two & co", repr(out["MISSING_MEDIA_TEXT"]))
	check("S12: English input not modified", english["LANGUAGE_BUTTON"] == "Language")
	saved_path = os.path.join(tdir, "fa.json")
	saved = json.load(open(saved_path, encoding="utf-8")) if os.path.exists(saved_path) else {}
	check("S12: translations saved as fa.json with source English",
		saved.get("strings", {}).get("LANGUAGE_BUTTON", {}).get("en") == "Language")

	out = run("fa", fake_offline)
	check("S12: saved file reused offline (per and fa share it)", out["LANGUAGE_BUTTON"] == "[fa] Language & co" and not requests, str(requests))

	saved["strings"]["LANGUAGE_BUTTON"]["text"] = "زبان"
	with open(saved_path, "w", encoding="utf-8") as f:
		json.dump(saved, f, ensure_ascii=False)
	out = run("fa", fake_online)
	check("S12: hand correction kept", out["LANGUAGE_BUTTON"] == "زبان" and not requests, str(requests))

	english["LANGUAGE_BUTTON"] = "Choose language"
	out = run("fa", fake_online)
	check("S12: changed English is re-translated", out["LANGUAGE_BUTTON"] == "[fa] Choose language & co" and len(requests) == 1, str(requests))
	english["LANGUAGE_BUTTON"] = "Language"

	# saved.zip restore: every language folder's interface.json is rewritten
	content = os.path.join(base, "content")
	os.makedirs(content, exist_ok=True)
	with open(os.path.join(content, "languages.json"), "w", encoding="utf-8") as f:
		json.dump([{"codes": ["per"], "text": "x", "default": True}, {"codes": ["en"], "text": "English", "rtl": True}], f)
	for lang in ("en", "per"):
		os.makedirs(os.path.join(content, lang, "data"))
		with open(os.path.join(content, lang, "data", "interface.json"), "w") as f:
			json.dump({"LANGUAGE_BUTTON": "old"}, f)
	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader, "load_config", lambda t: {"interface": english, "languageCodes": codes}))
		stack.enter_context(mock.patch.object(mmiLoader, "TRANSLATIONS_DIRECTORY", tdir))
		stack.enter_context(mock.patch.object(mmiLoader.urllib.request, "urlopen", fake_offline))
		real = mmiLoader.get_interface_for_language
		stack.enter_context(mock.patch.object(mmiLoader, "get_interface_for_language",
			lambda l, i, c: real(l, i, c, tdir)))
		mmiLoader._translation_offline = False
		mmiLoader.refresh_interface_translations(content, "unused")
	per = json.load(open(os.path.join(content, "per", "data", "interface.json"), encoding="utf-8"))
	en = json.load(open(os.path.join(content, "en", "data", "interface.json"), encoding="utf-8"))
	check("S12: restore refresh translates per from saved file",
		per.get("MEDIA_TYPE", {}).get("VIDEO") == "[fa] Video & co", str(per.get("MEDIA_TYPE")))
	check("S12: restore refresh: English changed back + offline -> English, not a stale translation",
		per.get("LANGUAGE_BUTTON") == "Language", str(per.get("LANGUAGE_BUTTON")))
	check("S12: restore refresh rewrites en", en.get("LANGUAGE_BUTTON") == "Language")
	langs = {r["codes"][0]: r for r in json.load(open(os.path.join(content, "languages.json"), encoding="utf-8"))}
	check("S12: restore refresh sets rtl for per", langs["per"].get("rtl") is True and langs["per"]["default"] is True)
	check("S12: restore refresh clears wrong rtl on en", "rtl" not in langs["en"])

	# .Language file (capital L) is found
	media = os.path.join(base, "media_lang")
	os.makedirs(media)
	with open(os.path.join(media, ".Language"), "w") as f:
		f.write("per\n")
	_, lang, _ = mmiLoader.detect_language_dirs(media, codes)
	check("S12: .Language (any case) is read", lang == "per", lang)
	mmiLoader._translation_offline = False


if __name__ == '__main__':
	scenarios = [
		scenario_flat_english,
		scenario_language_dirs,
		scenario_collection,
		scenario_singular,
		scenario_language_file,
		scenario_invalid_lang_dirs,
		scenario_unsupported_extensions,
		scenario_collection_always_finalised,
		scenario_mixed_flat_and_subdir,
	]

	with tempfile.TemporaryDirectory() as tmp:
		for i, scenario in enumerate(scenarios, 1):
			sub = os.path.join(tmp, f"s{i:02d}")
			os.makedirs(sub, exist_ok=True)
			scenario(sub)

		# Scenario 10 (load_config) uses its own sub-dir
		sub10 = os.path.join(tmp, "s10")
		os.makedirs(sub10, exist_ok=True)
		scenario_load_config(sub10)

		sub11 = os.path.join(tmp, "s11")
		os.makedirs(sub11, exist_ok=True)
		scenario_usb_permissions(sub11)

		sub12 = os.path.join(tmp, "s12")
		os.makedirs(sub12, exist_ok=True)
		scenario_interface_translations(sub12)

	print(f"\n{'='*60}")
	print(f"Results: {PASS} passed, {FAIL} failed")
	if ERRORS:
		print("Failed checks:")
		for e in ERRORS:
			print(f"  - {e}")
	print('='*60)
	sys.exit(0 if FAIL == 0 else 1)
