#! /bin/bash

var1=$( modprobe -c | grep 8812au )
var2=$( modprobe -c | grep 88x2bu )
var3=$( modprobe -c | grep 8821cu )

if [ ${#var1} -lt 5 ]							#Check if we have 8812au loaded
then
  echo "Loading 8812au"
  insmod /usr/lib/$( uname -r)/kernel/net/wirless/8812au		#We found nothing so try to load this versions 8812au
  modprobe 8812au
  depmod -A
else
  echo "8812au module already loaded"
fi

if [ ${#var2} -lt 5 ]							#Check if we have 88x2bu loaded
then
  echo "Loading 88x2bu"
  insmod /usr/lib/$( uname -r)/kernel/net/wirless/88x2bu		#We found nothing so try to load this versions 88x2bu
  modprobe 88x2bu
  depmod -A
else
  echo "88x2bu module already loaded"
fi

if [ ${#var3} -lt 5 ]							#Check if we have 88x2bu loaded
then
  echo "Loading 8821cu"
  insmod /usr/lib/$( uname -r)/kernel/net/wirless/8821cu		#We found nothing so try to load this versions 88x2bu
  modprobe 8821cu
  depmod -A
else
  echo "88x2cu module already loaded"
fi
