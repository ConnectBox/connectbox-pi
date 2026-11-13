# Administering a ConnectBox

This document describes how to administer a ConnectBox for a purchased unit.
If you built a Raspberry Pi version you should use (https://github.com/ConnectBox/connectbox-pi/docs/administration_rpi.md)

# Initial Administration

1. ConnectBox comes with system software. No content is included.
2. Plug into a power source and wait 1 minute for startup.
3. Locate and join the wireless network called _ConnectBox - Free Media_
4. Navigate to the Administration area: http://connectbox/admin and login (username and password are case sensitive):

- username: admin
- password: connectbox

5. _Recommended_: Change the password for the Administration area. Go to the Configure Menu and select Password. Enter a new password and press submit. When you next try to change the system, you will be prompted to login again. Use the new password when that happens.
6. _Optional_: Change the name of the system (Configure -> System). This only appears in the location bar of the browser. If you change this, you will need to login again
7. _Optional_: Change the name of the wireless network. (Configure -> SSID). When you do this, you will be disconnected from the wireless network and will need to locate and join the newly named wireless network
8. _Optional_: Change the WiFi channel. (Configure -> Channel)

# Content

- This assumes you are placing your content on a USB stick.
- The ConnectBox will display an appropriate icon for each folder on your USB stick. A folder icon can be set in one of these ways:
  1. Choose an icon from the [icon list](http://fontawesome.io/icons/) and give your folder the same name as the icon. For example, if you want to use the [address book icon](http://fontawesome.io/icon/address-book), your folder should be named `address-book`
  2. Name your folder what you like e.g. `people`. Choose an icon from the [icon list](http://fontawesome.io/icons/) e.g. `address-book` and create a file next to the folder called `_icon_<folder-name>_<icon-name>` e.g. `_icon_people_address-book`
  3. Name your folder what you like e.g. `people`. Put your own image on the USB stick, next to the folder and name it `_icon_<folder-name>.<extension>` where `extension` is the image type (gif, jpg, png) e.g. `_icon_people.jpg`
  4. If none of the above are done, your folder will have a [default folder icon](http://fontawesome.io/icon/folder/)

- When you insert your USB stick into the ConnectBox, content will automatically be visible in the ConnectBox web interface (this is http://connectbox unless the system name has been changed during Initial Administration)
- To update the files on the USB stick, go to the Configure Menu in Administration area, then go to System and press "Unmount USB", then remove the USB stick from the ConnectBox

# Internet connection, internet sharing and the front panel (November 2026)

## Connect the box to the internet (Configuration -> Connect To Wi-Fi Hotspot)

The box can use a WiFi network with internet access (a phone hotspot, a router) as
its uplink, besides an Ethernet cable.  Open *Connect To Wi-Fi Hotspot*, scan or type
the network name (*Client SSID*) and its *Wifi Password*, and save.

- **Remembered networks:** once the box is connected to a network **and** the
  internet answers through it, the box remembers that network (name and
  password), up to 10, newest first; an 11th drops the oldest.  When the saved
  network is out of range the box connects by itself to any remembered one in
  range.  A network that connects but has no internet is not remembered.
- **Wipe client SSID and password:** the last row of the section.  After you
  confirm, the box sets the SSID and password back to the defaults
  (`Default` / `Default1`), forgets all remembered networks and disconnects from the
  internet WiFi.  Use it before handing a box on, or before making an image from it.

## Advanced options

*Enable Advanced Options* (Configuration page) shows the advanced settings.  The
choice is remembered in that browser: Advanced stays on after the next login until
you press the button again, which hides them.

## Share Internet With Wi-Fi Users (Advanced)

Under *Connect To Wi-Fi Hotspot*, with Advanced options on.  Off by default.  When
it is on, phones on the ConnectBox WiFi can use the box's internet connection
(Ethernet or the client WiFi above), IPv4 only, with no filtering.

- **Metered connections:** if the box's internet is metered (mobile data, pay per
  MB), every phone's traffic, including app and system updates, counts against it.
- Turning it on or off disconnects the phones once; they rejoin by themselves (a
  phone may join another known WiFi network instead).
- While it is on, phones see a normal internet connection and do not open the
  ConnectBox page by themselves: open **http://connectbox** (http://wi.fi and
  http://gowifi.org still lead to the box).
- **Data shared:** the section shows the data phones have passed through the box,
  with download and upload, since the date shown (1 MB = 1,000,000 bytes).  It is
  kept across reboots.  *Reset data counter* sets it back to 0.  Reload the page to
  see the latest figures.
- The setting survives a reboot.  Images are always made with it off.
- Turning sharing on also turns on the front panel's *Internet Data* page (see
  *LCD Interface* below); turning it off turns that page off again, unless you
  had switched the page on yourself.

## HDMI Screen (Advanced, Raspberry Pi boxes)

A monitor or TV on the box's HDMI port shows a playlist of the box's video, audio
and picture files.  Sound goes out over the same HDMI cable.  With nothing to play
the screen shows the box name and the WiFi name.

- **Build the playlist:** pick a file in the list and press *Add to playlist*; use
  ↑ ↓ ✕ to reorder or remove.  The list groups the files under **Language: xxx**
  headings, and each playlist entry shows its language in bold and underlined
  (e.g. *Intro video (video) · **Language: English***).  *Seconds per picture*
  sets how long a picture stays.
- **Play playlist:** saves the list and starts it from the top.  It then loops for
  ever, and starts by itself whenever the box starts.
- **Save playlist:** saves the list and starts it, unless a *Play now* file is still
  playing (the playlist then starts when that file ends).
- **Play now:** plays only the file selected in the list, once, then the playlist
  goes on.
- **Stop:** ends whatever is playing, the playlist included, and leaves the box name
  on the screen until *Play playlist* or *Save playlist* (or a restart of the box).
- **Visitors can use "Play on HDMI":** a switch (off by default).  When it is on,
  everyone on the WiFi gets a screen button next to the download button on the
  media pages; otherwise only a logged-in admin does.
- Playlist items on a USB key are skipped while the key is out.  Images are made
  with an empty playlist and the visitor switch off.

## Host name

*Configuration → Web Server → Hostname* (an Advanced option) accepts letters, digits and hyphens only (1-63, not
starting or ending with a hyphen; no spaces).  The new name is used at once: in the
address bar (http://name), on the front panel and on the HDMI screen.  No restart
is needed.

## Front panel

- **Amber LED:** lit (solid, or blinking to show a low battery) only while the
  access point is really transmitting, so phones can join it.  Off while the WiFi
  is starting or has failed.
- **IP addresses page:** a status page with the box's three addresses, one per
  line: `AP` (the WiFi the phones join), `WiFi` (the box's own connection to another
  WiFi network) and `Eth` (the wired port).  A line reads `not connected` when the
  interface has no address and `none` when the box has no such interface.  The WiFi
  address changes at every start (by design), so read it here before using SSH or
  opening the box from the other network.  It comes after the statistics pages.
- **Internet Data page:** a status page "Internet: ON/off" with the total, download
  and upload data shared, before the admin icon.  It is shown while its switch in
  *LCD Interface* is on: off by default, turned on and off with internet sharing
  (see below).
- **Battery pages:** on a Raspberry Pi or CM4 box with the ATtiny battery
  controller, the multi-battery page is on by default.

## LCD Interface (Advanced)

Switches for the front panel's pages: *Main*, *Info*, *Battery*, *Battery Details*,
*Memory*, *Stats*, *Admin*, and since November 2026:

- **Show LCD IP Addresses Page:** on by default (also on a box set up before the
  switch existed).
- **Show LCD Internet Data Page:** off by default.  Turning *Share Internet With
  Wi-Fi Users* on turns it on; turning sharing off turns it off again, unless you
  switched it on yourself - your own choice is never undone (on or off).  When it
  is on, the page is shown even with no data counted.  After you change the
  sharing switch the page shows this switch's new state without a reload.

## Box Content (Advanced)

Copies the box's own content (on its SD card) to or from a USB key - the same as
the front panel's admin menu, so the panel shows the same pages while it runs.
Each item explains itself and asks before it starts.  The status line under it
follows the copy every 2 seconds: *Put the USB key in* (if none is in; it waits up
to 5 minutes), *Copying 45% of 22431 MB*, *Copied: take the USB key out*, then
*Done - the menus are being rebuilt* or *Failed: ...*.  One copy runs at a time,
from the page or the panel; a copy started on the panel shows here too.  Leaving
the page does not stop a copy.

- **Copy USB key to the box:** replaces the box's own content with the key's
  `content` folder, then rebuilds the menus once the key is taken out.  The box's
  current content is deleted first, once the check shows there is room.  If the
  copy fails part way (e.g. the key is pulled or drops out), the part already
  copied stays on the box.
- **Copy box content to a USB key:** replaces the key's `content` folder with the
  box's own content.  A FAT32 key cannot take a file of 4 GB or more (large ZIM
  files): the copy says *File over 4GB* before it starts.
- Errors (shown on the page and the panel): *No content dir* (the key has no
  `content` folder), *Not enough room*, *Nothing to copy*, *Remove 2nd USB*,
  *File over 4GB*, *USB not mounted*, *Failed Copy*, *Battery low*.  On a
  Raspberry Pi with no front panel the copies work the same way (no battery
  check).

## Wipe All Storage (Advanced)

For emergencies, when the box is found and its content could put people in
danger.  Enter the **admin password** and press the play button; a wrong password
wipes nothing.  The page then says *The media on this box and all USB keys are
being wiped. The Wi-Fi will go off.*

1. Within about 2 seconds the box stops serving: the WiFi (access point), the web
   pages, the chat and the content loader stop and stay off.
2. Within seconds **every USB key** is made unreadable (partition table, file
   systems and the start of every partition overwritten, plus the key's own erase
   where it has one), then on the **SD card** the media and everything that names
   or shows it is deleted: the box's own content, the menus and thumbnails, the
   ZIM (Kiwix) list, the HDMI playlist, the chat, every log including the usage
   statistics, and swap (overwritten).  The card is told to erase the freed space.
3. Then, for as long as the box has power, the USB keys and the card's free space
   are overwritten with random data, pass after pass (at low priority, so the
   front panel stays usable).  A key plugged in during this is destroyed too.

The system on the SD card is kept: after the power is cut and the box restarts it
works as before, with empty menus and the WiFi on.  A wiped USB key has to be
formatted again (FAT32 or exFAT) before it can be used.  Left on the box: its name
and WiFi name, the operator details and the client WiFi settings in the
configuration, and the system's own records in memory until the power goes.

