# Making a ConnectBox

The ConnectBox runs on Raspbian Lite and is setup using Ansible.

## Install Vanilla Raspbian-lite on Raspberry Pi

Follow the [Raspberry Pi install instructions](https://www.raspberrypi.org/documentation/installation/installing-images/). Boot the Raspberry Pi with the image. This assumes that your Pi is attached to the network via its ethernet port, so that the wifi interface can be configured as an AP. Make a note of the IP address associated with the ethernet interface when it boots.

Until [Issue 43](https://github.com/ConnectBox/connectbox-pi/issues/43) is resolved, use Raspbian 2016-09-27.

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

## Use the ConnectBox

1. Search for, and connect to the WiFi point named "ConnectBox - Free Media"
1. Open your browser, go somewhere (anywhere)
