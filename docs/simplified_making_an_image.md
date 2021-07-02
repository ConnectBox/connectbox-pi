# Create Image

This is the simplified build procedure for making a SD Card master image for the Raspberry Pi Well device.

* Use a new or reformatted SD Card of 8GB.  Larger may be used but the burner image will not use the extra space.  Future copies of the image will benefit from larger SD Cards for additional storage.
* Download the latest Raspberry Pi OS Lite (Raspbian) image to your computer: https://www.raspberrypi.org/software/operating-systems/.  Be certain to download and use only the Lite version.
* Using Etcher (https://www.balena.io/etcher/), burn the RaspianOS image to the SD Card.
* Eject and reinsert the SD Card.  Using a terminal, navigate to the boot partition on the SD Card and run this command to enable SSH:
```
touch ssh
```
* Use a text editor to modify cmdline.txt and remove the portion that reads (this disables the partition resize on boot):
```
init=/usr/lib/raspi-config/init_resize.sh
```
* Eject the SD Card and place it into the Raspberry Pi device and boot the Pi.  Determine the IP Address of the device (https://www.raspberrypi.org/documentation/remote-access/ip-address.md)
* Navigate to the ansible directory of this repo and create an inventory file with a single configuration row like this: 
```
<IPADDRESS> ansible_user=pi connectbox_default_hostname=thewell wireless_country_code=US do_image_preparation=true 
```
* Execute Ansible command to create the image: 
```
ansible-playbook -i INVENTORYFILEPATH site.yml 
```
* Ensure that the Ansible process completes to the end.  The Pi will shutdown at the end of the process.  Remove the SD Card.  The SD card now contains a small release image for The Well!  
* Insert the SD Card back in the Mac / PC.
* Copy the image from the device.
  * Mac example (use the df command to determine the disk id such as /dev/disk4 and give a filename such as thewell-20210624-0621.img: 
  ```
  sudo dd bs=1m count=3550 if=/dev/<DISKID> of=<FILENAME>
  ```
  * Compress the image with a command like this:
  ```
  xz <FILENAME>
  ```
  * Now your finished and compressed image is called something like thewell-20210624-0621.img.xz
  * You can test the image by taking a new SD Card and using Etcher to burn the new image to the card.  Boot the card in a Pi and wait a few minutes for the initial configuration and look for the SSID of TheWell to become visible.
