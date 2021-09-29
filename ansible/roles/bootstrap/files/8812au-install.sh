#!/bin/bash
echo '\nYou are running version '$(uname -r)'\n'
sudo apt -y update
sudo apt -y install build-essential bc git wget libelf-dev libssl-dev
sudo apt -y install raspberrypi-kernel-headers
cd /home
git clone --depth 1 https://github.com/gordboy/rtl8812au-5.9.3.2
# alternate github repository is https://github.com/aircrack-ng/rtl8812au
sudo ln -s linux $(uname -r)
sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
cd ./rtl8812au-5.9.3.2/
sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
sed -i 's/CONFIG_POWER_SAVING = y/CONFIG_POWER_SAVING = n/g' Makefile
if [[-f install.sh]]
then
  echo "\nusing install.sh\n"
  sudo chmod +x install.sh
  sudo sh ./install.sh
else
  echo "\nusing Makefile to build\n"
  sudo make -j4
  sudo make install
  pause 'Make is complete ready to install'
  sudo insmod 8812au.ko
  sudo cp 8812au.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
  sudo depmod
fi
echo "system will need to be rebooted"
sudo apt-get remove build_essentials bc libssl-dev 
sudo rm /lib/modules/$(uname -r)/build
sudo rm ../$(uname -r)



