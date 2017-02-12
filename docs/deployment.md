# Making a ConnectBox

The ConnectBox runs on Raspbian Lite and is setup using Ansible.

## Install Vanilla Raspbian-lite on Raspberry Pi

Download the [current Raspbian Jessie Lite](https://www.raspberrypi.org/downloads/raspbian/). The Nov 2016 introduced a security update that disables the SSH daemon by default. The connectbox is deployed using Ansible, which connects to the Raspberry Pi over SSH, so ssh needs to be enabled by mounting the downloaded image and creating a file called ssh in the `/boot` directory. The [security update](https://www.raspberrypi.org/blog/a-security-update-for-raspbian-pixel/) describes other ways to enable ssh. Once the image has been updated to enabled ssh, [put the image on an SD card](https://www.raspberrypi.org/documentation/installation/installing-images/) and boot the Raspberry Pi from it.

The rest of this guide assumes that your Pi is attached to the network via its ethernet port, so that the wifi interface can be configured as an AP. Make a note of the IP address associated with the ethernet interface when it boots.

## Get Ansible

This project uses Ansible v2.1+ with some additional, optional tools. Ansible connects to the Raspberry Pi to perform setup activities but is actually run from a different machine, like a separate server or a workstation. There are many ways to install Ansible, but package managers normally have an outdated version that is not suitable. Steps for installing to a python virtualenv are included below, as one way to install a suitable version and some additional tools. From the directory containing this README, run:

```
$ mkdir ~/.virtualenvs
$ virtualenv ~/.virtualenvs/connectbox-pi
$ . ~/.virtualenvs/connectbox-pi/bin/activate
$ pip install -r requirements.txt
```

## Run Ansible

Note that this should be run on the same machine where you setup your virtualenv - don't try to run it on the Raspberry Pi

1. cd into the `ansible` directory in this project.
1. Copy `inventory.example` to `inventory` (in the same directory) and follow the instructions in that file so that ansible can deploy to your Raspberry Pi
1. Confirm connectivity by running `ansible --ask-pass -i inventory all -m ping` . You will be prompted for the password for the pi user, which is still the default of _raspberry_ . If you do not see a **pong** response, then you'll have to revisit your connectivity before continuing.
1. _Optional_: If you're developing and want to avoid entering the password for each ansible run, use/reuse an ssh key pair. I'm reusing one: `ssh pi@192.168.20.183 "mkdir /home/pi/.ssh; chmod 700 /home/pi/.ssh"` and `scp ~/.ssh/id_rsa.pub pi@192.168.20.183:/home/pi/.ssh/authorized_keys` (`192.168.20.183` is the IP of my Pi)
1. **Commands assume ssh keys are setup from here**. If you haven't set them up, just add `--ask-pass` to the `ansible` or `ansible-playbook` command line and you'll be right.
1. Run the playbook: `ansible-playbook -i inventory site.yml`. No tasks should fail.

### Optional Ansible Arguments

- Sample content is deployed by default. To prevent sample content being deployed, add `-e deploy_sample_content=False` to the `ansible-playbook` commandline.
- The Wireless SSID can be changed from the admin interface but it can also be changed at deployment time. To specify a different ssid, add `-e ssid="<new ssid>"` to the `ansible-playbook` commandline e.g. `-e ssid="My Connectbox"`.
- sshd is disabled by default at the end of the ansible playbook run. This is done because it addresses the problem of unauthorised remote access when default passwords are not changed, but does so in a way that it's easy to restore access if it was done by mistake. To leave sshd running at the end of the playbook run add `-e disable_sshd_after_run=False` to the `ansible-playbook` commandline.

## Use the ConnectBox

1. Search for, and connect to the WiFi point named "ConnectBox - Free Media"
1. Open your browser, go somewhere (anywhere)
