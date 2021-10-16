#!/bin/bash
sudo apt update
sudo apt -y upgrade
sudo apt -y install build-essential bc git wget libelf-dev libssl-dev
sudo apt -y install raspberrypi-kernel-headers
if [(-f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/8812au.ko) | (-f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/88X2u.ko)]
then
  printf "Skipping the RTL8812au driver as it already exists"
else
  printf "Compiling the RTL8812au driver then installing"
  if (-d ./rtl8812au-5.9.3.2]
  then
    printf "Destination git directory already exsists"
  else
    git clone --depth 1 https://github.com/gordboy/rtl8812au-5.9.3.2
  fi
  # alternate github repository is https://github.com/aircrack-ng/rtl8812au
  sudo ln -s linux $(uname -r)
  sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
  printf '\nyou running version\n'$(uname -r)
  cd ./rtl8812au-5.9.3.2/
  sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
  sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
  sed -i 's/CONFIG_POWER_SAVING = y/CONFIG_POWER_SAVING = n/g' Makefile
  if [[-f install.sh]]
  then
    printf "\nusing install.sh\n"
    sudo chmod +x install.sh
    sudo sh ./install.sh
  else
    printf "\nusing Makefile to build\n"
    sudo make -j4
    sudo make install
    pause 'Make is complete ready to install'
    sudo insmod 8812au.ko
    sudo cp 8812au.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
    sudo depmod
  fi
fi
if [(-f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/88x2bu.ko) | (-f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/88x2bu.ko)]
then
  printf "Skipping the RTL8812bu driver as it already exists"
else
  printf "Compiling the RTL8812bu driver then installing"
  if (-d ./rtl88x2bu]
  then
    printf "Destination git directory already exsists"
  else
    git clone --depth 1 https://github.com/cilynx/rtl88x2bu
  fi
  sudo ln -s linux $(uname -r)
  sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
  printf '\nyou running version\n'$(uname -r)
  cd ./rtl88x2bu/
  sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
  sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
  sed -i 's/CONFIG_POWER_SAVING = y/CONFIG_POWER_SAVING = n/g' Makefile
  if [[-f install.sh]]
  then
    printf "\nusing install.sh\n"
    sudo chmod +x install.sh
    sudo sh ./install.sh
  else
    printf "\nusing Makefile to build\n"
    sudo make -j4
    sudo make install
    pause 'Make is complete ready to install'
    sudo insmod 88x2bu.ko
    sudo cp 88x2bu.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
    sudo depmod
  fi
fi
printf "system will need to be rebooted"
sudo apt-get remove build-essential bc libssl-dev 
sudo rm /lib/modules/$(uname -r)/build
sudo rm ../$(uname -r)



