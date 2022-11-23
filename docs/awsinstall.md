# Installing on AWS

These videos will demonstrate how to build The Well on an AWS instance for development and testing purposes.  You will need an AWS account and basic understanding of using AWS to find this most helpful.

* Start AWS EC2 instance (a server): https://www.loom.com/share/39624989bfa5458db8d6e79141623b81?sharedAppSource=personal_library
* Setup DNS for the new instance on AWS Route 53: https://www.loom.com/share/389ace3911df48f6a1c6da7920e59fac?sharedAppSource=personal_library
* Initialize SSH using your key: https://www.loom.com/share/fb2e8c0e1811442bb2189762f061101d?sharedAppSource=personal_library
* Run Ansible to install The Well software onto AWS instance: https://www.loom.com/share/ca558202c06047c687c6bdbb8366fa80?sharedAppSource=personal_library

Example inventory file: https://github.com/ConnectBox/connectbox-pi/blob/master/ansible/inventory.example

Typical Ansible command (be in the ansible directory of this repo): ansible-playbook -i inventory site.yml 
