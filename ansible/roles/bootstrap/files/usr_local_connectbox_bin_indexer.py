#!/usr/bin/env python3

# Indexer v.1.0.1
# Author: Josh Brunty (josh dot brunty at marshall dot edu)
# DESCRIPTION: This script generates an .html index  of files within a directory (recursive is OFF by default). Start from current dir or from folder passed as first positional argument. filter("*.py") in config. 

# -handle symlinked files and folders: displayed with custom icons
# By default only the current folder is processed.
# Use config 'recursive' to process nested folders.

#initial call fucnciton was:
#   config:
#	'verbose'
#	'recursive'
#       'filter(file filter)' for sort function
#   process_dir(top_dir, dest_dir, config)


import datetime
import os
import sys
import logging
from pathlib import Path
from urllib.parse import quote

DEFAULT_OUTPUT_FILE = 'index.html'

def pretty_size(bytes_count):
    """Human-readable file sizes."""
    UNITS_MAPPING = [
        (1024 ** 5, ' PB'),
        (1024 ** 4, ' TB'),
        (1024 ** 3, ' GB'),
        (1024 ** 2, ' MB'),
        (1024 ** 1, ' KB'),
        (1024 ** 0, (' byte', ' bytes')),
    ]
    for factor, suffix in UNITS_MAPPING:
        if bytes_count >= factor:
            break
    amount = int(bytes_count / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix

def process_dir(top_dir, dest_dir, opts):
    print("passed directories and options are: ", top_dir, dest_dir, opts)
    
    glob_patt = "*"
    if 'filter(' in opts:
        try:
            x = opts.find('filter(') + 7
            y = opts[x:].find(')')
            if y != -1:
                glob_patt = opts[x:x+y]
        except Exception as e:
            print(f"Error parsing filter: {e}")

    # Ensure we are working with Path objects for traversal
    path_top_dir = Path(top_dir)
    index_path = Path(dest_dir) / 'index.html'
    
    print("final top_path and index path are: ", path_top_dir, index_path)

    if 'verbose' in opts:
        print(f'Traversing dir {path_top_dir.absolute()}')

    try:
        index_file = open(index_path, 'w', encoding='utf-8')
    except Exception as e:
        print('cannot create file %s %s' % (index_path, e))
        return

    index_file.write("""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    * { padding: 0; margin: 0; }
    body {
        font-family: sans-serif;
        text-rendering: optimizespeed;
        background-color: #ffffff;
    }
    a {
        color: #006ed3;
        text-decoration: none;
    }
    a:hover,
    h1 a:hover {
        color: #319cff;
    }
    header,
    #summary {
        padding-left: 5%;
        padding-right: 5%;
    }
    th:first-child,
    td:first-child {
        width: 5%;
    }
    th:last-child,
    td:last-child {
        width: 5%;
    }
    header {
        padding-top: 25px;
        padding-bottom: 15px;
        background-color: #f2f2f2;
    }
    h1 {
        font-size: 20px;
        font-weight: normal;
        white-space: nowrap;
        overflow-x: hidden;
        text-overflow: ellipsis;
        color: #999;
    }
    h1 a {
        color: #000;
        margin: 0 4px;
    }
    h1 a:hover {
        text-decoration: underline;
    }
    h1 a:first-child {
        margin: 0;
    }
    main {
        display: block;
    }
    .meta {
        font-size: 12px;
        font-family: Verdana, sans-serif;
        border-bottom: 1px solid #9C9C9C;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .meta-item {
        margin-right: 1em;
    }
    #filter {
        padding: 4px;
        border: 1px solid #CCC;
    }
    table {
        width: 100%;
        border-collapse: collapse;
    }
    tr {
        border-bottom: 1px dashed #dadada;
    }
    tbody tr:hover {
        background-color: #ffffec;
    }
    th,
    td {
        text-align: left;
        padding: 10px 0;
    }
    th {
        padding-top: 15px;
        padding-bottom: 15px;
        font-size: 16px;
        white-space: nowrap;
    }
    th a {
        color: black;
    }
    th svg {
        vertical-align: middle;
    }
    td {
        white-space: nowrap;
        font-size: 14px;
    }
    td:nth-child(2) {
        width: 80%;
    }
    td:nth-child(3) {
        padding: 0 20px 0 20px;
    }
    th:nth-child(4),
    td:nth-child(4) {
        text-align: right;
    }
    td:nth-child(2) svg {
        position: absolute;
    }
    td .name {
        margin-left: 1.75em;
        word-break: break-all;
        overflow-wrap: break-word;
        white-space: pre-wrap;
    }
    td .goup {
        margin-left: 1.75em;
        padding: 0;
        word-break: break-all;
        overflow-wrap: break-word;
        white-space: pre-wrap;
    }
    .icon {
        margin-right: 5px;
    }
    tr.clickable { 
        cursor: pointer; 
    } 
    tr.clickable a { 
        display: block; 
    } 
    @media (max-width: 600px) {
        * {
            font-size: 1.06rem;
        }
        .hideable {
            display: none;
        }
        td:nth-child(2) {
            width: auto;
        }
        th:nth-child(3),
        td:nth-child(3) {
            padding-right: 5%;
            text-align: right;
        }
        h1 {
            color: #000;
        }
        h1 a {
            margin: 0;
        }
        #filter {
            max-width: 100px;
        }
    }
    </style>
</head>
<body>
    <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" height="0" width="0" style="position: absolute;">
    <defs>
        <g id="go-up">
            <path d="M10,9V5L3,12L10,19V14.9C15,14.9 18.5,16.5 21,20C20,15 17,10 10,9Z" fill="#696969"/>
        </g>
        <g id="folder" fill-rule="nonzero" fill="none">
            <path d="M285.22 37.55h-142.6L110.9 0H31.7C14.25 0 0 16.9 0 37.55v75.1h316.92V75.1c0-20.65-14.26-37.55-31.7-37.55z" fill="#FFA000"/>
            <path d="M285.22 36H31.7C14.25 36 0 50.28 0 67.74v158.7c0 17.47 14.26 31.75 31.7 31.75H285.2c17.44 0 31.7-14.3 31.7-31.75V67.75c0-17.47-14.26-31.75-31.7-31.75z" fill="#FFCA28"/>
        </g>
        <g id="folder-shortcut" fill-rule="nonzero" fill="none">
             <path d="M285.22 37.55h-142.6L110.9 0H31.7C14.25 0 0 16.9 0 37.55v75.1h316.92V75.1c0-20.65-14.26-37.55-31.7-37.55z" fill="#FFA000"/>
             <path d="M285.22 36H31.7C14.25 36 0 50.28 0 67.74v158.7c0 17.47 14.26 31.75 31.7 31.75H285.2c17.44 0 31.7-14.3 31.7-31.75V67.75c0-17.47-14.26-31.75-31.7-31.75z" fill="#FFCA28"/>
        </g>
        <g id="file" stroke="#000" stroke-width="25" fill="#FFF" fill-rule="evenodd" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 24.12v274.76c0 6.16 5.87 11.12 13.17 11.12H239c7.3 0 13.17-4.96 13.17-11.12V136.15S132.6 13 128.37 13H26.17C18.87 13 13 17.96 13 24.12z"/>
            <path d="M129.37 13L129 113.9c0 10.58 7.26 19.1 16.27 19.1H249L129.37 13z"/>
        </g>
        <g id="file-shortcut" stroke="#000" stroke-width="25" fill="#FFF" fill-rule="evenodd" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 24.12v274.76c0 6.16 5.87 11.12 13.17 11.12H239c7.3 0 13.17-4.96 13.17-11.12V136.15S132.6 13 128.37 13H26.17C18.87 13 13 17.96 13 24.12z"/>
            <path d="M129.37 13L129 113.9c0 10.58 7.26 19.1 16.27 19.1H249L129.37 13z"/>
        </g>
    </defs>
    </svg>
<header>
    <h1>""" + f'{path_top_dir.name}' + """</h1>
</header>
<main>
    <div class="listing">
        <table aria-describedby="summary">
            <thead>
            <tr>
                <th></th>
                <th>Name</th>
                <th>Size</th>
                <th class="hideable">Modified</th>
                <th class="hideable"></th>
            </tr>
            </thead>
            <tbody>
            <tr class="clickable">
                <td></td>
                <td><a href=".."><svg width="1.5em" height="1em" version="1.1" viewBox="0 0 24 24"><use xlink:href="#go-up"></use></svg>
                <span class="goup">..</span></a></td>
                <td>&mdash;</td>
                <td class="hideable">&mdash;</td>
                <td class="hideable"></td>
            </tr>
""")

    # sort entries
    try:
        entries = sorted(path_top_dir.glob(glob_patt), key=lambda p: (not p.is_dir(), p.name.lower()))
    except Exception as e:
        print(f"Error listing entries in {path_top_dir}: {e}")
        entries = []

    for entry in entries:
        if entry.name.lower() == 'index.html':
            continue

        if entry.is_dir() and 'recursive' in opts:
            process_dir(entry, entry, opts)

        size_bytes = -1
        size_pretty = '&mdash;'
        last_modified_human_readable = '-'
        last_modified_iso = ''
        
        try:
            stats = entry.stat()
            if entry.is_file():
                size_bytes = stats.st_size
                size_pretty = pretty_size(size_bytes)

            last_modified = datetime.datetime.fromtimestamp(stats.st_mtime).replace(microsecond=0)
            last_modified_iso = last_modified.isoformat()
            last_modified_human_readable = last_modified.strftime("%c")
        except Exception as e:
            print(f'Error accessing stats for {entry}: {e}')

        entry_path = entry.name
        if entry.is_dir():
            entry_path = entry.name + '/'
            entry_type = 'folder'
            if entry.is_symlink():
                entry_type = 'folder-shortcut'
        else:
            entry_type = 'file'
            if entry.is_symlink():
                entry_type = 'file-shortcut'

        index_file.write(f"""
            <tr class="file">
                <td></td>
                <td>
                    <a href="{quote(entry_path)}">
                        <svg width="1.5em" height="1em" version="1.1" viewBox="0 0 317 258"><use xlink:href="#{entry_type}"></use></svg>
                        <span class="name">{entry.name}</span>
                    </a>
                </td>
                <td data-order="{size_bytes}">{size_pretty}</td>
                <td class="hideable"><time datetime="{last_modified_iso}">{last_modified_human_readable}</time></td>
                <td class="hideable"></td>
            </tr>
""")

    index_file.write("""
            </tbody>
        </table>
    </div>
</main>
</body>
</html>""")
    index_file.close()

