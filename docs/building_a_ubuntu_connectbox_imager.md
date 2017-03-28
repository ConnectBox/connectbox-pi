# An Easy Guide to Using Ubuntu 16.04 (Xenial) to build ConnectBox Images
by GeoDirk

## Summary
This document describes the steps necessary to build a ConnectBox operating system image using an Ubuntu 16.04 LTS (Xenial) operating system. Ubuntu can be run from a desktop/laptop or hosted inside a virtual machine.

This document assumes that you have gotten as far as having Ubuntu 16.04 installed and running somewhere on the network.

As of the release of this document, the Ansible playbook has been designed to work on the following devices:

- Raspberry Pi 3 (RPi3)
- Raspberry Pi Zero W (RPiZ)
- Pine64
- Orange Pi Zero (OPiZ)

For the remainder of this document, we'll assume that the user is desiring to create a ConnectBox image for a RPi3 device. However, the same principles apply to any of the other devices; just substitute out the approprate commands where needed.

## Prepare Ubuntu 16.04

The first step is to make sure that Ubuntu has been updated to the lastest releases.  Open up a Terminal window and we'll be typing or pasting in these commands:

```
sudo apt-get update
sudo apt-get upgrade -y
```

## Setting up Ansible

Ansible is used as the script engine on this Ubuntu machine to remotely configure the services on the RPi3.  The following are the steps to install Ansible and the environment.  Note that this might take quite a bit of time for each step

```bash
sudo apt-get install language-pack-en-base -y
sudo apt-get install git -y

sudo apt-add-repository ppa:ansible/ansible
```
You'll need to hit the Enter key after this command to accept adding in the repository.

```bash
sudo apt-get update
sudo apt-get install ansible -y
```

## Setting up your Device

We first setup your RPi3 with a fresh base operating system image. Follow the instructions to install the base image on your MicroSD card and boot your device with it (_Install Vanilla Raspbian-lite on Raspberry Pi 3_):

[Deployment Docs](https://github.com/ConnectBox/connectbox-pi/blob/master/docs/deployment.md)

Then setup your SSH keys per that same doco

## Configuring and Running the Ansible Playbook

Let's now clone the ConnectBox Github repository with the follwing commands:

```bash
cd ~
mkdir tmp
cd tmp/
git clone https://github.com/ConnectBox/connectbox-pi.git
cd connectbox-pi/
```

Once complete, continue on with the following:

```bash
cd ansible/
cp inventory.example inventory
nano inventory
```

This will launch an editor of a configuration file that we need to edit.  You will need to modify the following lines for a RPi3 (for other devices, use the proper )

```
[raspberry_pi_3]
#192.168.20.183 ansible_user=pi wireless_country_code=AU
```

__developer_mode=true leaves the connectbox in an insecure state__ - read the doco (reference) to find out whether this is suitable.

We want to modify the second line to first remove the leading `#` comment, change the IP address to our RPi3 device's IP address, and to change the `wireless_country_code` to `developer_mode=True` (make sure that `True` is this case and not "true")

```
[raspberry_pi_3]
192.168.88.26 ansible_user=pi developer_mode=True
```

Use CNTL-X to toggle the files save, a `y` to confirm that you want to exit, and click `Enter` to overwrite the file.

We are now have everything ready to run the Ansible playbook to flash our device.  Start the playbook by using this command:

```bash
ansible-playbook -i inventory site.yml
```

The process will start modifying the RPi3 device and turning it into a ConnectBox.  This process will take a long time so just sit back and surf the internet for cat videos while you monitor its progress:

--snippet--
```bash
(connectbox-pi) box@ubuntu:~/tmp/connectbox-pi/ansible$ ansible-playbook -i inventory site.yml

PLAY [all] *********************************************************************

TASK [setup] *******************************************************************
ok: [192.168.88.26]

TASK [bootstrap : Install aptitude] ********************************************
skipping: [192.168.88.26]

TASK [bootstrap : Add debian signing keys, necessary for backports repo] *******
changed: [192.168.88.26] => (item=7638D0442B90D010)
changed: [192.168.88.26] => (item=8B48AD6246925553)

TASK [bootstrap : Populate apt cache to avoid problems when loading jessie backport repo] ***
changed: [192.168.88.26]

TASK [bootstrap : Enable Jessie backport repo] *********************************
```

Upon completion, you will presented with a summary of what went right and if there were any errors:

```bash
PLAY RECAP *********************************************************************
192.168.88.26              : ok=64   changed=50   unreachable=0    failed=0  
```

If there are no reported errors, your RPi3 is now running as a ConnectBox.  You can add your own content to it (e.g., videos, books, music, etc).

Once you finish that, duplicate the microSD card to quickly create additional ConnectBoxes - you do not need to run this script again.
