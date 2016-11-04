# Indigitous Hack

This is a solution to the biblebox-pi challenge as a part of [Indigitous #hack[(https://indigitous.org/hack/challenges/bibleboxpi/) taking place on Nov 4-6 2016. If you're a part of the hack, and would like to collaborate, I'm _@edwin_ on Kingdom Builders slack, or via email at: edwin@wordspeak.org

# Quick Start

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

## WLAN Access Point

* Override SSID on ansible command line with `-e ssid="some ssid"` (or use other ansible methods like `host_vars`)
* **Need help with hostapd.conf** (not sure which things should be enabled) e.g. (but not limited to) `country_code`, `ieee80211d`, `ieee80211h` (https://w1.fi/hostapd/)
