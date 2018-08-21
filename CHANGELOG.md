# Change Log
All notable changes to this project wil be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

This project indentifies releases by release date.

# Unreleased

* Changed: Show full URL in captive portal animations
* Added: Generate a basic index.html when activating static site mode, if one doesn't exist
* Changed: Only use mitogen ansible strategies in CI to avoid causing swapping on small devices

# 20180809

* Added: Show animation in the captive portal browser to demonstrate how to get to content
* Added: Finish setting of locale on Armbian devices

# 20180728

* Fixed: Android 7 devices only showed captive portal instructions momentarily [Issue #251](https://github.com/ConnectBox/connectbox-pi/issues/251)
* Changed: Display a link rather than a text URL in the captive portal for MacOS 10.13 (High Sierra) devices
* Changed: Display a link rather than a text URL in the captive portal for iOS 11 devices

# 20180717

* Added: Optimised 2.4Ghz parameters for the likely next wifi chipset (rtl8812au)
* Fixed: Android 8 devices with active celluar connections were unable to remain connected to the captive portal [Issue #250](https://github.com/ConnectBox/connectbox-pi/issues/250)

# 20180708

* Fixed: Admin system actions report "not initiated" despite performing action [Issue #247](https://github.com/ConnectBox/connectbox-pi/issues/247)
* Changed: The firewall no longer blocks access to ssh on the wifi interface
* Changed: Make sshswitch service a drop-in, so that it overrides the raspbian service by the same name

# 20180630

* Changed: Images no longer have ssh enabled by default. To enable ssh, create .connectbox/enable-ssh on your USB storage, insert the USB storage and boot the device. Please change the root password immediately after booting
* Changed: The admin interface has been rewritten using React (matching the icon-only interface)

# 20180604

* Fixed: Prevent upstream armbian packages overwriting our kernel and uboot packages (this time compatible with aptitude's behaviour)

# 20180602

* Added: Support for OLED HAT (Q3Y2018 HAT).
* Fixed: Prevent upstream armbian packages overwriting our kernel and uboot packages
* Added: Complete disabling of automatic OS updates (allowing ansible-playbook runs to complete without failing on dpkg locks) [Issue #214](https://github.com/ConnectBox/connectbox-pi/issues/214)

# 20180526

* Changed: Admin API migrated to python
* Removed: PHP packages are no longer included by default (they're still available through the system package manager)
* Fixed: Folder icon rendering issues [Issue #233](https://github.com/ConnectBox/connectbox-pi/issues/233)
* Fixed: NEO ethernet MAC changes at power cycle [Issue #237](https://github.com/ConnectBox/connectbox-pi/issues/237)
* Added: Packages and system overlays required for future OLED integration
* Added: ConnectBox build number under /etc/connectbox-release (not exposed in UI yet)
* Changed: Optimised device-specific wifi parameters are applied at device startup, rather than hardcoded (allowing experimentation with other wifi adapters)

# 20180418

* Changed: Switch to Armbian 5.41 with a 4.14y kernel

# 20180122

* Fixed: Corrupted /boot/armbianEnv.txt on unclean shutdown [Issue #220](https://github.com/ConnectBox/connectbox-pi/issues/220)
* Fixed: Broken wifi on developer images when eth is unplugged

# 20180113

* Fixed: Missing usbhost1 device tree because of aptitude/apt-mark interaction for held packages

# 20180108

* Added: Reporting user interface accessible from admin dashboard
* Added: Current project and product info in Admin "About" section
* Added: Pin kernel and device tree packages to prevent inadvertant kernel upgrade
* Added: VMWare Fusion as an additional provider for Vagrant
* Added: Link to admin interface in footer from icon-only interface
* Removed: Redundant Admin "Contact" section

# 20171224

* Added: Captive Portal Workflow for Android devices
* Removed: Automatic redirection to Connectbox page when attempting to load other sites
* Fixed: Constrain Wifi channel selection to valid values in the admin UI
* Added: Initial implementation of chat API and UI
* Added: Install and activate battery level shutdown for NanoPi NEO devices with a Connectbox Hat

# 20171001

* Added: Automatically reboot system if required during ansible playbook runs
* Added: Automate several on-device tasks required for creation of images
* Fixed: Fail during CI if any Ansible run or any tests fail
* Changed: Remove selenium tests.
* Changed: Bump versions of python dependencies for the build system, and start maintaining dependencies with pip-compile
* Added: Schedule resize of root partition on raspbian at first boot for image creation
* Changed: Cleanup admin and development documentation to reflect current state
* Removed: Support for Raspbian Jessie and Armbian Jessie
* Added: Support for Raspbian Stretch
* Changed: Use udev to mount USB storage instead of usbmount
* Changed: Purge apt caches before imaging to reduce image size

# 20170916

* Fixed: Channel 11-14 unavailable regardless of regulatory domain [Issue #168](https://github.com/ConnectBox/connectbox-pi/issues/168)
* Changed: Do not allow 40Mhz 2.4Ghz channels [PR #170](https://github.com/ConnectBox/connectbox-pi/pull/170)
* Fixed: Image does not expose all available space on the microsd card [Issue #163](https://github.com/ConnectBox/connectbox-pi/issues/163)
* Fixed: File listings do not have a cache policy [PR #172](https://github.com/ConnectBox/connectbox-pi/pull/172)
* Changed: Disable automatic apt upgrades [PR #173](https://github.com/ConnectBox/connectbox-pi/pull/173)

# 20170901

* Fixed: Ethernet MAC address changes on each reboot: [Issue #124](https://github.com/ConnectBox/connectbox-pi/issues/124)
* Fixed: Image does not expose all available space on the microsd card [Issue #163](https://github.com/ConnectBox/connectbox-pi/issues/163)
* Added: Attempt to set the WiFi Regulatory domain automatically based on the regulatory domain of surrounding devices [PR #166](https://github.com/ConnectBox/connectbox-pi/pull/166)

# 20170827

* Fixed: Admin Interface - Unable to use input boxes on small screen ([Issue #158](https://github.com/ConnectBox/connectbox-pi/issues/158))
* Fixed: Admin interface - error dialog button off screen ([Issue #157](https://github.com/ConnectBox/connectbox-pi/issues/157))
* Fixed: Setting Wifi channel, Hostname or SSID through admin interface while on wifi reports an error ([Issue #156](https://github.com/ConnectBox/connectbox-pi/issues/156))
* Added: Allocate DHCP addresses with a 24h lease instead of 2min and from a /16 address space instead of a /24 ([PR #164](https://github.com/ConnectBox/connectbox-pi/pull/164))

# 20170820

* Removed: Images based on the legacy images are no longer produced based on results of [legacy vs mainline testing](https://github.com/ConnectBox/wifi-test-framework/blob/master/reports/legacy_and_mainline.md).
* Removed: The unprivileged `box` account is no longer present on new images.
* Added: Improved WiFi performance by activating high-throughput capabilities for the RT5372 device, based on the results of [ht_capab testing](https://github.com/ConnectBox/wifi-test-framework/blob/master/reports/htcapab.md)
* Changed: The default password for root has changed on new images. See the [Release Notes](https://github.com/ConnectBox/connectbox-pi/wiki/Release-Notes:-25-unit-pilot) for the new default.

# 20170815

This is a mainline-only release.

* Changed: Separate static-site and icon-only images are now unnecessary as the mode can be toggled via the admin interface. The image defaults to icon-only.
* Changed: This release includes the re-written icon-only interface.
* Fixed: Standard Operating System folders on USB storage are not hidden in Icon-only interface: [Issue #118](https://github.com/ConnectBox/connectbox-pi/issues/118)

# 20170809

This is a mainline-only release. Separate static-site and icon-only images are now unnecessary as the mode can be toggled via the admin interface. The image defaults to icon-only.

* Fixed: Wifi was not operating in 802.11n mode.
* Fixed: Linux desktops could not connect to the web interface using the default ConnectBox hostname
* Fixed: Toggling Icon-Only and Static-site mode required shell access (this is now an option in the admin interface)

# 20170714

Initial public release
