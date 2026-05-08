#! /usr/bin/env python3
import os

def _get_axp_port():
    try:
        with open("/proc/cpuinfo") as f:
            cpuinfo = f.read()
        if "Raspberry" in cpuinfo and "Compute Module" in cpuinfo:
            return 10  # CM4
        if "Radxa CM3" in cpuinfo:
            return 0   # RM3
    except Exception:
        pass
    return 0  # NEO default

try:
    import smbus2
    from axp209 import AXP209, AXP209_ADDRESS
    axp = AXP209(_get_axp_port())
    hexval = axp.bus.read_byte_data(AXP209_ADDRESS, 0x32)
    hexval = hexval | 0x80
    axp.bus.write_byte_data(AXP209_ADDRESS, 0x32, hexval)
except Exception:
    pass

# Always ensure OS shuts down cleanly regardless of AXP209 outcome
os.system("/sbin/shutdown -h now")
