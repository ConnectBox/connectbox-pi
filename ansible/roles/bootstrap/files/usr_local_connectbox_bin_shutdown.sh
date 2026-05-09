#! /usr/bin/env python3
# shutdown.sh — ConnectBox hardware power-off script
#
# Called by shutdownShell.sh (via /usr/local/bin/poweroff/poweroff) after the
# OS has been asked to halt.  This script signals the AXP209 power-management
# IC to physically cut power to the board, then falls back to a clean OS
# shutdown in case the AXP209 is unreachable.
#
# Despite the .sh extension this is a Python 3 script (the shebang selects the
# interpreter).  The extension is kept for historical compatibility with the
# symlink and deploy paths.

import os


def _get_axp_port():
    """Determine which i2c bus the AXP209 is attached to for this hardware.

    The AXP209 power-management IC is wired to different i2c buses depending
    on the SBC variant:
      - Raspberry Pi Compute Module 4 (CM4): i2c-10
      - Radxa CM3 (RM3): i2c-0
      - NanoPi NEO (default): i2c-0

    Detection reads /proc/cpuinfo which is always available on Linux without
    any additional libraries.

    Returns
    -------
    int
        The i2c bus number to pass to AXP209().
    """
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


# -------------------------------------------------------------------------
# AXP209 hardware power-off sequence.
#
# Writing bit 7 of register 0x32 instructs the AXP209 to cut the DCDC/LDO
# outputs after its configured shutdown delay (3 seconds, set during HAT
# init by register 0x32 value 0x43).  This causes an immediate hardware
# power cut rather than waiting for the OS to finish halting.
#
# The entire block is wrapped in try/except for two reasons:
#   1. smbus2 / axp209 may not be installed on all hardware variants.
#   2. The i2c bus may be unreachable (e.g. during early boot or if the
#      AXP209 is absent on Pi-only builds without a HAT).
# A failure here must never prevent the OS shutdown from running.
# -------------------------------------------------------------------------
try:
    import smbus2
    from axp209 import AXP209, AXP209_ADDRESS
    axp = AXP209(_get_axp_port())
    hexval = axp.bus.read_byte_data(AXP209_ADDRESS, 0x32)
    hexval = hexval | 0x80
    axp.bus.write_byte_data(AXP209_ADDRESS, 0x32, hexval)
except Exception:
    pass

# Always ensure OS shuts down cleanly regardless of AXP209 outcome.
# This is the guaranteed fallback: even if the AXP209 step failed (wrong
# bus, missing library, i2c error), the OS will still halt cleanly and
# any remaining disk writes will be flushed before power is cut.
os.system("/sbin/shutdown -h now")
