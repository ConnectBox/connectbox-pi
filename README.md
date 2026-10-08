[![Build Status](https://travis-ci.org/ConnectBox/connectbox-pi.svg?branch=master)](https://travis-ci.org/ConnectBox/connectbox-pi)

# ConnectBox

ConnectBox is an offline media-sharing appliance: a small single-board computer that
runs its own WiFi access point with a captive portal and serves media from a USB
drive through a web interface, with no internet connection needed. To build one, see
[docs/deployment.md](docs/deployment.md).

## mmiLoader — USB Content Indexer

`mmiLoader.py` (deployed to `/usr/local/connectbox/bin/mmiLoader.py` by the `bootstrap` role) scans USB content and builds the JSON/file structure used by the enhanced media interface.

### USB insert behaviour

| Scenario | Behaviour |
|---|---|
| No `saved.zip` on the USB | Full index walk — scans all files, extracts thumbnails, writes JSON, creates `saved.zip` at end |
| `saved.zip` on the USB (in `content/` or the USB root) | Content directory is wiped and `saved.zip` is extracted in full (fast); no indexing |
| `saved.zip` deleted from USB | Falls through to full index walk |
| USB removed | Menus are cleared to the empty English page (`mmiLoader.py --clear`, run by PxUSBm) and Kiwix stops serving the USB's ZIM files |

After a `saved.zip` restore, mmiLoader also rewrites every language's `interface.json`
(translations) and the right-to-left flags in `languages.json`, because the zip holds the
versions from when it was made.

To force a full re-index on a USB key that already has `saved.zip`, delete `saved.zip` from the USB drive.

### Visitors during indexing

A full index rebuilds the menus from scratch (minutes on a large USB). While it runs, anyone opening the menu gets a small **"Loading new content"** page with a progress count ("340 / 778") instead of an empty menu. The visitor's language is not known before the menu loads, so the message is shown in every language on the USB (English first), using the same translations as the menus (`INDEXING_TITLE`, `INDEXING_TEXT`: shipped for Arabic, Spanish, Farsi, Portuguese and Chinese, looked up online for other languages when the box is online, otherwise English). The page refreshes itself every 20 seconds (to `/?reload=<time>`, an address no browser has cached) and gives way to the menu as soon as the menus are written. The app's start page is sent with `Cache-Control: no-cache`, so browsers check with the box instead of reusing an old copy. mmiLoader writes the page to `/tmp/connectbox-indexing.html` and removes it at the end (also on any exit, on SIGTERM, by `--clear`, and at reboot as `/tmp` is tmpfs); nginx serves it for `/` and `/index.html` only while the file exists, so admin, chat, Kiwix and media keep working. A `saved.zip` restore takes seconds and shows no page.

### OLED display messages during indexing

| Message | Meaning |
|---|---|
| `Checking USB Permissions` | Linux-formatted USB (ext4 etc.): making files readable by the web server |
| `Loading USB` | Checking for `saved.zip` |
| `Unzipping USB` | Restoring from `saved.zip` (fast path) |
| `Indexing USB` | Full index walk in progress |
| `Creating ZIP File` | Compressing a web archive directory |
| `Highly Complex Filesystem` | Complex HTML directory structure detected |

### Video thumbnail extraction

Thumbnails are extracted from video files using `ffmpeg`. mmiLoader tries frames at 15 s, 30 s, 1 min, 2 min, and 3 min, skipping any frame that is predominantly black, white, or a near-uniform solid colour (detected via grayscale mean and standard deviation). The first usable frame is saved as a hidden `.thumbnail-<lang>-<slug>.png` on the USB drive so it is not re-extracted on subsequent runs.

### Language support

Regional language variants (e.g. `zh-CN`, `pt-BR`) on the USB are handled by aliasing the base code (`zh`, `pt`) to the full variant directory. The media interface always requests content using the base code, so this symlink ensures the correct content is served.

Language folders and `.language` may use 2- or 3-letter codes; `per` and `fa` are both Farsi, `ara` and `ar` both Arabic. Right-to-left languages (Arabic, Farsi, Hebrew, Urdu, ...) are flagged `"rtl": true` in `languages.json`, which flips the interface. The language button on the home page shows the active language's own name (e.g. فارسی).

A first-time visitor starts in the first of their browser's preferred languages that the box has (exact match such as `pt-BR`, otherwise the same base language, `pt`); if the box has none of them, the default language from `languages.json` is used. A language picked with the language button is remembered and always wins.

### Interface translations

The app's own text (section titles, media types, the footer's Configuration link, chat labels) comes from each language's `interface.json`. Upstream only has English, so mmiLoader writes each language's file from `/usr/local/connectbox/translations/<code>.json`:

1. Reviewed files are shipped by Ansible for Farsi, Arabic, Spanish, Portuguese and Chinese (`ansible/roles/bootstrap/files/translations/`).
2. For any other language, if the box has internet, the English text is translated online (MyMemory) and saved there, so it keeps working offline afterwards.
3. With no internet, English is shown and the lookup is retried on the next USB insert.

Online translations of short interface words are often poor; check new files in `/usr/local/connectbox/translations/` and correct the `text` values (corrections are kept). A string is re-translated only when its English changes.

### Web content and ZIM pages: getting back to the menu

Every page inside web content (HTML folders) and ZIM files shows a small round house button in the bottom-left corner that returns to the ConnectBox menu in the visitor's language. nginx adds it as pages are served; the content itself is not changed. Links inside web content that point to pages missing from the USB go back to that item's start page instead of a blank page.

### ZIM files (offline websites)

Put `.zim` files (from https://library.kiwix.org) in a language folder on the USB, e.g. `content/en/wikipedia_en_100_2025-01.zim`. Each one becomes a card in that language with the ZIM's own title and icon (a dark icon is put on a white background so it shows on the dark cards; an empty one is replaced by the standard web icon), and opens in Kiwix; a ZIM tagged with several languages also appears in its other languages that are on the box. A ZIM placed directly in `content/` (not in a language folder) gets no card. TED ZIMs open in the language of the menu they were opened from instead of TED's English default; other multi-language ZIMs open in their own default language. Search inside a ZIM is Kiwix's own. Files over 4 GB need an exFAT or ext4 USB. After adding ZIMs to a USB that already has `saved.zip`, delete `saved.zip` so the USB is re-indexed.

### Word documents (.docx)

Word files on the USB are shown as web pages, so phones without an office app can read them. When the USB is indexed, mmiLoader converts each `.docx` with [mammoth](https://github.com/mwilliamson/python-mammoth) (installed by Ansible) into `<lang>/html/<slug>/index.html`, with its images saved beside it. Like a PDF, the card opens a details page with a book button, which opens that page (with the home button) in the same tab, and a download button for the original `.docx`. Text, headings, lists, tables, images and links are kept; exact layout is not (headers and footers, text boxes, columns). A folder of Word files is still a collection, and each document has its own book and download buttons. Old `.doc` files and any `.docx` that cannot be converted stay download-only. For documents whose layout matters, save them as PDF before copying them to the USB.

### Spreadsheets (.xlsx, .xls)

Spreadsheets are shown as web pages the same way as Word files: mmiLoader reads `.xlsx` with [openpyxl](https://openpyxl.readthedocs.io/) and old `.xls` with [xlrd](https://xlrd.readthedocs.io/) (both installed by Ansible) and writes one table per visible sheet, with links between sheets. Cells show the values Excel last saved (formulas show their result); charts, images, colours and number formats are not kept. A sheet is cut at 2,000 rows (the page says how many rows there are), so pages stay quick on phones and on the box; the download button gives the whole file. The card has an XLSX/XLS icon and opens a details page with the book and download buttons, like PDFs and Word files.

### Presentations (.pptx)

PowerPoint files are shown as web pages too, read with Python's standard library (no extra package): one numbered section per visible slide with its title, text (bullet levels kept), pictures, tables and the speaker notes under a translated "Speaker notes" label (`SLIDE_NOTES` in the translation files), and slide-number links at the top. The slide design (backgrounds, positions, colours, animations, charts, diagrams) is not kept, so for decks where the look matters save them as PDF in PowerPoint before copying them to the USB. Old `.ppt` files stay download-only. The stock file-type table had no PowerPoint entries, so Ansible adds `.pptx` and `.ppt` to `types.json`.

### Download sizes

Every download button (details page and the viewers' top bar) shows the file's size, for example "412 MB", so users know how big a download is before they start it. The app asks the box for the size (a HEAD request, headers only) when the button appears; if the size cannot be found the button is shown without it. Added by `patch_download_size.py` when the enhanced interface is installed.

### USB file systems

`PxUSBm.py` is the only USB mounter (it polls `lsblk` every ~3 s). It mounts FAT32, exFAT and NTFS sticks, and Linux file systems (ext2/3/4, xfs, btrfs, f2fs), including sticks formatted on the whole disk with no partition table (`mkfs.ext4 /dev/sdX`). Use ext4 or exFAT for files over 4 GB (FAT32's limit).

On Linux file systems, files keep the owner and permissions of the computer that wrote them, which can stop the web server reading them (cards show but open with 403). mmiLoader therefore adds read permission for everyone (like `chmod -R a+rX`, skipping symlinks and never adding execute to files) before indexing. Only files missing permission are changed, so re-inserting the same stick is quick.

### Starting the indexer and single-instance guard

`PxUSBm.py` starts mmiLoader on the poll after `/media/usb0` is mounted, in the transient systemd unit `connectbox-loader`, and stops it when the USB is removed. The sentinel `/tmp/.usb0_indexed` stops it re-running on every poll. mmiLoader refuses to start while a run is in progress, marked by `/tmp/creating_menus.txt` (removed at the end of a run, when the run is stopped, and by `--clear`).

## OpenWell — content packages from a server

Besides USB sticks, a box can get its menus and media from a **content package** on a
ConnectBox server. Packages are made in [MediaBuilder](https://github.com/ConnectBox/mediabuilder)
(a Bolt CMS site) and listed by the server's chathost; a package is the same
`languages.json` / `<lang>/data/*.json` / media layout that mmiLoader builds from a USB.
The box side is `lazyLoader.py` (run by connectbox-manage), the admin pages are in
connectbox-admin-ui, and the server side is connectbox-chathost.

**Setting up:** the box must have its server set (`server_url` in `brand.j2`, the same
server it syncs chat with) and an internet connection.

**In the admin pages** (Configuration → *Web Server*):

| Control | What it does |
|---|---|
| **Subscribe to Content Package** | Lists the server's packages (`<server>/chathost/link/openwell`, which forwards to MediaBuilder's package list) and saves the chosen one in `assets/content/subscription.json`. This only records the choice - nothing is downloaded yet. |
| **Download Missing Content Files** | Runs `lazyLoader.py`. If the subscribed package on the server is newer than the one on the box (or none has been downloaded), it downloads the package (`openwell.zip`) into the menus, then downloads every media file or image the menus refer to that is not on the box yet. Press it after subscribing, and again to pick up package updates or retry failed files. |
| **Load Content From USB Flash** | If the stick has `package/` with a package in it, the menus are linked straight to it. Otherwise it deletes `content/saved.zip` from the stick and runs a full mmiLoader re-index of `content/` - a "re-index now" button for normal sticks. |

There is no automatic schedule: updates arrive only when someone presses
**Download Missing Content Files**. Progress goes to `/tmp/loadContent.log`; the admin
pages show the number of files that failed (`Failed Item Count`) and the current
package's name (`itemName` in the first language's `main.json`).

Known issue: the USB button recognises a package folder by `package/language.json`,
while packages (like the menus) contain `languages.json`, so a copied package is
normally loaded through the `content/` re-index path instead.

# Making a ConnectBox

See [docs/deployment.md](docs/deployment.md)

# Making a Connectbox on AWS

See [docs/awsinstall.md](docs/awsinstall.md)

# Connectbox setup and administration

See [docs/administration.md](docs/administration.md)

# User documents

PDF copies of the current user documents (the Word originals are kept outside the repository):

- [What is a ConnectBox (V8)](docs/manuals/What-is-a-ConnectBox-V8.pdf): a short overview
- [ConnectBox Specification (V9)](docs/manuals/ConnectBox-Specification-V9.pdf): features and hardware
- [Getting Started (V10)](docs/manuals/ConnectBox-GettingStarted-V10.pdf): setting up a unit, adding media, the admin pages
- [Supported File Types (V3)](docs/manuals/ConnectBox-Supported-File-Types-V3.pdf): which files open on the ConnectBox and which are download-only
- [Translations Guide](docs/manuals/ConnectBox-Translations-Guide.pdf): how the menu wording is translated and how to correct it

# Developing the ConnectBox Software

See [docs/development.md](docs/development.md)

# MicroSD Card Images/Releases

Ready-made images are on the [releases page](https://github.com/ConnectBox/connectbox-pi/releases).
To make one, see [docs/making_an_image.md](docs/making_an_image.md).
