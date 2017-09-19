# Change Log
All notable changes to this project wil be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/).

This project indentifies releases by release date.

Current open Issues: https://github.com/ConnectBox/connectbox-pi/issues?q=is%3Aopen+is%3Aissue+milestone%3A%2225-unit+pilot%22


# Unreleased

* Added: Automatically reboot system if required during ansible playbook runs
* Added: Automate several on-device tasks required for creation of images

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
