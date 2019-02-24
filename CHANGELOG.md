# Change Log
All notable changes to this project wil be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

This project indentifies releases by release date.

# Unreleased

* Changed: Activate sshd when configured USB storage is attached, rather than at boot time.

# 20181215

* Changed: Allow HAT service to start up earlier in the boot sequence
* Changed: Allow more frequent HAT button pushes (reduce bounce detection time to 125ms)
* Added: Improved detection of RTL8812AU devices

# 20181208

* Changed: Dramatically improved responsiveness of buttons on devices with OLED screens
* Changed: Reduced background power consumption on devices with OLED screens

# 20181126

* Fixed: Add libfreetype - required for OLED HAT operation

# 20181125

* Changed: Start HAT service earlier in the boot sequence
* Fixed: Memory leak in connectbox-hat-service that would cause lockup of devices running a Q3Y2018 HAT after a few hours.
* Fixed: Allow controlled shutdown on devices running a Q1Y2018 HAT by initiating shutdown sequence when battery voltage drops below 3.2V instead of the previous value of 3.0V

# 20181119

* Fixed: Missing library that was preventing OLED HATs from displaying content
* Added: Code to allow in-development Q4Y2018 HAT to function

# 20181103

* Changed: Disabled non-OFDM Wifi rates to improve overall throughput when a connected client has a bad connection
* Fixed: Compatibility with some Android 9 devices that have active cellular plans
* Changed: Image is now based on Debian Stretch instead of Ubuntu Xenial.
* Changed: Image rebased against current Armbian sunxi-next.
* Changed: "conservative" CPU frequency governor is now selected (was: "ondemand")

# 20181021

* Fixed: Allow sshd to be enabled on Raspberry Pi devices by the usual .connectbox/enable-ssh method via USB storage
* Added: "Return to main interface" button in the admin area [Issue #274](https://github.com/ConnectBox/connectbox-pi/issues/274)

# 20181016

* Changed: Upgrade to Ansible 2.6.5.
* Changed: Run image preparation logic in CI
* Removed: Many OS packages that are not required for ConnectBox operation but took disk space

# 20180915

* Changed: Further enbiggening the OK button on the captive portal page
* Changed: Do not create captive portal log file from flask process, which would prevent startup after log rotation

# 20180911

* Fixed: Android 7.1 is shown captive portal window when rejoining network
* Fixed: Android 7.1 no longer falls back to cellular after 5 minutes
* Changed: Extract captive portal into Connectbox/simple-offline-captive-portal
* Changed: Run captive portal as a separate service from chat and admin
* Changed: Only show OK button on captive portal page for Android, and only for >= v6
* Changed: Enbiggen the OK button on the captive portal page
* Changed: Python module bumps for CVE-2018-7750 and CVE-2018-10903

# 20180825

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
