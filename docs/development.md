# Developing the ConnectBox software

If you're developing the interface, it's often faster to do development on a virtual machine and do final validation against a real device (Raspberry Pi 3/Raspberry Pi Zero W/NanoPi NEO/Orange Pi Zero/Pine64). If you want to do this, a `Vagrantfile` exists to allow [Vagrant](https://www.vagrantup.com) to automatically provision a virtual machine (running Debian Jessie) that behaves like a ConnectBox in all areas except the provision of a wireless network. It's also easy to directly develop against a device, but it's often a little slower because of the limited resources on the device itself.

## Get Ansible

Whether you're using Vagrant or developing directly against a device, you'll need Ansible to perform the setup. To develop the Ansible playbooks, or develop the ConnectBox software, you'll need to have Ansible 2.4+ and some extra tools. From the directory containing this README, run:

```bash
$ mkdir ~/.virtualenvs
$ virtualenv ~/.virtualenvs/connectbox-pi
$ . ~/.virtualenvs/connectbox-pi/bin/activate
$ pip install -r requirements.txt
```


## Developing against a VM

1. [Install Vagrant](https://www.vagrantup.com/docs/installation/)
1. Run `vagrant up` in this directory to tell Vagrant to bring up the virtual machines and apply the Ansible playbooks. Two VMs are provisioned - IP addresses are shown at the completion of the `vagrant up`. You can ssh without worrying about ssh key setup using `vagrant ssh`
1. Add the recommended lines in `/etc/hosts` per the message at th end of the `vagrant up` run. This is required because the webserver redirects to the name of the host and DNS is not being served by the ConnectBox itself.
1. Run the tests. In the same directory as the `Vagrantfile` run: `TEST_IP=172.28.128.3 python -m unittest discover tests` (assuming your VM IP address is `172.28.128.3`). All the tests should pass.
1. The WiFi Point is not active when running from a virtual machine, but you can still view the ConnectBox Site by browsing to the address e.g. http://ubuntu-vagrant.connectbox/

## Developing against a device from a base image

1. This is identical to deploying a new device, so follow the instructions in the [deployment.md](deployment.md) documentation. You probably want to run the Ansible playbook many times as you do your development, so you will likely want to specify the `developer_mode` variable on your commandline on in the Ansible inventory.

## Developing against a device from a ConnectBox release image

Pre-made release images are distributed on GitHub (https://github.com/ConnectBox/connectbox-pi/releases) . sshd is not running on pre-made release images. To permanently enable it, make a directory called `.connectbox` on your USB storage device and place a file named `enable-ssh` in that folder. Insert your USB storage into the ConnectBox and you will be able to ssh to the ConnectBox as `root/connectbox`. Please change the root password immediately.

## Connecting to the ConnectBox

1. You can access the ConnectBox site by connecting to a WiFi point named "ConnectBox - Free Media". Once connected to the WiFi point, follow the instructions in the splash page to get to the connectbox site.
1. You can also access the ConnectBox Site over ethernet. The Connectbox is discoverable via mDNS/Bonjour so it should be sufficient to browse to http://<hostname>.local e.g. http://connectbox.local 

# Tests

1. We have a test suite. From the parent directory of this document, run: `TEST_IP=<ip-of-your-device> python -m unittest discover tests` . All the tests should pass.

