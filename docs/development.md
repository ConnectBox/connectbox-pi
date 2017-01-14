# Developing the ConnectBox software

If you're developing the interface, it's often faster to do development on a virtual machine and do final validation against a Raspberry Pi. If you want to do this, a `Vagrantfile` exists to allow [Vagrant](https://www.vagrantup.com) to automatically provision a virtual machine (running Debian Jessie) that behaves like a ConnectBox in all areas except the provision of a wireless network. It's also easy to develop against a Raspberry Pi.

## Get Ansible

Whether you're using Vagrant or developing directly against a Raspberry Pi, you'll need Ansible to perform the setup, so follow the _Get Ansible_ instructions in the [deployment.md](deployment.md) documentation.

## Developing against a VM

1. [Install Vagrant](https://www.vagrantup.com/docs/installation/)
1. Run `vagrant up` in this directory to tell Vagrant to bring up the virtual machine and apply the Ansible playbooks. The VM is accessible at `172.28.128.3` but you can ssh without worrying about ssh key setup using `vagrant ssh`
1. Add a line in `/etc/hosts` on the machine where you run Vagrant: `172.28.128.3 connectbox.local` . This is required because the webserver redirects to `http://connectbox.local` and DNS is not being served by the ConnectBox itself.
1. (Optionally) run the tests. In this directory: `TEST_IP=172.28.128.3 python -m unittest discover tests`
1. The WiFi Point is not active when running from a virtual machine, but you can still view the ConnectBox Site by browsing to http://connectbox.local

## Developing against a Raspberry Pi

1. Follow the _Run Ansible_ instructions in the [deployment.md](deployment.md) documentation.
1. You can access the ConnectBox site by connecting to a WiFi point named "ConnectBox - Free Media", but as the ssh port is not accessible from the WiFi network on the Pi, you may want to use a different device. Once connected to the WiFi point, go somewhere (anywhere) in your browser and you should be redirected to the ConnectBox site.
1. You can also access the ConnectBox Site over ethernet. To do so add an entry in `/etc/hosts` on the machine where you ran Ansible, add the line `<ip-of-your-raspberry-pi> connectbox.local` . Then browse to http://connectbox.local
1. (Optionally) run the tests. In this directory: `TEST_IP=<ip-of-your-raspberry-pi> python -m unittest discover tests`
