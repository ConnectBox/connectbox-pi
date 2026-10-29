#!/usr/bin/env bash
if [[ -z "$1" ]]; then
    echo "you need to provide the hex file as a paramater to program!"
 
else
echo "${1} is the file your going to program"
echo -n "Proceed? [y/n]: "
read ans
  if [[ "$ans" == "y" || "$ans" == "Y" ]]; then
    if [[ -r $1 ]]; then
       sudo systemctl stop neo-battery-shutdown
       sleep 4
       avrdude -P /dev/spidev0.0 -c linuxspi -p t88 -U flash:w:$1
       sleep 2
       sudo systemctl restart neo-battery-shutdown
       echo "finished program and restart of neo-battery-shutdown"
    else
       echo "${1} is not a readable file"
    fi
  else
    echo "Aborting the ATTiny programming by user request"
  fi
fi

