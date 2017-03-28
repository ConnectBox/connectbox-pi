# Making a ConnectBox

The ConnectBox runs on a few different devices, with a specific operating system for each. It requires Raspbian Lite for Raspberry Pi 3 and Raspberry Pi Zero W devices and Armbian for Orange Pi Zero and Pine64 devices. The ConnectBox is setup using Ansible and is performed using an ethernet connection to the device.

# Terminology

For simplicity, let's assume the following terms:
* __workstation__: The machine where you'll run Ansible. It might be a Linux virtual machine, or server or it might be a laptop running MacOS, or something else. When describing commands to run on the workstation, we'll display the workstation prompt as `box@ubuntu:`.
 Most importantly, the workstation is different to your _device_.
* __device__: The ConnectBox hardware. It might be a Raspberry Pi 3, or it might be one of the other supported devices. When describing commands to be run on the device, we'll display the device prompt as `pi@rasberrypi:` even though it will be different on other devices.

## Install Vanilla Raspbian-lite on Raspberry Pi 3 or Raspberry Pi Zero W

Download the [current Raspbian Jessie Lite](https://www.raspberrypi.org/downloads/raspbian/). The Nov 2016 introduced a security update that disables the SSH daemon by default. The connectbox is deployed using Ansible, which connects to the Raspberry Pi over SSH, so ssh needs to be enabled. Enable sshd by one of the methods below (you only need to choose one):
Note: this is a Raspberry Pi device specific step as the other devices have their SSH enabled]

### Enabling sshd on the device using raspi-config

Connect a keyboard and monitor to the Raspberry Pi and boot it up. Log in using the default credentials of:
 username: pi
 password: raspberry

It is important that you DO NOT do anything further to the Raspberry Pi other than the steps outlined below. The Ansible playbook expects an environment that is factory fresh and any other changes can prevent successful execution.

The snippet below is from the offical Raspbian docs: [Setup SSH](https://www.raspberrypi.org/documentation/remote-access/ssh/)

From the Raspberry Pi command line, run the following command:

```bash
sudo raspi-config

1. Select "Interfacing Options" from the window
3. Navigate to and select "SSH"
4. Choose "Yes"
5. Select "Ok"
6. Choose "Finish"
```

### Enabling sshd on the operating system image

On your desktop, mount the downloaded image and creating a file called ssh in the `/boot` directory. Once the image has been updated to enabled ssh, [put the image on an SD card](https://www.raspberrypi.org/documentation/installation/installing-images/) and boot the Raspberry Pi from it.

## Install Armbian on Orange Pi Zero or Pine64

Download the [Debian Jessie Pine64 Armbian Server Legacy Image](https://www.armbian.com/pine64/) put it into an SD card. Do not use a Ubuntu Xenial image as the Ansible playbooks expect Debian. The [Armbian Getting Started Guide](https://docs.armbian.com/User-Guide_Getting-Started/) is useful. Before running ansible, you need to login and set the root password per the Armbian Getting Started Guide.

## Setup SSH Keys

Ansible connects to your device over ssh. While it *is* possible to run Ansible without ssh keys (using the `--ask-pass` commandline argument), using ssh keys allow for quick, secure, passwordless access and help avoids the playbook failures that can occur during deployment if a password prompt is left for too long.

### Generating an SSH keypair

If you already have an ssh keypair, you can skip this step.

Once the commands are processed, we now need to create a set of SSH keys on our machine that we will eventually use when running the Ansible script over on the RPi3.

```
ssh-keygen
```

Hit return to just accept the defaults until you get back to the command prompt.

```bash
box@ubuntu:~$ ssh-keygen
Generating public/private rsa key pair.
Enter file in which to save the key (/home/box/.ssh/id_rsa): 
Created directory '/home/box/.ssh'.
Enter passphrase (empty for no passphrase): 
Enter same passphrase again: 
Your identification has been saved in /home/box/.ssh/id_rsa.
Your public key has been saved in /home/box/.ssh/id_rsa.pub.
The key fingerprint is:
SHA256:vuUwcoZTkDqakuAT21drYfbSE3WsT36HxBT1g4PzQmI box@ubuntu
The key's randomart image is:
+---[RSA 2048]----+
|              ...|
|       .    o ...|
|      o  E = =...|
|     . .. + =o. .|
|..  o  =S. o oo  |
|o.+o .++= . =. . |
|o+o. .++*+.  o...|
| .. . .=.*.   . .|
|        . .      |
+----[SHA256]-----+
```

### Deploying SSH keys

Find the IP address for the ethernet interface of your device.

A simple method involves connecting a keyboard and monitor, logging in and looking at the output of `ifconfig eth0`. In the example below, the IP address for the **eth0** adaptor is the number: 192.168.88.26  Write this down as we'll need it in a moment.

```bash
pi@raspberrypi:~ $ ifconfig eth0
eth0      Link encap:Ethernet  HWaddr b8:27:eb:e3:7c:1d  
          inet addr:192.168.88.26  Bcast:192.168.88.255  Mask:255.255.255.0
          inet6 addr: fe80::e102:ac35:54f:6479/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:412 errors:0 dropped:10 overruns:0 frame:0
          TX packets:150 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000 
          RX bytes:28756 (28.0 KiB)  TX bytes:19294 (18.8 KiB)
```

Another method involves looking at the logs of your DHCP server to see which address was allocated.

From the command line on your workstation, we'll log into the device remotely so we can pass over our SSH keys. [From here on our, replace the IP address 192.168.88.26 with your specific device's IP address]


```bash
ssh pi@192.168.88.26
```
You'll need to answer "yes" when you are prompted to add in the RPi's fingerprint and then enter in the 's password of "raspberry"

```bash
box@ubuntu:~$ ssh pi@192.168.88.26
The authenticity of host '192.168.88.26 (192.168.88.26)' can't be established.
ECDSA key fingerprint is SHA256:P7Eqv0UkjbG9yWSYE5qzDNc5K6vOqCJ4kQ1fakB2aVk.
Are you sure you want to continue connecting (yes/no)? yes
Warning: Permanently added '192.168.88.26' (ECDSA) to the list of known hosts.
pi@192.168.88.26's password: 

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Thu Mar 16 19:48:28 2017 from 192.168.88.212
pi@raspberrypi:~ $ 
```
We are now inside of the RPi3 so you'll notice that the command prompt has changed to: **pi@raspberrypi:** . From here we create an administrative directory for our ssh keys and set standard permissions.

```bash
pi@raspberrypi:~ $ mkdir ~/.ssh
pi@raspberrypi:~ $ chmod 700 ~/.ssh
```

We want to type `exit` to get back to our Ubuntu prompt:

```bash
pi@raspberrypi:~ $ exit
logout
Connection to 192.168.88.26 closed.
box@ubuntu:~$ 
```
We now copy over our public SSH key to the RPi3 so we no longer need to log in [use your RPi3's IP address]:

```bash
scp ~/.ssh/id_rsa.pub pi@192.168.88.26:.ssh/authorized_keys
```
You'll be prompted for the RPi3's password of "raspberry" one last time.

```bash
box@ubuntu:~$ scp ~/.ssh/id_rsa.pub pi@192.168.88.26:.ssh/authorized_keys
pi@192.168.88.26's password: 
id_rsa.pub                                    100%  392     0.4KB/s   00:00    
box@ubuntu:~$ 
```
We should test that the SSH key transfer worked by trying to once again SSH into the RPi3:

```bash
ssh pi@192.168.88.26
```

You shouldn't be prompted for the password but taken right in [Note: look for the `pi@raspberrypi` at the command prompt to verify that you are inside the RPi3]

```bash
box@ubuntu:~$ ssh pi@192.168.88.26

The programs included with the Debian GNU/Linux system are free software;
the exact distribution terms for each program are described in the
individual files in /usr/share/doc/*/copyright.

Debian GNU/Linux comes with ABSOLUTELY NO WARRANTY, to the extent
permitted by applicable law.
Last login: Thu Mar 16 19:56:01 2017 from 192.168.88.212
pi@raspberrypi:~ $ 
```
Type `exit` to get back to the Ubuntu machine;

```bash
pi@raspberrypi:~ $ exit
logout
Connection to 192.168.88.26 closed.
box@ubuntu:~$ 
```

## Get Ansible

This project uses Ansible v2.1 or above. 

Package managers generally have an out-dated version of ansible, but the [Ansible documentation](http://docs.ansible.com/ansible/intro_installation.html#installing-the-control-machine) lists methods for obtaining Ansible for common platforms.

e.g. for Ubuntu, only the following is necessary (steps taken from the Ansible docs):

```bash
$ sudo apt-get install software-properties-common
$ sudo apt-add-repository ppa:ansible/ansible
$ sudo apt-get update
$ sudo apt-get install ansible
```

The developing.md file lists an alternative method for setting up Ansible using python virtualenvs. If you are developing playbooks, you should follow those instructions.

## Run Ansible

__A default ansible-playbook run will disable sshd and lock out the default user account. Read "Optional Ansible Arguments" if you don't want this__

The rest of this guide assumes that your device is attached to the network via its ethernet port, so that the wifi interface can be configured as an Access Point.

Clone the ConnectBox Github repository to your workstation with the following commands, if you have not already done so:

```bash
cd ~
mkdir tmp
cd tmp/
git clone https://github.com/ConnectBox/connectbox-pi.git
cd connectbox-pi/
```

Once complete, create a copy of the ansible inventory based on the example file:

```bash
cd ansible/
cp inventory.example inventory
```

Open the inventory file in an editor, and uncomment the appropriate line for your device type. For example, you would need to modify the following lines for a RPi3/RPiZero+

```
[raspberry_pi_3]
#192.168.20.183 ansible_user=pi wireless_country_code=AU
```

We want to modify the second line to first remove the leading `#` comment, change the IP address to our RPi3 device's IP address, change the `wireless_country_code` to an [appropriate regulatory domain](https://git.kernel.org/cgit/linux/kernel/git/sforshee/wireless-regdb.git/tree/db.txt) (00 is the default, and may not be appropriate). If you are experimenting with the system, you may want to activate developer mode by setting `developer_mode=true` but know that __developer_mode=true leaves the connectbox in an insecure state__ . Read the Optional Ansible Arguments documentation below to find out whether this is suitable. __developer_mode=true is unsuitable for real-world use__

Once done you will likely have something of this form, and you should save the file:

```
[raspberry_pi_3]
192.168.88.26 ansible_user=pi wireless_country_code=GB
```

Confirm connectivity by running `ansible -i inventory all -m ping` . If you do not see a **pong** response after entering the password, then you'll have to revisit your connectivity before continuing.

We are now have everything ready to run the Ansible playbook to setup our device.  Start the playbook by using this command:

```bash
ansible-playbook -i inventory site.yml
```

The process will start modifying the device and turning it into a ConnectBox.  This process will take a long time so just sit back and surf the internet for cat videos while you monitor its progress:

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

### Optional Ansible Arguments

To use these arguments, add them to the inventory file or add `-e option_name=value` to the `ansible-playbook` commandline e.g. `-e ssid="My Connectbox"` or `-e deploy_sample_content=false`

- __deploy_sample_content__ _(default: true)_: Installs sample files to demonstrate ConnectBox functionality.
- __ssid__ _(default: ConnectBox - Free Media)_: The Wireless SSID can be changed from the admin interface but it can also be changed at deployment time.
- __developer_mode__ _(default: false)_: Developer mode leaves the device in an insecure state, but makes it possible to examine the internal state of the ConnectBox. When developer mode is false _(think, production mode)_, sshd is stopped and disabled by default at the end of the ansible playbook run, and the user account is locked (with `usermod -L`). This is done to prevent unauthorised remote access and console access, particularly if operating system default passwords are not changed. If you have inadvertently locked yourself out, the [Raspbian security update](https://www.raspberrypi.org/blog/a-security-update-for-raspbian-pixel/) describes how to re-enable sshd and you can re-enable the account using information at RaspberryPi Spy - [Reset a lost Raspberry Pi password)[http://www.raspberrypi-spy.co.uk/2014/08/how-to-reset-a-forgotten-raspberry-pi-password/)

## Use the ConnectBox

1. Search for, and connect to the WiFi point named "ConnectBox - Free Media"
1. Open your browser, go somewhere (anywhere)
