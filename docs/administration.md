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

## Front panel

- **Amber LED:** lit (solid, or blinking to show a low battery) only while the
  access point is really transmitting, so phones can join it.  Off while the WiFi
  is starting or has failed.
- **Internet page:** a status page "Internet: ON/off" with the total, download and
  upload data shared.  It appears in the page list (before the admin icon) while
  sharing is on or the total is not 0.
- **Battery pages:** on a Raspberry Pi or CM4 box with the ATtiny battery
  controller, the multi-battery page is on by default.
