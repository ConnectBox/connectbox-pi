#!/bin/bash
 
if [ -f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/rtw88.ko ];
then
  printf "Driver rtw88.ko already exists\n"
else
  if [ -f /lib/modules/$(uname -r)/kernel/driver/net/wirless/rtwusb.ko ];
  then
    printf "Driver rtw88.ko already exists\n"
  else
    if [ -d /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/rtw88 ];
    then
      printf "Skipping the rtw88 driver as it is already integrated into the kernel\n"
    else
      printf "Compiling the RTW88 driver then installing\n"
      reboot = "no"
      if [ -d ./rtw88-usb];
      then
        printf "Destination git directory already exsists\n"
      else
      git clone --depth 1 https://github.com/kimocoder/rtw88-usb
      fi
	fi
	sudo ln -s linux $(uname -r)
    sudo ln -s /usr/src/linux-headers-$(uname -r) /lib/modules/$(uname -r)/build
    printf 'you running version%s\n' "$(uname -r)"
	printf 'your running version%s\n' "$(uname -m)"
    cd ./rtw88-usb/
	mkdir /lib/modules/$(uname -r)/kernel/driver/net/wirless/realtek/rtw88
    printf "using Makefile to build\n"
    sudo make -j4
    sudo make install
    printf 'Make is complete ready to install\n'
    sudo insmod rtw88.ko
	sudo insmod rtwusb.ko
    sudo cp *.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
	
    sudo depmod
    rm -r ./rtw88-usb
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
