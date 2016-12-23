# ConnectBox

ConnectBox is a media sharing device based on small form factor computers like the Raspberry Pi.

# Quick Start

How to deploy what's in this repo.

## Get Ansible

This project uses Ansible v2.1+ with some additional, optional tools. Ansible does not run on the Raspberry Pi itself, but is instead run from a different machine like a separate server or a workstation. There are many ways to install Ansible, but package managers normally have an outdated version that is not suitable. Steps for installing to a python virtualenv are included below, as one way to install a suitable version and some additional tools. From the directory containing this README, run:

```
$ mkdir ~/.virtualenvs
$ virtualenv ~/.virtualenvs/connectbox-pi
$ . ~/.virtualenvs/connectbox-pi/bin/activate
$ pip install -r requirements.txt
```

## Option 1: Running on a Raspberry Pi

## Install Vanilla Raspbian-lite on Raspberry Pi

Follow the [Raspberry Pi install instructions](https://www.raspberrypi.org/documentation/installation/installing-images/). Boot the Raspberry Pi with the image. This assumes that your Pi is attached to the network via its ethernet port, so that the wifi interface can be configured as an AP. Make a note of the IP address associated with the ethernet interface when it boots.

## Run Ansible

Note that this should be run on the same machine where you setup your virtualenv - don't try to run it on the Raspberry Pi

1. cd into the `ansible` directory in this project.
1. Edit `inventory` and add a line with the IP address of the Raspberry Pi ethernet interface and `user=pi` (copy the format of the example line)
1. Confirm connectivity by running `ansible --ask-pass -i inventory all -m ping` . You will be prompted for the password for the pi user, which is still the default of _raspberry_ . If you do not see a **pong** response, then you'll have to revisit your connectivity before continuing.
1. _Optional_: If you're developing and want to avoid entering the password for each ansible run, use/reuse an ssh key pair. I'm reusing one: `ssh pi@192.168.20.183 "mkdir /home/pi/.ssh; chmod 700 /home/pi/.ssh"` and `scp ~/.ssh/id_rsa.pub pi@192.168.20.183:/home/pi/.ssh/authorized_keys` (`192.168.20.183` is the IP of my Pi)
1. **Commands assume ssh keys are setup from here**. If you haven't set them up, just add `--ask-pass` to the `ansible` or `ansible-playbook` command line and you'll be right.
1. Run the playbook: `ansible-playbook -i inventory site.yml`. No tasks should fail.

### Use the ConnectBox

1. Search for, and connect to the WiFi point named "ConnectBox - Free Media"
1. Open your browser, go somewhere (anywhere)

## Options 2: Running on a virtual machine

It's often faster to do development on a virtual machine and do final validation against a Raspberry Pi. A `Vagrantfile` exists in this directory.

### Vagrant

With Vagrant installed, run `vagrant up` in this directory and the VM will start and have the ansible playbooks applied to them. You can reapply the playbooks with `vagrant provision` to test ansible playbook development. Have a look at [Vagrant - Getting Started](https://www.vagrantup.com/docs/getting-started/) for more details.

1. Install Vagrant
1. Run `vagrant up` in this directory. Vagrant takes care of starting the VM and applying the playbooks. You can ssh to the VM using `vagrant ssh`. The webserver is accessible on the VM on the IP `172.28.128.3`
1. (Optionally) run the tests. In this directory: `TEST_IP=172.28.128.3 python -m unittest discover tests`


### Browse the ConnectBox Site

The WiFi Point is not active when running from a virtual machine, but you can still view the ConnectBox Site. On the machine where you ran vagrant:

1. To `/etc/hosts` on the machine where you ran vagrant, add the line `172.28.128.3 connectbox.local`
1. Browse to http://connectbox.local

# Notes

The foundation of documentation and other stuff.

Useful references:

* https://www.pi-point.co.uk/closedcloud-walkthrough/
* https://wiki.alpinelinux.org/wiki/Raspberry_Pi_3_-_Configuring_it_as_wireless_access_point_-AP_Mode
* https://learn.adafruit.com/setting-up-a-raspberry-pi-as-a-wifi-access-point/install-software (uses isc-dhcp-server instead of dnsmasq)

## System

* Alter the ipv4 config on the WLAN side by overriding the ipv4 variables in `ansible/roles/network-interfaces/defaults`
* Firewall rules only allow traffic from the LAN side. SSH access is denied from the WLAN
* Firewall rules only allow http, dhcp and dns from the WLAN

## WLAN Access Point

* Override SSID on ansible command line with `-e ssid="some ssid"` (or use other ansible methods like `host_vars`)

## DHCP and DNS

* The DHCP lease period is 1h. This may be too long given the device is only serving a /24.
* Currently `dnsmasq` logs MAC addresses of the requesting device in `/var/log/daemon.log` when it receives a DHCP request. This can be incriminating, and should be scrubbed or better still, not logged at all. Also need to deal with the DHCP lease file `/var/lib/misc/dnsmasq.leases` and `/var/log/syslog`
* `dnsmasq` tells the connectbox to use it as the DNS resolver, so even when you have a connection via the ethernet port, it cannot resolve names. To alter this, change `/etc/resolv.conf` and replace `127.0.0.1` with a real nameserver in the `nameserver` line.

## Web Server

* Content on the first usb drive is exposed to the webserver in the content directory. The drive is auto-mounted.
* Automatically redirect to content having connected to the WiFi
