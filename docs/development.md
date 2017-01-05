# Developing on a virtual machine

It's often faster to do development on a virtual machine and do final validation against a Raspberry Pi. A `Vagrantfile` exists in this directory.

### Vagrant

With Vagrant installed, run `vagrant up` in this directory and the VM will start and have the ansible playbooks applied to them. You can reapply the playbooks with `vagrant provision` to test ansible playbook development. Have a look at [Vagrant - Getting Started](https://www.vagrantup.com/docs/getting-started/) for more details.

1. Install Vagrant
1. Run `vagrant up` in this directory. Vagrant takes care of starting the VM and applying the playbooks. You can ssh to the VM using `vagrant ssh`. The webserver is accessible on the VM on the IP `172.28.128.3`
1. Install Ansible (see [deployment.md])
1. Add a line in `/etc/hosts` on your host (the machine running Vagrant): `172.28.128.3 connectbox.local` . This is required because the webserver redirects to `http://connectbox.local`.
1. (Optionally) run the tests. In this directory: `TEST_IP=172.28.128.3 python -m unittest discover tests`


### Browse the ConnectBox Site

The WiFi Point is not active when running from a virtual machine, but you can still view the ConnectBox Site. On the machine where you ran vagrant:

1. To `/etc/hosts` on the machine where you ran vagrant, add the line `172.28.128.3 connectbox.local`
1. Browse to http://connectbox.local
