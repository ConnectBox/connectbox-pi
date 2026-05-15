# mmiLoader USB Content Structure Reference

`mmiLoader.py` walks `/media/usb0/content` and converts whatever it finds into JSON
consumed by the Angular/Ionic media-interface frontend.  This document describes every
structure it recognises and how each one is rendered.

---

## 1. Top-level layout — language vs. flat

### 1a. Multi-language USB (language folders)

Name each top-level folder with an ISO 639 language code.  mmiLoader validates each
directory name against `languageCodes.json`.

```
content/
  en/          ← English — ISO 639-1 two-letter code
  zh-CN/       ← Simplified Chinese — IETF regional tag (zh symlink created automatically)
  pt/          ← Portuguese — two-letter code
  fr/          ← French
```

All non-language folders at the root are silently skipped when at least one valid
language directory exists.

**Supported language code formats**

| Format | Example | Notes |
|--------|---------|-------|
| ISO 639-1 two-letter | `en`, `fr`, `zh` | Most common |
| ISO 639-2 three-letter | `zho`, `fra` | Accepted if in languageCodes.json |
| IETF regional tag | `zh-CN`, `pt-BR` | Base-code symlink (`zh` → `zh-CN`) created automatically so the frontend can resolve URLs |

Codes longer than 3 characters that do not contain `-` are rejected.

### 1b. Flat USB (no language folders)

All content sits directly under `content/`.  mmiLoader defaults to English (`en`).

```
content/
  video.mp4
  guide.pdf
  gospel-comics/
    page1.jpg
    page2.jpg
```

### 1c. `.language` override file

Place a plain-text file `.language` in `content/` containing a single language code
(e.g. `zh`).  Overrides the default `en` when no language-named directories exist.

```
content/
  .language       ← contains: zh
  sermon.mp4
  study-guide.pdf
```

---

## 2. Directory types

mmiLoader assigns each directory one of the following internal types, in priority order.

### 2a. Singular — one or two media files

**Trigger**: a folder containing ≤ 2 non-hidden, non-underscore files and no
subdirectories.

**Frontend**: each file appears as an independent card on the home screen.

```
content/
  en/
    welcome.mp4          ← standalone item card
    intro/
      readme.pdf         ← standalone item card (1-file folder = singular)
```

### 2b. Collection — multiple media files, one folder

**Trigger**: a folder containing > 2 files and no subdirectories.

**Frontend**: shown as a single collection card; tapping it opens an episode list.
The collection card image comes from folder art (see §4) or the first recognisable
media type found.

```
content/
  en/
    sermons/
      sermon-1.mp4
      sermon-2.mp4
      sermon-3.mp4
      cover.jpg          ← optional folder art used as collection card image
```

### 2c. Web content — directory with an HTML entry point

**Trigger** (any one of):
- `index.html` exists in the directory, OR
- `index.htm` exists in the directory, OR
- exactly one `.html` / `.htm` file exists (no index required)

Language root directories are **exempt** — they may contain an `index.html`
alongside PDFs/videos without being treated as a web app.

**Frontend**: shown as a tile with a `www.png` icon; tapping opens the web app
inside the in-app browser.  A zip archive of the whole directory is created on
the USB (`.webarchive-<lang>-<dir>.zip`) so users can also download it.

All files inside the web content directory are suppressed from the per-file loop
(added to `webpaths`); only the `index.html` / `index.htm` generates a JSON entry.

Add `.NoWebcompress` to `content/` to skip the zip step for all web directories.

```
content/
  en/
    gospel-comics/
      index.html
      images/
        page1.png
        page2.png
      css/
        style.css
```

Single-file HTML example (e.g. an article):

```
content/
  en/
    article/
      my-article.html    ← only HTML file — treated as web content
      banner.jpg
```

### 2d. Android app — directory with AndroidManifest.xml

**Trigger**: `AndroidManifest.xml` present in the directory.

**Frontend**: shown as an app download tile with `app.png` icon.  A zip archive
is created (same mechanism as web content).

```
content/
  en/
    my-app/
      AndroidManifest.xml
      classes.dex
      res/
        ...
```

### 2e. Complex directory — tree with subdirectories

**Trigger**: a directory that is itself not a language root AND whose walk reveals at
least one subdirectory at any depth.

**Processing**: `indexer.py` recursively generates a static HTML file-browser
(`index.html`) for the directory tree.  The result is linked into the content
area and served as a web app.

**Frontend**: shown as a tile like any other web-content entry; tapping opens the
generated file browser.

```
content/
  en/
    training-course/
      module-1/
        lesson-1.pdf
        lesson-2.pdf
      module-2/
        lesson-3.pdf
        worksheet.docx
      overview.pdf
```

> Files at any depth are included.  There is no limit on how many files a level
> can contain — the only trigger is the presence of at least one subdirectory.

### 2f. Language root itself

The language root (e.g. `en/`, `zh-CN/`) is walked but never itself turned into a
content item.  Files placed directly in the language root (not in sub-folders) are
indexed as individual singular items.

```
content/
  en/
    welcome.mp4           ← singular item card (directly in language root)
    bible/
      genesis.mp4         ← part of the 'bible' collection
      exodus.mp4
```

---

## 3. Supported file types

mmiLoader reads `types.json` for the complete extension map.  The important
categories and their behaviour:

| Category | Example extensions | Thumbnail | Fallback icon |
|----------|--------------------|-----------|--------------|
| Video | `.mp4 .mkv .webm .avi .mov` | ffmpeg frame (progressive seek 1s→5s→15s→30s→60s, skips black frames) | `video.png` |
| Audio | `.mp3 .m4a .ogg .aac .flac` | Embedded album art via ffmpeg | `sound.png` |
| Image | `.jpg .jpeg .png .gif .webp .bmp` | The image itself | `images.png` |
| PDF | `.pdf` | — | `pdf.png` |
| Word document | `.doc .docx` | — | `doc.png` |
| Spreadsheet | `.xls .xlsx .pptx` | — | `sheet.png` |
| Other document | `.h5p .txt` | — | `pdf.png` |
| ePub | `.epub` | — | `epub.png` |
| Archive | `.zip .gz .7z .bz2 .tar` | — | `zip.png` |
| Android app | (directory with `AndroidManifest.xml`) | — | `app.png` |
| Web app | (directory with `index.html/htm`) | — | `www.png` |

Files with extensions not in `types.json` are silently skipped.
Files and directories whose names start with `.` or `_` are also skipped.

---

## 4. Folder art

Place an image file in a directory to use it as the collection card icon.  mmiLoader
looks for these names in priority order:

1. `folder.png`
2. `folder.jpg`
3. `cover.jpg`
4. `album.art.jpg`
5. `front.jpg`
6. Any other `.png`, `.jpg`, or `.gif` not starting with `.thumbnail`

The image must be placed in the **collection or singular folder**, not inside a
subdirectory.  Language roots and HTML content directories ignore folder art.

---

## 5. Special control files

These hidden files in `content/` (or USB root) modify mmiLoader's behaviour.

| File | Location | Effect |
|------|----------|--------|
| `.language` | `content/` | Sets the language code for a flat (no language dirs) USB |
| `.compress` | `content/` | Auto-creates a downloadable zip of every multi-file directory |
| `.NoWebcompress` | `content/` | Suppresses zip creation for all web content directories |
| `saved.zip` | `content/` or USB root | Fast-load cache — mmiLoader extracts it and exits immediately |
| `.indexed.idx` | `content/` | Marker written after first complex-directory index run |
| `.thumbnail-<lang>-<slug>.png` | `content/` root | Cached thumbnail; re-checked for black frames on each run |

Delete `saved.zip` to force a full re-index.  Delete individual `.thumbnail-*` files
to force re-extraction of those thumbnails.

---

## 6. Complete worked example

```
content/
  .language          ← not needed here since we have language dirs
  en/
    welcome.mp4                      ← singular item
    study-guide.pdf                  ← singular item
    sermons/                         ← collection (>2 files)
      cover.jpg
      sermon-jan.mp4
      sermon-feb.mp4
      sermon-mar.mp4
    gospel-comics/                   ← web content (has index.html)
      index.html
      images/
        page1.png
    training/                        ← complex dir (has subdirs)
      module-1/
        lesson.pdf
      module-2/
        lesson.pdf
  zh-CN/
    welcome.mp4                      ← singular (zh symlink auto-created → zh-CN)
    sermons/
      sermon-1.mp4
      sermon-2.mp4
```

**What the frontend sees (English home screen)**

| Card | Type | Thumbnail |
|------|------|-----------|
| welcome | Video | ffmpeg frame |
| study-guide | PDF | pdf.png icon |
| sermons | Collection | cover.jpg |
| gospel-comics | Web app | www.png |
| training | Web app (file browser) | www.png |
