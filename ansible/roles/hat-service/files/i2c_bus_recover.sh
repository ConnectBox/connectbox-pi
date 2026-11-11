#!/bin/bash
# Free the front-panel I2C bus if a device is holding SDA low (Raspberry Pi
# builds; run by the hat service's systemd unit before it starts).
#
# The OLED, AXP209 and ATtiny share one bus.  If a transfer is cut off part
# way (e.g. the hat service is stopped mid-read), the device being read can
# keep SDA low, and a reboot does not clear it because the front panel stays
# powered.  Then nothing on the bus answers ("SDA stuck at low" in dmesg) and
# the hat service cannot start (2026-11-10, CM5, twice).  The standard cure is
# to clock SCL until the device releases SDA, then send a STOP.
#
# usage: i2c_bus_recover.sh [BUS] [--force]     BUS defaults to 10
#   --force  run the clock/STOP sequence even if SDA is high (for testing)
# Always exits 0: a problem here must not stop the hat service starting.

BUS=10; FORCE=0
for a in "$@"; do case "$a" in --force) FORCE=1 ;; *) BUS="$a" ;; esac; done
log() { echo "i2c_bus_recover: i2c-$BUS: $*"; }

command -v pinctrl >/dev/null || { log "no pinctrl, skipped"; exit 0; }
node=$(readlink -f "/sys/bus/i2c/devices/i2c-$BUS/of_node" 2>/dev/null)
[ -n "$node" ] && [ -f "$node/pinctrl-0" ] || { log "no device-tree pin information, skipped"; exit 0; }

# The pins come from the bus's pin-control node (first phandle in pinctrl-0).
ph=$(od -An -tx1 -N4 "$node/pinctrl-0" | tr -d ' \n')
pins=""
while read -r f; do
    [ "$(od -An -tx1 -N4 "$f" | tr -d ' \n')" = "$ph" ] || continue
    d=$(dirname "$f")
    if [ -f "$d/pins" ]; then                       # RP1 (Pi 5 / CM5): "gpio38" "gpio39"
        pins=$(tr '\0' '\n' < "$d/pins" | sed -n 's/^gpio\([0-9]\+\)$/\1/p' | sort -n | tr '\n' ' ')
    elif [ -f "$d/brcm,pins" ]; then                # BCM2711 and older: u32 list
        pins=$(od -An -tu1 -v "$d/brcm,pins" | tr -s ' ' '\n' | grep -v '^$' |
               awk '{b[NR%4]=$1} NR%4==0 {print b[1]*16777216+b[2]*65536+b[3]*256+b[0]}' | sort -n | tr '\n' ' ')
    fi
    break
done < <(find /sys/firmware/devicetree/base -name phandle 2>/dev/null)

set -- $pins
[ $# -eq 2 ] || { log "could not find its two pins (got: '$pins'), skipped"; exit 0; }
SDA=$1; SCL=$2                                      # on Raspberry Pi I2C pins SDA is the lower GPIO

if [ "$(pinctrl lev "$SDA")" = "1" ] && [ $FORCE = 0 ]; then
    exit 0                                          # bus free: nothing to do
fi
log "SDA (GPIO$SDA) is low - clocking SCL (GPIO$SCL) to release it"

# Remember the pins' function and pull ("38: a3    pu | lo // ..." -> a3 pu).
read -r _ sda_fn sda_pull _ < <(pinctrl get "$SDA")
read -r _ scl_fn scl_pull _ < <(pinctrl get "$SCL")

pinctrl set "$SDA" ip pu
pinctrl set "$SCL" op dh
for i in $(seq 1 18); do
    pinctrl set "$SCL" dl; pinctrl set "$SCL" dh
    [ "$(pinctrl lev "$SDA")" = "1" ] && [ $i -ge 9 ] && break
done
# STOP: SDA low -> high while SCL is high
pinctrl set "$SDA" op dl; pinctrl set "$SCL" dh; pinctrl set "$SDA" dh
pinctrl set "$SDA" ip pu
state=$(pinctrl lev "$SDA")

pinctrl set "$SDA" "$sda_fn" "$sda_pull"
pinctrl set "$SCL" "$scl_fn" "$scl_pull"
[ "$state" = "1" ] && log "released after $i clock pulses" || log "SDA still low after $i pulses (power-cycle the box)"
exit 0
