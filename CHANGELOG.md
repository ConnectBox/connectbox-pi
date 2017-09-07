# Change Log
All notable changes to this project wil be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/) and this
project does not adhere to [Semantic Versioning](http://semver.org) but
instead indentifies releases by release date.

# Unreleased

* Stuff


# 20170901

## Changes

* Fixed: Ethernet MAC address changes on each reboot: [Issue #124](https://github.com/ConnectBox/connectbox-pi/issues/124)
* Fixed: Image does not expose all available space on the microsd card [Issue #163](https://github.com/ConnectBox/connectbox-pi/issues/163)
* Attempt to set the WiFi Regulatory domain automatically based on the regulatory domain of surrounding devices [PR #166](https://github.com/ConnectBox/connectbox-pi/pull/166) 

## Newly Found

* Channel 11-14 unavailable regardless of regulatory domain [Issue #168](https://github.com/ConnectBox/connectbox-pi/issues/168)

## Known Issues

* Android devices are not presented with a Captive Portal screen to guide them to content [Issue #89](https://github.com/ConnectBox/connectbox-pi/issues/89)
* Setting WiFi TX Power is disabled in the Admin interface [Issue #40](https://github.com/ConnectBox/connectbox-pi/issues/40)
* Admin interface allows invalid channel to be set (disables the AP) [Issue #165](https://github.com/ConnectBox/connectbox-pi/issues/165)

# 20170827

## Changes

* Fixed: Admin Interface - Unable to use input boxes on small screen ([Issue #158](https://github.com/ConnectBox/connectbox-pi/issues/158))
* Fixed: Admin interface - error dialog button off screen ([Issue #157](https://github.com/ConnectBox/connectbox-pi/issues/157))
* Fixed: Setting Wifi channel, Hostname or SSID through admin interface while on wifi reports an error ([Issue #156](https://github.com/ConnectBox/connectbox-pi/issues/156))
* Allocate DHCP addresses with a 24h lease instead of 2min and from a /16 address space instead of a /24 ([PR #164](https://github.com/ConnectBox/connectbox-pi/pull/164))

## Newly Found

* Image does not expose all available space on the microsd card [Issue #163](https://github.com/ConnectBox/connectbox-pi/issues/163)
* Admin interface allows invalid channel to be set (disables the AP) [Issue #165](https://github.com/ConnectBox/connectbox-pi/issues/165)

## Known Issues

* Ethernet MAC address changes on each reboot: [Issue #124](https://github.com/ConnectBox/connectbox-pi/issues/124)
* Android devices are not presented with a Captive Portal screen to guide them to content [Issue #89](https://github.com/ConnectBox/connectbox-pi/issues/89)
* Setting WiFi TX Power is disabled in the Admin interface [Issue #40](https://github.com/ConnectBox/connectbox-pi/issues/40)

# 20170820

## Changes

* Images based on the legacy images are no longer produced based on results of [legacy vs mainline testing](https://github.com/ConnectBox/wifi-test-framework/blob/master/reports/legacy_and_mainline.md).
* Improved WiFi performance by activating high-throughput capabilities for the RT5372 device, based on the results of [ht_capab testing](https://github.com/ConnectBox/wifi-test-framework/blob/master/reports/htcapab.md)
* The default password for root has changed on new images. See the [Release Notes](https://github.com/ConnectBox/connectbox-pi/wiki/Release-Notes:-25-unit-pilot) for the new default.
* The unprivileged `box` account is no longer present on new images.

## Newly Found

* Admin Interface - Unable to use input boxes on small screen [Issue #158](https://github.com/ConnectBox/connectbox-pi/issues/158) _(workaround: close the menu after th making a selection by using the hamburger icon)_
* Admin interface - error dialog button off screen [Issue #157](https://github.com/ConnectBox/connectbox-pi/issues/157)
* Setting Wifi channel, Hostname or SSID through admin interface while on wifi reports an error [Issue #156](https://github.com/ConnectBox/connectbox-pi/issues/156)

## Known Issues

* Ethernet MAC address changes on each reboot: [Issue #124](https://github.com/ConnectBox/connectbox-pi/issues/124)
* Updating Wifi Channel or SSID via admin interface while on Wifi reports an error (though update is successful) [Issue #156](https://github.com/ConnectBox/connectbox-pi/issues/156)
* Android devices are not presented with a Captive Portal screen to guide them to content [Issue #89](https://github.com/ConnectBox/connectbox-pi/issues/89)
* Setting WiFi TX Power is disabled in the Admin interface [Issue #40](https://github.com/ConnectBox/connectbox-pi/issues/40)

# 20170815

This is a mainline-only release.

## Changes

* Separate static-site and icon-only images are now unnecessary as the mode can be toggled via the admin interface. The image defaults to icon-only.
* This release includes the re-written icon-only interface.

## Resolved

* Standard Operating System folders on USB storage are not hidden in Icon-only interface: [Issue #118](https://github.com/ConnectBox/connectbox-pi/issues/118)

## Known Issues

* Ethernet MAC address changes on each reboot (Mainline only): [Issue #124](https://github.com/ConnectBox/connectbox-pi/issues/124)
* Updating Wifi Channel or SSID via admin interface while on Wifi reports an error (though update is successful) [Issue #156](https://github.com/ConnectBox/connectbox-pi/issues/156)
* Android devices are not presented with a Captive Portal screen to guide them to content [Issue #89](https://github.com/ConnectBox/connectbox-pi/issues/89)
* Setting WiFi TX Power is disabled in the Admin interface [Issue #40](https://github.com/ConnectBox/connectbox-pi/issues/40)


# 20170809

This is a mainline-only release.
Separate static-site and icon-only images are now unnecessary as the mode can be toggled via the admin interface. The image defaults to icon-only.

## Resolved

* Wifi was not operating in 802.11n mode.
* Linux desktops could not connect to the web interface using the default ConnectBox hostname
* Toggling Icon-Only and Static-site mode requires shell access (this is now an option in the admin interface)

## Newly Found

* Updating Wifi Channel or SSID via admin interface while on Wifi reports an error (though update is successful) [Issue #156](https://github.com/ConnectBox/connectbox-pi/issues/156)

## Known Issues

* Ethernet MAC address changes on each reboot (Mainline only): [Issue #124](https://github.com/ConnectBox/connectbox-pi/issues/124)
* Standard Operating System folders on USB storage are not hidden in Icon-only interface: [Issue #118](https://github.com/ConnectBox/connectbox-pi/issues/118)
* Android devices are not presented with a Captive Portal screen to guide them to content [Issue #89](https://github.com/ConnectBox/connectbox-pi/issues/89)
* Setting WiFi TX Power is disabled in the Admin interface [Issue #40](https://github.com/ConnectBox/connectbox-pi/issues/40)

# 20170714

Initial public release

## Known issues

* Toggling Icon-Only and Static-site requires shell access [Issue #127](https://github.com/ConnectBox/connectbox-pi/issues/127)
* Ethernet MAC address changes on each reboot (Mainline only): [Issue #124](https://github.com/ConnectBox/connectbox-pi/issues/124)
* Standard Operating System folders on USB storage are not hidden in Icon-only interface: [Issue #118](https://github.com/ConnectBox/connectbox-pi/issues/118)
* Android devices are not presented with a Captive Portal screen to guide them to content [Issue #89](https://github.com/ConnectBox/connectbox-pi/issues/89)
* Setting WiFi TX Power is disabled in the Admin interface [Issue #40](https://github.com/ConnectBox/connectbox-pi/issues/40)
