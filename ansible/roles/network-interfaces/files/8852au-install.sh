#!/usr/bin/bash
 
if [ -f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/88x2cu.ko ];
then
  printf "Driver rtl8812cu already exists\n"
else
  if [ -d /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/rtw89 ];
  then
    printf "Skipping the rtl8852cu driver as it is already integrated into the kernel\n"
  else
    printf "Compiling the RTL8852qu driver then installing\n"
    reboot = "no"
    if [ -d ./rtl8852au];
    then
      printf "Destination git directory already exsists\n"
    else
      git clone --depth 1 https://github.com/lwfinger/rtl8852au
    fi
    sudo ln -s linux $(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
    printf '\nyour running version $(uname -r) \n'
    cd ./rtl8821CU/
    sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
    sed -i 's/CONFIG_PLATFORM_NV_TK1_UBUNTU = n/CONFIG_PLATFORM_NV_TK1_UBUNTU = y/g' Makefile
#    if [ $(uname -m) == "aarch64" ]
#    then
#      sed -i 's/CONFIG_PLATFORM_ARM_RPI = y/CONFIG_PLATFORM_ARM_RPI = n/g' Makefile
#	    sed -i 's/CONFIG_PLATFORM_ARM64_RPI = n/CONFIG_PLATFORM_ARM64_RPI = y/g' Makefile
#	    printf ' We changed to 64bit compile \n'
#	  fi 
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
      sudo insmod 8852au.ko
      sudo cp 8852au.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
      sudo depmod
    fi
    rm -r ../rtl8852au
  fi
fi

if [ -n "$reboot" ];
then
  printf "system will need to be rebooted\n"
fi
