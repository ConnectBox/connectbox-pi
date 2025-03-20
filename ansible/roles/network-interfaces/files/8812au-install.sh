#!/usr/bin/bash

if [ -f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/8812au.ko ];
then
  printf "Driver rtl8812au.ko already exsists\n"
else
  if [ -d /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/8xxxu ];
  then
    printf "Skipping the RTL8812au driver as it is integrated into the kernel\n"
  else
    printf "Compiling the RTL8812au driver then installing\n"
    reboot = "no"
    if [ -d ./8812au-20210820 ];
    then
      printf "Destination git directory already exsists\n"
    else
      git clone --depth 1 https://github.com/morrownr/8812au-20210820
    fi
    # alternate github repository is https://github.com/aircrack-ng/rtl8812au
    sudo ln -s linux $(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
    printf "\nyou running version"+"$(uname -r)\n"
    cd ./8812au-20210820/
    sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
    sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
    sed -i 's/CONFIG_POWER_SAVING = y/CONFIG_POWER_SAVING = n/g' Makefile
    printf "we check for 64 bit architecture $(uname -m)"
    if [ $(uname -m) == "aarch64" ]
    then
      sh ARM64_RPI.sh
      echo "we ran ARM64_RPI.sh"
    fi
    if [ -f install.sh ];
    then
      printf "using install.sh\n"
      sudo chmod +x install.sh
      sudo sh ./install.sh
    else
      printf "using Makefile to build\n"
      sudo make -j4
      sudo make install
      printf 'Make is complete ready to install\n'
      sudo insmod 8812au.ko
      sudo cp 8812au.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
      sudo depmod
      rm -r /tmp/8812a8-20210820
    fi
  fi
fi 
sleep 2

if [ -n "$reboot" ];
then
  printf "system will need to be rebooted\n"
fi
