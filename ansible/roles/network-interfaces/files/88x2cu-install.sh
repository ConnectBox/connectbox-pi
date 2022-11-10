#!/usr/bin/bash
 
if [ -f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/88x2cu.ko ];
then
  printf "Driver rtl8812cu already exists\n"
else
  if [ -d /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/88x2cu ];
  then
    printf "Skipping the rtl88x2cu driver as it is already integrated into the kernel\n"
  else
    printf "Compiling the RTL88x2cu driver then installing\n"
    reboot = "yes"
    if [ -d ./rtl88x2cu];
    then
      printf "Destination git directory already exsists\n"
    else
      git clone --depth 1 https://github.com/brektrou/rtl8821CU
    fi
    sudo ln -s linux $(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
    printf '\nyour running version $(uname -r) \n'
    cd ./rtl8821CU/
    sed -i 's/CONFIG_PLATFORM_I386_PC = y/CONFIG_PLATFORM_I386_PC = n/g' Makefile
    sed -i 's/CONFIG_PLATFORM_ARM_RPI = n/CONFIG_PLATFORM_ARM_RPI = y/g' Makefile
    if [ $(uname -m) == "aarch64" ]
    then
      sed -i 's/CONFIG_PLATFORM_ARM_RPI = y/CONFIG_PLATFORM_ARM_RPI = n/g' Makefile
	    sed -i 's/CONFIG_PLATFORM_ARM64_RPI = n/CONFIG_PLATFORM_ARM64_RPI = y/g' Makefile
	    printf ' We changed to 64bit compile \n'
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
      sudo insmod 88x2cu.ko
      sudo cp 88x2cu.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
      sudo depmod
    fi
    rm -r ./88x2cu
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