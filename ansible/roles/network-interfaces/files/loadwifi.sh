#! /bin/bash

var1=$( modprobe -c | grep 8812au )
var2=$( modprobe -c | grep 88x2bu )
var3=$( modprobe -c | grep 8852au )

if [ ${#var1} -lt 5 ]							#Check if we have 8812au loaded
then
  echo "Loading 8812au"
  insmod /usr/lib/modules/$( uname -r)/kernel/net/drivers/wirless/8812au		#We found nothing so try to load this versions 8812au
  modprobe 8812au
  depmod -A
else
  echo "8812au module already loaded"
fi

if [ ${#var2} -lt 5 ]							#Check if we have 88x2bu loaded
then
  echo "Loading 88x2bu"
  insmod /usr/lib/modules/$( uname -r)/kernel/net/drivers/wirless/88x2bu		#We found nothing so try to load this versions 88x2bu
  modprobe 88x2bu
  depmod -A
else
  echo "88x2bu module already loaded"
fi

if [ ${#var3} -lt 5 ]							#Check if we have 88x2bu loaded
then
  echo "Loading 8852au"
  insmod /usr/lib/modules/$( uname -r)/kernel/drivers/net/wirless/8852au		#We found nothing so try to load this versions 88x2bu
  modprobe 8852au
  depmod -A
else
  echo "8852au module already loaded"
fi
