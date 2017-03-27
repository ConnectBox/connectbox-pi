# An Idiot's Guide to Using Ubuntu 16.04 (Xenial) to build ConnectBox Images
Revision 1.0  March 16, 2017
by GeoDirk (a Linux Idiot)

## Summary
This document describes the steps necessary to build a ConnectBox firmware image using an Ubuntu 16.04 LTS (Xenial) operating system. Ubuntu can be run from a desktop/laptop or hosted inside a virtual machine.

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

After you get the RPi3 booted, you still will need to do some quick minor setup on the RPi3 to ensure that we can communicate with the device. [Note: this is a Raspberry Pi device specific step as the other devices have their SSH enabled]

Connect up some way to log into the RPi3 using a monitor and make sure that the RPi3 has a LAN cable plugged in on the same network as our Ubuntu machine.  Boot up the RPi3 and log in using the default credentials of:
 username: pi
 password: raspberry

It is important that you DO NOT do anything further to the RPi3 other than the steps outlined below as our Ansible script needs an environment that is factory fresh. Any changes to the RPi3 can break the script from completing.

We need to only setup our SSH server on the RPi3 to allow our Ubuntu machine to talk to the RPi3. The below code snippets is from the offical Raspbian docs: [Setup SSH](https://www.raspberrypi.org/documentation/remote-access/ssh/)

From the RPi3 command line, run the following command:

```bash
sudo raspi-config

1. Select "Interfacing Options" from the window
3. Navigate to and select "SSH"
4. Choose "Yes"
5. Select "Ok"
6. Choose "Finish"
```
We now also need to setup the RPi3 to have it automatically accept the SSH certificate from the Ubuntu machine so we don't need to log in with the username and password. So to setup SSH certs on this end, the simpiest way is to run the following commands hitting the `Enter` key to just accept the defaults:

```bash
ssh-keygen
cd .ssh/
touch authorized_keys
```

Last thing we need to do is to get the RPi3's IP address.  Run the command:

```bash
ifconfig
```

And we need to pull out the ipaddress.  In the example below, the IP address for the **eth0** adaptor is the number: 192.168.88.26  Write this down as we'll need it in a moment.

```bash
pi@raspberrypi:~ $ ifconfig
eth0      Link encap:Ethernet  HWaddr b8:27:eb:e3:7c:1d  
          inet addr:192.168.88.26  Bcast:192.168.88.255  Mask:255.255.255.0
          inet6 addr: fe80::e102:ac35:54f:6479/64 Scope:Link
          UP BROADCAST RUNNING MULTICAST  MTU:1500  Metric:1
          RX packets:412 errors:0 dropped:10 overruns:0 frame:0
          TX packets:150 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000 
          RX bytes:28756 (28.0 KiB)  TX bytes:19294 (18.8 KiB)

lo        Link encap:Local Loopback  
          inet addr:127.0.0.1  Mask:255.0.0.0
          inet6 addr: ::1/128 Scope:Host
          UP LOOPBACK RUNNING  MTU:65536  Metric:1
          RX packets:0 errors:0 dropped:0 overruns:0 frame:0
          TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1 
          RX bytes:0 (0.0 B)  TX bytes:0 (0.0 B)

wlan0     Link encap:Ethernet  HWaddr b8:27:eb:b6:29:48  
          inet6 addr: fe80::b624:4967:8365:d9cf/64 Scope:Link
          UP BROADCAST MULTICAST  MTU:1500  Metric:1
          RX packets:2 errors:0 dropped:2 overruns:0 frame:0
          TX packets:0 errors:0 dropped:0 overruns:0 carrier:0
          collisions:0 txqueuelen:1000 
          RX bytes:123 (123.0 B)  TX bytes:0 (0.0 B)
```


## Ubuntu/RPi3 SSH Configuration
Switch back over to your Ubuntu machine so we can now firmly establish our communication ties between the Ubuntu machine and the remote device.

From the command line, we'll now need to log into the RPi3 remotely so we can pass over our SSH keys. [From here on our, replace the IP address 192.168.88.26 with your specific RPi3 device's IP address]

```bash
ssh pi@192.168.88.26
```
You'll need to answer "yes" when you are prompted to add in the RPi's fingerprint and then enter in the RPi3's password of "raspberry"

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
We are now inside of the RPi3 so you'll notice that the command prompt has changed to: **pi@raspberrypi:**

We want to type `exit` to get back to our Ubuntu prompt:

```bash
pi@raspberrypi:~ $ exit
logout
Connection to 192.168.88.26 closed.
box@ubuntu:~$ 
```
We now copy over our public SSH key to the RPi3 so we no longer need to log in [use your RPi3's IP address]:

```bash
scp ~/.ssh/id_rsa.pub pi@192.168.88.21:.ssh/authorized_keys
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



## Configuring and Running the Ansible Playbook

We need to create the virtual environment for our Ubuntu system to run in.  Type the following at the command prompt:

```bash
mkdir ~/.virtualenvs
virtualenv ~/.virtualenvs/connectbox-pi. ~/.virtualenvs/connectbox-pi/bin/activate
```
You should notice that after that last command that your command prompt will change to look like this with the `(connectbox-pi}` prefix:

```bash
box@ubuntu:~$ virtualenv ~/.virtualenvs/connectbox-pi
Running virtualenv with interpreter /usr/bin/python2
New python executable in /home/box/.virtualenvs/connectbox-pi/bin/python2
Also creating executable in /home/box/.virtualenvs/connectbox-pi/bin/python
Installing setuptools, pkg_resources, pip, wheel...done.
box@ubuntu:~$ . ~/.virtualenvs/connectbox-pi/bin/activate
(connectbox-pi) box@ubuntu:~$ 
```

Let's now clone the ConnectBox Github repository with the follwing commands:

```bash
cd ~
mkdir tmp
cd tmp/
git clone https://github.com/ConnectBox/connectbox-pi.git
cd connectbox-pi/
pip install -r requirements.txt
```

The last command will take a while as it sets up the environment and packages to run the Ansible playbook. *[Note that you will probably get some errors about the cryptography.  That is normal and we don't need it for what we are doing]*

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
