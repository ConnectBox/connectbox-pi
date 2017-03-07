# Making a ConnectBox

The ConnectBox runs on a few different devices, with a specific operating system for each. It requires Raspbian Lite for Raspberry Pi 3 devices and Armbian for Orange Pi Zero and Pine64 devices. The ConnectBox is setup using Ansible.

## Install Vanilla Raspbian-lite on Raspberry Pi

Download the [current Raspbian Jessie Lite](https://www.raspberrypi.org/downloads/raspbian/). The Nov 2016 introduced a security update that disables the SSH daemon by default. The connectbox is deployed using Ansible, which connects to the Raspberry Pi over SSH, so ssh needs to be enabled by mounting the downloaded image and creating a file called ssh in the `/boot` directory. The [security update](https://www.raspberrypi.org/blog/a-security-update-for-raspbian-pixel/) describes other ways to enable ssh. Once the image has been updated to enabled ssh, [put the image on an SD card](https://www.raspberrypi.org/documentation/installation/installing-images/) and boot the Raspberry Pi from it.

## Install Armbian on Orange Pi Zero or Pine64

Download the [Debian Jessie Pine64 Armbian Server Legacy Image](https://www.armbian.com/pine64/) put it into an SD card. Do not use a Ubuntu Xenial image as the Ansible playbooks expect Debian. The [Armbian Getting Started Guide](https://docs.armbian.com/User-Guide_Getting-Started/) is useful. Before running ansible, you need to login and set the root password per the Armbian Getting Started Guide.

## Get Ansible

This project uses Ansible v2.1+ with some additional, optional tools. Ansible connects to the device to perform setup activities but is actually run from a different machine, like a separate server or a workstation. There are many ways to install Ansible, but package managers normally have an outdated version that is not suitable. Steps for installing to a python virtualenv are included below, as one way to install a suitable version and some additional tools. From the directory containing this README, run:

```
$ mkdir ~/.virtualenvs
$ virtualenv ~/.virtualenvs/connectbox-pi
$ . ~/.virtualenvs/connectbox-pi/bin/activate
$ pip install -r requirements.txt
```

## Run Ansible

Note that this should be run on the same machine where you setup your virtualenv - don't try to run it on the device itself.

__A default ansible-playbook run will disable sshd and lock out the default user account. Read "Optional Ansible Arguments" if you don't want this__

The rest of this guide assumes that your device is attached to the network via its ethernet port, so that the wifi interface can be configured as an AP. Make a note of the IP address associated with the ethernet interface when it boots.

1. cd into the `ansible` directory in this project.
1. Copy `inventory.example` to `inventory` (in the same directory) and follow the instructions in that file so that ansible knows what type of device it is deploying to.
1. Confirm connectivity by running `ansible --ask-pass -i inventory all -m ping` . You will be prompted for the password for the default user. On a Raspberry Pi, the password will be _raspberry_. On Armbian devices, use the password that you chose on your first login (remembering that you need to login and set the password for the root user on Armbian devices). If you do not see a **pong** response after entering the password, then you'll have to revisit your connectivity before continuing.
1. _Optional_: If you're developing and want to avoid entering the password for each ansible run, use/reuse an ssh key pair. I'm reusing one: `ssh pi@192.168.20.183 "mkdir /home/pi/.ssh; chmod 700 /home/pi/.ssh"` and `scp ~/.ssh/id_rsa.pub pi@192.168.20.183:/home/pi/.ssh/authorized_keys` (`192.168.20.183` is the IP of my device, in this case a Raspberry Pi)
1. **Commands assume ssh keys are setup from here**. If you haven't set them up, just add `--ask-pass` to the `ansible` or `ansible-playbook` command line and you'll be right.
1. Run the playbook: `ansible-playbook -i inventory site.yml`. No tasks should fail.

### Optional Ansible Arguments

- Sample content is deployed by default. To prevent sample content being deployed, add `-e deploy_sample_content=False` to the `ansible-playbook` commandline.
- The Wireless SSID can be changed from the admin interface but it can also be changed at deployment time. To specify a different ssid, add `-e ssid="<new ssid>"` to the `ansible-playbook` commandline e.g. `-e ssid="My Connectbox"`.
- sshd is stopped and disabled by default at the end of the ansible playbook run, and the user account is locked (with `usermod -L`). This is done to prevent unauthorised remote access and console access, particularly if operating system default passwords are not changed. If you do not want this to happen add `-e developer_mode=False` to the `ansible-playbook` commandline, but realise that this leaves the device in an insecure mode. If you have inadvertently locked yourself out, the [Raspbian security update](https://www.raspberrypi.org/blog/a-security-update-for-raspbian-pixel/) describes how to re-enable sshd and you can re-enable the account using information at RaspberryPi Spy - [Reset a lost Raspberry Pi password)[http://www.raspberrypi-spy.co.uk/2014/08/how-to-reset-a-forgotten-raspberry-pi-password/)

## Use the ConnectBox

1. Search for, and connect to the WiFi point named "ConnectBox - Free Media"
1. Open your browser, go somewhere (anywhere)
