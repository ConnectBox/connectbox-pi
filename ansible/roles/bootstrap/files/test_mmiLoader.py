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
	# Each scenario is a separate mmiLoader run: start with no media/ names used
	mmiLoader._media_names.clear()

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
		"ar": {"english": ["Arabic"]}, "ara": {"english": ["Arabic"]}, "es": {"english": ["Spanish"]},
		"spa": {"english": ["Castilian", "Spanish"]}, "zh": {"english": ["Chinese"]}, "xyz": {"english": ["Nowhere"]},
		"no": {"english": ["Norwegian"]}, "nb": {"english": ["Bokmål", "Norwegian"]}, "nn": {"english": ["Norwegian", "Nynorsk"]},
		"nor": {"english": ["Norwegian"]}, "nno": {"english": ["Norwegian", "Nynorsk"]}, "xxn": {"english": ["Norwegian", "Other"]},
	}
	check("S12: per -> fa", mmiLoader.translation_code("per", codes) == "fa")
	check("S12: ara -> ar", mmiLoader.translation_code("ara", codes) == "ar")
	check("S12: spa -> es (shares one name)", mmiLoader.translation_code("spa", codes) == "es")
	check("S12: nor -> no (exact match wins)", mmiLoader.translation_code("nor", codes) == "no")
	check("S12: nno -> nn (exact match wins)", mmiLoader.translation_code("nno", codes) == "nn")
	check("S12: ambiguous shared name kept", mmiLoader.translation_code("xxn", codes) == "xxn")
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


def scenario_zim(base):
	"""
	Scenario 13: ZIM (Kiwix) support.

	kiwix-manage is faked: subprocess.run is patched to append a <book> entry
	to the library file, the way the real tool does, with metadata from a
	table keyed by file name.  Checks the library rebuild, card files, ZIMs in
	collection folders, and cross-listing of multi-language ZIMs.
	"""
	import base64
	import xml.sax.saxutils as su
	print("\n-- Scenario 13: ZIM files --")
	tpl = make_templates(base)
	media = os.path.join(base, "usb", "content")
	content_dir = os.path.join(base, "www")
	library = os.path.join(base, "kiwix", "library.xml")
	fake_manage = os.path.join(base, "kiwix-manage")
	open(fake_manage, "w").close()
	png = base64.b64encode(b"\x89PNG fake icon").decode()
	meta = {
		"wiki_en_mini_2025-01.zim": {"title": "Wikipedia Mini", "language": "eng", "favicon": png},
		"phrasebook_multi_2025-02.zim": {"title": "Phrasebook", "language": "eng,fra,deu", "favicon": ""},
		"cuisine_fr_2025-03.zim": {"title": "Cuisine", "language": "fra", "favicon": png},
		"broken.zim": None,                     # kiwix-manage fails on this one
	}
	for rel in ("en/wiki_en_mini_2025-01.zim", "en/phrasebook_multi_2025-02.zim",
				"en/Lessons/cuisine_fr_2025-03.zim", "en/Lessons/lesson1.mp4", "en/broken.zim", ".hidden/x.zim"):
		p = os.path.join(media, *rel.split("/"))
		os.makedirs(os.path.dirname(p), exist_ok=True)
		open(p, "w").close()

	def fake_run(cmd, capture_output=True, text=True):
		lib, action, zim = cmd[1], cmd[2], cmd[3]
		info = meta[os.path.basename(zim)]
		if info is None:
			return types_module.SimpleNamespace(returncode=1, stdout="", stderr="invalid zim")
		xml = open(lib, encoding="utf-8").read()
		attrs = " ".join('%s=%s' % (k, su.quoteattr(v)) for k, v in
						 dict(info, id=os.path.basename(zim), path=zim, description="About " + info["title"]).items() if v)
		xml = xml.replace("</library>", "  <book " + attrs + " />\n</library>")
		open(lib, "w", encoding="utf-8").write(xml)
		return types_module.SimpleNamespace(returncode=0, stdout="", stderr="")

	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader.subprocess, "run", fake_run))
		stack.enter_context(mock.patch.object(mmiLoader, "update_display", lambda m: None))
		stack.enter_context(mock.patch.object(mmiLoader, "usb_is_present", lambda: True))
		books = mmiLoader.rebuild_kiwix_library(media, library, fake_manage)
	names = sorted(b["url_name"] for b in books.values())
	check("S13: library lists the good ZIMs (not broken, not hidden dirs)",
		names == ["cuisine_fr_2025-03", "phrasebook_multi_2025-02", "wiki_en_mini_2025-01"], str(names))
	check("S13: url_name is the file name without .zim", "wiki_en_mini_2025-01" in names)
	check("S13: library swapped in, no temporary file left", not os.path.exists(library + ".new"))

	# Safety net: restart kiwix-serve only if a book is still not served
	restarts = []
	def fake_restart(cmd, capture_output=True, text=True):
		restarts.append(cmd)
		return types_module.SimpleNamespace(returncode=0, stdout="", stderr="")
	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader.subprocess, "run", fake_restart))
		stack.enter_context(mock.patch.object(mmiLoader.time, "sleep", lambda s: None))
		served = {"value": set(names)}
		stack.enter_context(mock.patch.object(mmiLoader, "kiwix_served_names", lambda *a: served["value"]))
		check("S13: all books served -> no restart", mmiLoader.ensure_kiwix_serves(books) == [] and not restarts)
		served["value"] = set(names) - {"phrasebook_multi_2025-02"}
		check("S13: book still missing -> kiwix-serve restarted",
			mmiLoader.ensure_kiwix_serves(books, wait=4) == ["phrasebook_multi_2025-02"]
			and restarts == [["systemctl", "restart", "kiwix-serve"]], str(restarts))
		served["value"] = None
		restarts.clear()
		check("S13: kiwix-serve not reachable -> nothing done", mmiLoader.ensure_kiwix_serves(books) == [] and not restarts)
	catalog = ('<feed><entry><link type="text/html" href="/kiwix/content/phet_pt_all_2026-08" /></entry>'
		'<entry><link type="text/html" href="/kiwix/content/ted_mul-exercise_2026-09" /></entry></feed>')
	with mock.patch.object(mmiLoader.urllib.request, "urlopen",
			lambda url, timeout=5: contextlib.closing(types_module.SimpleNamespace(read=lambda: catalog.encode(), close=lambda: None))):
		check("S13: served names read from the catalog",
			mmiLoader.kiwix_served_names() == {"phet_pt_all_2026-08", "ted_mul-exercise_2026-09"})
	check("S13: no Kiwix installed -> nothing listed",
		mmiLoader.rebuild_kiwix_library(media, library, os.path.join(base, "missing")) == {})
	mmiLoader._zim_books = books

	# Content directory with the language folders the box has
	mains = {}
	for lang in ("en", "fr", "es"):
		for sub in ("data", "html", "images", "media"):
			os.makedirs(os.path.join(content_dir, lang, sub), exist_ok=True)
		mains[lang] = {"content": []}
	mmiLoader._zim_cards = []

	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader, "update_display", lambda m: None))
		stack.enter_context(mock.patch.object(mmiLoader, "usb_is_present", lambda: True))
		stack.enter_context(mock.patch.object(mmiLoader, "run_cmd", lambda c: None))
		mmiLoader.process_directory_files(os.path.join(media, "en"), [], ["wiki_en_mini_2025-01.zim", "phrasebook_multi_2025-02.zim", "broken.zim"],
			"en", "language", "blank.gif", "blank.gif", [], {}, tpl, media, content_dir, mains)
		collection = mmiLoader.process_directory_files(os.path.join(media, "en", "Lessons"), [], ["cuisine_fr_2025-03.zim"],
			"en", "collection", "blank.gif", "blank.gif", [], {}, tpl, media, content_dir, mains)

	cards = {c["slug"]: c for c in mains["en"]["content"]}
	wiki = cards.get("wiki_en_mini_2025-01-zim", {})
	check("S13: ZIM card made", bool(wiki), str(list(cards)))
	check("S13: card is web content with ZIM mime type", wiki.get("mediaType") == "html" and wiki.get("mimeType") == "application/x-zim")
	check("S13: card title from the ZIM", wiki.get("title") == "Wikipedia Mini")
	check("S13: card description from the ZIM", wiki.get("description") == "About Wikipedia Mini")
	check("S13: card icon from the ZIM favicon", wiki.get("image") == "wiki_en_mini_2025-01-zim.png")
	icon = os.path.join(content_dir, "en", "images", "wiki_en_mini_2025-01-zim.png")
	check("S13: icon file decoded", os.path.isfile(icon) and open(icon, "rb").read() == b"\x89PNG fake icon")
	check("S13: ZIM without favicon uses www.png", cards.get("phrasebook_multi_2025-02-zim", {}).get("image") == "www.png")
	page = os.path.join(content_dir, "en", "html", "wiki_en_mini_2025-01-zim", "index.html")
	page_html = open(page, encoding="utf-8").read() if os.path.isfile(page) else ""
	check("S13: redirect page points into Kiwix", "/kiwix/content/wiki_en_mini_2025-01/" in page_html and "location.replace" in page_html)
	check("S13: data json written", os.path.isfile(os.path.join(content_dir, "en", "data", "wiki_en_mini_2025-01-zim.json")))
	check("S13: unregistered ZIM gets no card", "broken-zim" not in cards)
	check("S13: ZIM in a collection folder is a stand-alone card",
		"cuisine_fr_2025-03-zim" in cards and collection is None)

	added = mmiLoader.cross_list_zim_cards(mains, content_dir, {
		"en": {"english": ["English"]}, "eng": {"english": ["English"]},
		"fr": {"english": ["French"]}, "fra": {"english": ["French"]},
		"de": {"english": ["German"]}, "deu": {"english": ["German"]},
		"es": {"english": ["Spanish"]}})
	fr = [c["slug"] for c in mains["fr"]["content"]]
	check("S13: multi-language ZIM also listed in fr", "phrasebook_multi_2025-02-zim" in fr, str(fr))
	check("S13: fr gets its own redirect page",
		os.path.isfile(os.path.join(content_dir, "fr", "html", "phrasebook_multi_2025-02-zim", "index.html")))
	check("S13: language not on box (de) ignored, untagged (es) untouched", not mains["es"]["content"])
	check("S13: single-language fra ZIM in en folder is NOT cross-listed", "cuisine_fr_2025-03-zim" not in fr)
	check("S13: one card added in total", added == 1, str(added))
	check("S13: cross-listing twice adds nothing",
		mmiLoader.cross_list_zim_cards(mains, content_dir, {"en": {"english": ["English"]}, "fr": {"english": ["French"]},
			"eng": {"english": ["English"]}, "fra": {"english": ["French"]}, "deu": {"english": ["German"]}}) == 0)

	# TED ZIMs open in the card's language (localStorage key read by ted2zim)
	codes = {"en": {"english": ["English"]}, "eng": {"english": ["English"]}, "zh": {"english": ["Chinese"]},
		"zho": {"english": ["Chinese"]}, "es": {"english": ["Spanish"]}, "spa": {"english": ["Castilian", "Spanish"]},
		"fr": {"english": ["French"]}}
	ted = {"tags": "_category:ted;ted;_videos:yes", "language": "eng,spa,zho", "url_name": "ted_mul_x_2026-09"}
	check("S13: TED start language zh-CN -> zh-cn", mmiLoader.ted_start_language(ted, "zh-CN", codes) == "zh-cn")
	check("S13: TED start language es", mmiLoader.ted_start_language(ted, "es", codes) == "es")
	check("S13: TED not tagged with fr -> none", mmiLoader.ted_start_language(ted, "fr", codes) is None)
	check("S13: non-TED ZIM -> none",
		mmiLoader.ted_start_language(dict(ted, tags="_category:other;_videos:yes"), "es", codes) is None)
	ted_page = mmiLoader.zim_redirect_page("ted_mul_x_2026-09", "zh-cn")
	check("S13: TED page stores the language before redirecting",
		'localStorage.setItem("ted2zim.selectedLanguage", "zh-cn")' in ted_page
		and ted_page.index("localStorage") < ted_page.index("location.replace") < ted_page.index("http-equiv"))
	check("S13: other pages store nothing", "localStorage" not in mmiLoader.zim_redirect_page("wiki_en_mini_2025-01"))
	mmiLoader._zim_books = {}
	mmiLoader._zim_cards = []


def scenario_card_icons(base):
	"""
	Scenario 14: card icons for ZIMs (card_icon_png / zim_card_icon).

	Uses two real ZIM favicons - Open Music Theory's (1-bit palette, every
	pixel transparent, i.e. empty) and Stack Exchange Cooking's (8-bit palette
	with transparency, bright) - plus synthetic icons for the dark-on-
	transparent, light-on-transparent and opaque cases.
	"""
	import base64
	print("\n-- Scenario 14: card icons --")
	OMT = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAADAAAAAwAQMAAABtzGvEAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAANQTFRFR3BMgvrS0gAAAAF0Uk5TAEDm2GYAAAANSURBVBjTY2AYBdQEAAFQAAGn4toWAAAAAElFTkSuQmCC")
	COOKING = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAMAAABg3Am1AAAA/FBMVEX///8AAACbLSWbLSWbLSWbLSWbLSWbLSWbLSWbLSWbLSWbLSWBQDmbLSWbLSWbLSWbLSWBQDmBQDmbLSWBQDmBQDmBQDmBQDmBQDmBQDmBQDmBQDmBQDmBQDmEPjeRNS2BQDmBQDns2NahOjO/TEDmt7PdoJnz5eTMcGbhq6a6b2nuz8zEWE3ViIDHiYS0Ylz///+VMirZlIzgvbu7QDPNlpLTo6CRNC2IOzT58vGONy/my8nasK3BfHfy29mZLiaLOTKbLSWEPjeGPDWQNS7qw7+DPziTMyuBQDmuVE6oR0CMODCWMSmYLyju2df78/L35+bkwL3QfHPIZFmrwVUyAAAAInRSTlMAAEDvEIAwn79gIN+/z3CvUIBAjxBgr9+f789QIHCP7zCP5M9NzAAAAYZJREFUeJztk9FPwjAQxi3DCCaQGJ6M8UHcFNwIJztNSEbMPRAHxrDE//9/sb21rB3tXo0J3wPZ6Pfr197dLi7O+r8Snbqi3RQASAQBosflkoifJ1SAFvmBHuXasCOiN37CDoB4Lf1ZmX0BMe5IiOTCAXFm3Ckipl1H2ih7ZuwLacdjlA8geQCseHmrzNicDApPlYZ5Vm/JWyMmYKlV1r4sCb0DNnLcAOuhA9Cz/n8VyyvP4VSyLRZQeBxHpdpvAaMuf902F6CA9SkEjANbc/9ibsvAAcRSW9zKICfgQQfYwGVhHdco5qFYofE7ZR3va8Am6heOOQXUWOzVPCyO/gUD6ieGnQ8Q4kWtJ01Axu/qDlM/EPFoa6JSe8uUOnLiBUS0gUQPdKXGELcmrl0lo0GCsXf6QsC1HtdZ1ephHgDExvnGLIUACgDrfgCI/MA6CiX0Mh+Qj/x9UFK3PrT8pNe8QHFyJvosy9ubIED7uQ3k9F0a3XkBIR7KV6r18VU2urcTzvpz/QInBqmz3lM0rQAAAABJRU5ErkJggg==")

	w, h, px = mmiLoader.png_decode_rgba(COOKING)
	check("S14: decodes 8-bit palette + tRNS PNG", (w, h, len(px)) == (48, 48, 2304))
	check("S14: bright icon on transparent kept", mmiLoader.card_icon_png(COOKING) == COOKING)
	w, h, px = mmiLoader.png_decode_rgba(OMT)
	check("S14: decodes 1-bit palette PNG", (w, h) == (48, 48) and all(p[3] == 0 for p in px))
	check("S14: empty icon -> None (use www.png)", mmiLoader.card_icon_png(OMT) is None)
	check("S14: ZIM with empty favicon has no icon",
		mmiLoader.zim_card_icon({"favicon": base64.b64encode(OMT).decode()}) is None)
	check("S14: ZIM without favicon has no icon", mmiLoader.zim_card_icon({}) is None)

	W = H = 16
	def square(colour):
		return [colour if 4 <= x < 12 and 4 <= y < 12 else (0, 0, 0, 0) for y in range(H) for x in range(W)]
	dark = mmiLoader.png_encode_rgba(W, H, square((20, 20, 20, 255)))
	out = mmiLoader.card_icon_png(dark)
	fw, fh, fp = mmiLoader.png_decode_rgba(out)
	check("S14: dark icon on transparent flattened onto white",
		out != dark and fp[0] == (255, 255, 255, 255) and fp[8 * W + 8] == (20, 20, 20, 255) and (fw, fh) == (W, H))
	light = mmiLoader.png_encode_rgba(W, H, square((250, 250, 250, 255)))
	check("S14: light icon on transparent kept", mmiLoader.card_icon_png(light) == light)
	opaque = mmiLoader.png_encode_rgba(W, H, [(30, 30, 30, 255)] * (W * H))
	check("S14: opaque dark icon kept", mmiLoader.card_icon_png(opaque) == opaque)
	check("S14: unreadable data returned unchanged", mmiLoader.card_icon_png(b"not a png") == b"not a png")
	half = mmiLoader.png_encode_rgba(W, H, [(0, 0, 0, 128 if (x + y) % 2 else 0) for y in range(H) for x in range(W)])
	check("S14: semi-transparent dark icon flattened",
		mmiLoader.png_decode_rgba(mmiLoader.card_icon_png(half))[2][1] == (127, 127, 127, 255))


def scenario_duplicate_names(base):
	"""
	Scenario 15: files with the same name in different folders.

	A different file with an already-used name gets its own media/ link name
	and slug (folder added); an identical copy shares the existing link; files
	that never collide keep their names.
	"""
	print("\n-- Scenario 15: duplicate file names across folders --")
	mmiLoader._media_names.clear()
	media = os.path.join(base, "usb", "content")

	def put(rel, data):
		p = os.path.join(media, *rel.split("/"))
		os.makedirs(os.path.dirname(p), exist_ok=True)
		with open(p, "wb") as f:
			f.write(data)
		return p

	a = put("en/Series A/Lesson01.mp3", b"A" * 200000)
	b = put("en/Series B/Lesson01.mp3", b"B" * 200000)                  # different content
	copy = put("en/Series A copy/Lesson01.mp3", b"A" * 200000)          # identical to A
	tail = put("en/Series C/Lesson01.mp3", b"A" * 150000 + b"C" * 50000)   # same size, different end
	b2 = put("en/Other/Series B/Lesson01.mp3", b"D" * 200000)           # different, same folder name as B
	solo = put("en/Series A/Only.mp3", b"O" * 10)
	other_lang = put("es/Series B/Lesson01.mp3", b"E" * 10)

	u = mmiLoader.unique_media_name
	check("S15: first file keeps its name", u("en", "Lesson01.mp3", a) == "Lesson01.mp3")
	check("S15: same file again keeps its name", u("en", "Lesson01.mp3", a) == "Lesson01.mp3")
	check("S15: different file gets folder-qualified name", u("en", "Lesson01.mp3", b) == "Lesson01--Series_B.mp3")
	check("S15: identical copy shares the first file's name", u("en", "Lesson01.mp3", copy) == "Lesson01.mp3")
	check("S15: same size but different ending is not a copy", u("en", "Lesson01.mp3", tail) == "Lesson01--Series_C.mp3")
	check("S15: second different file from a same-named folder gets -2",
		u("en", "Lesson01.mp3", b2) == "Lesson01--Series_B-2.mp3")
	check("S15: repeat of a renamed file reuses its name", u("en", "Lesson01.mp3", b) == "Lesson01--Series_B.mp3")
	check("S15: names are per language", u("es", "Lesson01.mp3", other_lang) == "Lesson01.mp3")
	check("S15: non-colliding file keeps its name", u("en", "Only.mp3", solo) == "Only.mp3")

	# Through process_directory_files: two collection folders, links and slugs
	mmiLoader._media_names.clear()
	tpl = make_templates(os.path.join(base, "t"))
	content_dir = os.path.join(base, "www")
	for sub in ("data", "html", "images", "media"):
		os.makedirs(os.path.join(content_dir, "en", sub), exist_ok=True)
	mains = {"en": {"content": []}}
	types = {".mp3": {"image": "sound.png", "mediaType": "audio", "category": "Audios", "mimeType": "audio/mpeg"}}
	links = []
	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader, "run_cmd", lambda c: links.append(c) if c.startswith("ln -s") else None))
		stack.enter_context(mock.patch.object(mmiLoader, "update_display", lambda m: None))
		stack.enter_context(mock.patch.object(mmiLoader, "usb_is_present", lambda: True))
		cols = []
		# Stand-in for the link the first file creates (run_cmd is mocked)
		open(os.path.join(content_dir, "en", "media", "Lesson01.mp3"), "w").close()
		for folder in ("Series A", "Series B", "Series A copy"):
			col = mmiLoader.process_directory_files(os.path.join(media, "en", folder), [], ["Lesson01.mp3"],
				"en", "collection", "blank.gif", "blank.gif", [], types, tpl, media, content_dir, mains)
			cols.append(col)
	eps = [c["episodes"][0] for c in cols]
	check("S15: card titles stay the original file name", all(e["title"] == "Lesson01" for e in eps), str([e["title"] for e in eps]))
	check("S15: Series B episode links its own file",
		eps[1]["filename"] == "Lesson01--Series_B.mp3" and any("media/Lesson01--Series_B.mp3'" in c and "Series B/" in c for c in links), str(links))
	check("S15: Series B episode has its own slug", eps[1]["slug"] != eps[0]["slug"], eps[1]["slug"])
	check("S15: no second link attempted for the identical copy",
		not any("Series A copy/" in c for c in links), str(links))
	check("S15: identical copy shares Series A's link and slug",
		eps[2]["filename"] == "Lesson01.mp3" and eps[2]["slug"] == eps[0]["slug"])
	mmiLoader._media_names.clear()


def scenario_clear_menus(base):
	"""
	Scenario 16: mmiLoader --clear (clear_menus) after the USB is removed.
	"""
	print("\n-- Scenario 16: clear menus on USB removal --")
	tpl = make_templates(base)
	with open(os.path.join(tpl, "languages.json"), "w") as f:
		json.dump([{"text": "English", "codes": ["en-US", "en"], "default": True}], f)
	content = os.path.join(base, "content")
	for lang in ("en", "ar", "zh-CN"):
		os.makedirs(os.path.join(content, lang, "data"), exist_ok=True)
		with open(os.path.join(content, lang, "data", "main.json"), "w") as f:
			json.dump({"content": [{"slug": "old-card"}]}, f)
	with open(os.path.join(content, "languages.json"), "w") as f:
		json.dump([{"codes": ["ar"], "text": "x", "default": True}], f)
	marker = os.path.join(base, "creating_menus.txt")
	open(marker, "w").close()
	english = {"APP_NAME": "MyBox", "LANGUAGE_BUTTON": "Language"}
	with contextlib.ExitStack() as stack:
		stack.enter_context(mock.patch.object(mmiLoader, "run_cmd",
			lambda c: shutil.rmtree(content, ignore_errors=True) if c.startswith("rm -rf") else None))
		stack.enter_context(mock.patch.object(mmiLoader, "load_config",
			lambda t: {"interface": dict(english, FOOTER_CONFIGURATION="Configuration"), "languageCodes": {"en": {"english": ["English"]}}}))
		mmiLoader.clear_menus(content, tpl, marker)
	left = sorted(os.listdir(content))
	check("S16: only the empty English menu is left", left == ["en", "footer.html", "languages.json"], str(left))
	main = json.load(open(os.path.join(content, "en", "data", "main.json")))
	check("S16: no cards", main.get("content") == [], str(main))
	langs = json.load(open(os.path.join(content, "languages.json")))
	check("S16: default languages.json (English)", langs[0]["text"] == "English" and langs[0]["default"] is True)
	iface = json.load(open(os.path.join(content, "en", "data", "interface.json")))
	check("S16: English interface written with branding", iface.get("APP_NAME") == "MyBox" and iface.get("FOOTER_CONFIGURATION") == "Configuration")
	check("S16: stale 'indexing' marker removed", not os.path.exists(marker))


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

		sub13 = os.path.join(tmp, "s13")
		os.makedirs(sub13, exist_ok=True)
		scenario_zim(sub13)

		sub14 = os.path.join(tmp, "s14")
		os.makedirs(sub14, exist_ok=True)
		scenario_card_icons(sub14)

		sub15 = os.path.join(tmp, "s15")
		os.makedirs(sub15, exist_ok=True)
		scenario_duplicate_names(sub15)

		sub16 = os.path.join(tmp, "s16")
		os.makedirs(sub16, exist_ok=True)
		scenario_clear_menus(sub16)

	print(f"\n{'='*60}")
	print(f"Results: {PASS} passed, {FAIL} failed")
	if ERRORS:
		print("Failed checks:")
		for e in ERRORS:
			print(f"  - {e}")
	print('='*60)
	sys.exit(0 if FAIL == 0 else 1)
