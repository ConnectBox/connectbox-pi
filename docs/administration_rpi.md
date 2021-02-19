# Administering a ConnectBox

This document describes how to administer a ConnectBox created in an RPi environment.

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

- When administering an RPi based ConnectBox, your content must be manually placed in the /media/usb0 folder.
- The ConnectBox will display an appropriate icon for each folder in your /media/usb0 directory. A folder icon can be set in one of these ways:
  1. Choose an icon from the [icon list](http://fontawesome.io/icons/) and give your folder the same name as the icon. For example, if you want to use the [address book icon](http://fontawesome.io/icon/address-book), your folder should be named `address-book`
  2. Name your folder what you like e.g. `people`. Choose an icon from the [icon list](http://fontawesome.io/icons/) e.g. `address-book` and create a file next to the folder called `_icon_<folder-name>_<icon-name>` e.g. `_icon_people_address-book`
  3. Name your folder what you like e.g. `people`. Put your own image on the USB stick, next to the folder and name it `_icon_<folder-name>.<extension>` where `extension` is the image type (gif, jpg, png) e.g. `_icon_people.jpg`
  4. If none of the above are done, your folder will have a [default folder icon](http://fontawesome.io/icon/folder/)

- Content from a USB stick can be directly transferred to the /media/usb0 folder using the RPi desktop file management tools.)
