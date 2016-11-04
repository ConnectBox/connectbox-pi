# Indigitous Hack

This is a solution to the biblebox-pi challenge as a part of [Indigitous #hack](https://indigitous.org/hack/challenges/bibleboxpi/) taking place on Nov 4-6 2016. If you're a part of the hack, and would like to collaborate, I'm _@edwin_ on Kingdom Builders slack, or via email at: edwin@wordspeak.org.

There's a TODO section at the bottom of this document of tasks that I still need to work through if you're looking for an area to contribute.

# Quick Start

How to deploy what's in this repo.

## Get Ansible

This project uses Ansible v2.1+. Install it however you wish. I use a python virtualenv:

```
$ mkdir ~/.virtualenvs
$ mkvirtualenv ~/.virtualenvs/ansible
$ . ~/.virtualenvs/ansible/bin/activate
$ pip install ansible==2.1.2.0
```

## Install Vanilla Raspbian-lite on Raspberry Pi

Follow the [Raspberry Pi install instructions](https://www.raspberrypi.org/documentation/installation/installing-images/). Boot the Raspberry Pi with the image. This assumes that your Pi is attached to the network via its ethernet port, so that the wifi interface can be configured as an AP. Make a note of the IP address associated with the ethernet interface when it boots.

## Run Ansible

1. cd into the `ansible` directory in this project.
1. Edit `inventory` and replace whatever IP address is listed with the IP address of the Pi ethernet interface.
1. Confirm connectivity by running `ansible --ask-pass -i inventory all -m ping` . You will be prompted for the password for the pi user, which is still the default of _raspberry_ . If you do not see a **pong** response, then you'll have to revisit your connectivity before continuing.
1. _Optional_: If you're developing and want to avoid entering the password for each ansible run, use/reuse an ssh key pair. I'm reusing one: `ssh pi@192.168.20.183 "mkdir /home/pi/.ssh; chmod 700 /home/pi/.ssh"` and `scp ~/.ssh/id_rsa.pub pi@192.168.20.183:/home/pi/.ssh/authorized_keys` (`192.168.20.183` is the IP of my Pi)
1. **Commands assume ssh keys are setup from here**. If you haven't set them up, just add `--ask-pass` to the `ansible` or `ansible-playbook` command line and you'll be right.
1. Run the playbook: `ansible-playbook -i inventory site.yml`. No tasks should fail.


# Notes

The foundation of documentation and other stuff.

Useful references:

* https://www.pi-point.co.uk/closedcloud-walkthrough/
* https://wiki.alpinelinux.org/wiki/Raspberry_Pi_3_-_Configuring_it_as_wireless_access_point_-AP_Mode
* https://learn.adafruit.com/setting-up-a-raspberry-pi-as-a-wifi-access-point/install-software (uses isc-dhcp-server instead of dnsmasq)


## WLAN Access Point

* Override SSID on ansible command line with `-e ssid="some ssid"` (or use other ansible methods like `host_vars`)
* Currently `hostapd` logs MAC addresses of devices that connect in `/var/log/daemon.log`. This can be incriminating, and should be scrubbed or better still, not logged at all.

## DHCP

* The DHCP lease period is 1h. This may be too long given the device is only serving a /24.
* Currently `dnsmasq` logs MAC addresses of the requesting device in `/var/log/daemon.log` when it receives a DHCP request. This can be incriminating, and should be scrubbed or better still, not logged at all.

## Web Server

* d

# TODO

Stuff that I need help with, or may come back to

## WLAN AP

* Get help with hostapd config (not sure which things should be enabled) e.g. (but not limited to) `country_code`, `ieee80209d`, `ieee80211h` [hostapd doco](https://wireless.wiki.kernel.org/en/users/Documentation/hostapd)
* work out how to scrub MAC addresses from daemon.log

## Webserver

* make not about how HSTS will mean that not all sites can redirect to the portal - some will refuse to load outright
* redirect https and http to us?

## General System

* set host and domain
* firewall
  * make sure http, dhcp, dns are the only services visible on wlan0 (all others should come from eth0) - document this

## Security review

* change default passwords
* disable pi account and replace with admin type account
* make sure dnsmasq and hostapd output is scrubbed for MAC addresses, that would be incriminating

