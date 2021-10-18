#!/bin/bash
cd /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
if [ -f 8812au.ko ]
  then
    printf "skipping compile of 8812au.sh it already exsists"
    cd /tmp
  else
    cd /tmp
    sudo apt update
    sudo apt -y upgrade
    sudo apt -y install build-essential bc git wget libelf-dev libssl-dev
    sudo apt -y install raspberrypi-kernel-headers
    if [ -d rtl8812au-5.9.3.2 ]
      then
        sudo rm -r rtl8812au-5.9.3.2
    fi
    git clone --depth 1 https://github.com/gordboy/rtl8812au-5.9.3.2
    # alternate github repository is https://github.com/aircrack-ng/rtl8812au
    sudo ln -s linux $(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
    printf ' you running version ' $(uname -r)
    cd ./rtl8812au-5.9.3.2/
    sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
    sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
    sed -i 's/CONFIG_POWER_SAVING = y/CONFIG_POWER_SAVING = n/g' Makefile
    printf "/n"
    if [ -f install.sh ]
      then
        printf " using install.sh /n"
        sudo chmod +x install.sh
        sudo sh ./install.sh
      else
        printf " using Makefile to build /n"
        sudo make -j4
        sudo make install
        fprint 'Make is complete ready to install/n'
        sudo insmod 8812au.ko
        sudo cp 8812au.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
        sudo depmod
    fi
    printf "system will need to be rebooted"
    sudo apt -y remove build-essential bc libssl-dev 
    sudo rm -r /lib/modules/$(uname -r)/build
    sudo rm /tmp/rtl8812au-5.9.3.2
    sudo rm 8812au-install.sh
fi



