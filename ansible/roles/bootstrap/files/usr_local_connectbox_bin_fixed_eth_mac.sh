#!/bin/sh
# Give a NanoPi NEO's built-in ethernet a fixed MAC address (fix 63).
#
# Run by udev (/etc/udev/rules.d/72-connectbox-fixed-eth-mac.rules) when the
# interface appears, before ifupdown brings it up:
#     fixed_eth_mac.sh <interface>
#
# Why: the H3 has no MAC address stored in hardware, and the NanoPi NEO device
# tree in Armbian 23.02 has no "ethernet0" alias, so U-Boot cannot pass on the
# MAC it makes from the chip's ID and the kernel picks a random one at every
# boot.  The box ID (connectbox-manage get.boxid, phonehome.py) is the eth0
# MAC, so the cloud server saw a new box after each reboot.
#
# The MAC is made from the chip's unique ID (sunxi SID): the first 5 bytes of
# its SHA-256, after 02 (a locally administered, unicast address).  Same chip,
# same MAC - across reboots and re-imaging - and different on every box.  It
# does not use /etc/machine-id, which is the same on every box made from the
# image.  The Wi-Fi MACs are not touched (macchanger rotates those on purpose).

IF="$1"
SID=/sys/bus/nvmem/devices/sunxi-sid0/nvmem
[ -n "$IF" ] || exit 0

# The SID driver is built into the kernel, but wait briefly in case it is late
n=0
while [ ! -r "$SID" ] && [ $n -lt 10 ]; do sleep 0.5; n=$((n + 1)); done
if [ ! -r "$SID" ]; then
    logger -t fixed_eth_mac "$IF: no chip ID ($SID), MAC left as it is"
    exit 0
fi
ID=$(od -An -tx1 -N16 "$SID" | tr -d ' \n')
case "$ID" in
    ""|00000000000000000000000000000000)
        logger -t fixed_eth_mac "$IF: chip ID is empty, MAC left as it is"
        exit 0 ;;
esac

H=$(head -c 16 "$SID" | sha256sum | cut -c1-10)
MAC=$(echo "02$H" | sed 's/../&:/g; s/:$//')

CUR=$(cat "/sys/class/net/$IF/address" 2>/dev/null)
if [ "$CUR" = "$MAC" ]; then
    exit 0
fi
if ip link set dev "$IF" address "$MAC"; then
    logger -t fixed_eth_mac "$IF: MAC set to $MAC (was $CUR)"
else
    logger -t fixed_eth_mac "$IF: could not set MAC $MAC (still $CUR)"
fi
exit 0
