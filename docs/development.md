# Developing the ConnectBox software

If you're developing the interface, it's often faster to do development on a virtual machine and do final validation against a real device (Raspberry Pi 3/Raspberry Pi Zero W/Orange Pi Zero/Pine64). If you want to do this, a `Vagrantfile` exists to allow [Vagrant](https://www.vagrantup.com) to automatically provision a virtual machine (running Debian Jessie) that behaves like a ConnectBox in all areas except the provision of a wireless network. It's also easy to directly develop against a device, but it's often a little slower because of the limited resources on the device itself.

## Get Ansible

Whether you're using Vagrant or developing directly against a device, you'll need Ansible to perform the setup. To develop the Ansible playbooks, or develop the ConnectBox software, you'll need to have Ansible 2.1+ and some extra tools. From the directory containing this README, run:

```bash
$ mkdir ~/.virtualenvs
$ virtualenv ~/.virtualenvs/connectbox-pi
$ . ~/.virtualenvs/connectbox-pi/bin/activate
$ pip install -r requirements.txt
```


## Developing against a VM

1. [Install Vagrant](https://www.vagrantup.com/docs/installation/)
1. Run `vagrant up` in this directory to tell Vagrant to bring up the virtual machine and apply the Ansible playbooks. The VM is accessible at `172.28.128.3` but you can ssh without worrying about ssh key setup using `vagrant ssh`
1. Add a line in `/etc/hosts` on the machine where you run Vagrant: `172.28.128.3 connectbox.local` . This is required because the webserver redirects to `http://connectbox.local` and DNS is not being served by the ConnectBox itself.
1. Run the tests. In this directory: `TEST_IP=172.28.128.3 python -m unittest discover tests` . All the tests should pass.
1. The WiFi Point is not active when running from a virtual machine, but you can still view the ConnectBox Site by browsing to http://connectbox.local

## Developing against a Device

1. This is identical to deploying a new device, so follow the instructions in the [deployment.md](deployment.md) documentation. You probably want to run the Ansible playbook many times as you do your development, so you will likely want to specify the `developer_mode` variable on your commandline on in the Ansible inventory.

1. You can access the ConnectBox site by connecting to a WiFi point named "ConnectBox - Free Media". Once connected to the WiFi point, go somewhere (anywhere) in your browser and you should be redirected to the ConnectBox site.
1. You can also access the ConnectBox Site over ethernet. To do so add an entry in `/etc/hosts` on the machine where you ran Ansible, add the line `<ip-of-your-device> connectbox.local` . Then browse to http://connectbox.local
1. Run the tests. In this directory: `TEST_IP=<ip-of-your-device> python -m unittest discover tests` . All the tests should pass.

