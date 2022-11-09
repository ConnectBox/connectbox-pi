#!/bin/bash
 
if [ -f /lib/modules/$(uname -r)/kernel/drivers/net/wireless/88x2bu.ko ];
then
  printf "Driver rtl8812bu already exists\n"
else
  if [ -f /lib/modules/$(uname -r)/kernel/driver/net/wirless/rtw88.ko ];
  then
    printf "Skipping the RTl88x2bu and RTL88x2cu since rtw88.ko exsists"
  else
    if [ -d /lib/modules/$(uname -r)/kernel/drivers/net/wireless/realtek/88x2bu ];
    then
      printf "Skipping the rtl88x2bu driver as it is already integrated into the kernel\n"
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
      sudo insmod rtw88.ko
	  sudo insmod rtwusb.ko
      sudo cp *.ko /lib/modules/$(uname -r)/kernel/drivers/net/wireless/
      sudo depmod
    fi
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
