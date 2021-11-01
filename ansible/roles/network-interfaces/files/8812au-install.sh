#!/bin/bash

if [ -f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/8812au.ko ];
then
  printf "Driver rtl8812au.ko already exsists\n"
else
  if [ -d /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/8xxxu ];
  then
    printf "Skipping the RTL8812au driver as it is integrated into the kernel\n"
  else
    printf "Compiling the RTL8812au driver then installing\n"
    reboot = "yes"
    if [ -d ./rtl8812au-5.9.3.2 ];
    then
      printf "Destination git directory already exsists\n"
    else
      git clone --depth 1 https://github.com/gordboy/rtl8812au-5.9.3.2
    fi
    # alternate github repository is https://github.com/aircrack-ng/rtl8812au
    sudo ln -s linux $(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
    printf '\nyou running version %s\n', "$(uname -r)"
    cd ./rtl8812au-5.9.3.2/
    sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
    sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
    sed -i 's/CONFIG_POWER_SAVING = y/CONFIG_POWER_SAVING = n/g' Makefile
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
    fi
    rm -r ./rtl8812au-5.9.3.2
  fi
fi  
if [ -f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/88x2bu.ko ];
then
  printf "Driver rtl8812bu already exists\n"
else
  if [ -d /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/88x2bu ];
  then
    printf "Skipping the rtl88x2bu driver as it is already integrated into the kernel\n"
  else
    printf "Compiling the RTL8812bu driver then installing\n"
    reboot = "yes"
    if [ -d ./rtl88x2bu];
    then
      printf "Destination git directory already exsists\n"
    else
      git clone --depth 1 https://github.com/cilynx/rtl88x2bu
    fi
    sudo ln -s linux $(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
    printf 'you running version%s\n' "$(uname -r)"
    cd ./rtl88x2bu/
    sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
    sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
    sed -i 's/CONFIG_POWER_SAVING = y/CONFIG_POWER_SAVING = n/g' Makefile
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
      sudo insmod 88x2bu.ko
      sudo cp 88x2bu.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
      sudo depmod
    fi
    rm -r ./88x2bu
  fi
fi

if [ -n "$reboot" ];
then
  printf "system will need to be rebooted\n"
fi
if [ -f /lib/modules/$(uname -r)/build ]; then sudo rm /lib/modules/$(uname -r)/build
fi
if [ -f ../$(uname -r) ]; then sudo rm ../$(uname -r)
fi

