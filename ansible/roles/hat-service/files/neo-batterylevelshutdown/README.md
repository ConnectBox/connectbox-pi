# neo-batterylevelshutdown — Power Shutdown Logic

## Overview

The `neo-batterylevelshutdown` service monitors battery level, drives the OLED display, handles button presses, and initiates device shutdown. It runs as root via systemd (`neo-battery-shutdown.service`) and starts the service entry point at `/usr/local/connectbox/battery_tool_venv/bin/neo_batterylevelshutdown`.

---

## Startup sequence (`cli.py`)

1. Reads `/usr/local/connectbox/brand.j2` to determine device type (NEO, CM4, RM3, PI).
2. Waits for first-boot partition expansion to complete (`/usr/local/connectbox/expand_progress.txt`).
3. Calls `getHATClass()` which probes i2c for an AXP209 and reads GPIO test pins to identify the HAT revision:
   - No OLED → `DummyHAT`
   - No AXP209 → `q1y2018HAT` (voltage comparator HAT)
   - AXP209 + PA1 HIGH → `q3y2018HAT` (HAT 4.6.7)
   - AXP209 + PA1 LOW + PG11 HIGH → `q4y2018HAT` (HAT 5/6/CM4/RM3)
   - AXP209 + PA1 LOW + PG11 LOW → `q3y2021HAT` (HAT 7)
4. Starts `mainLoop()` on the detected HAT class.

---

## Shutdown trigger paths

There are two independent paths that lead to `shutdownDevice()`:

### Path 1 — Left button held (software trigger)

```
User holds left button >= ~5 seconds
  → GPIO falling-edge interrupt on PIN_L_BUTTON
  → buttons.handleButtonPress()
  → buttons.checkPressTime()
      polls GPIO while button held, breaks at CHECK_PRESS_THRESHOLD_SEC + 1 = 5 sec
      if single long press (>= 4 sec, no dual press): fall through
  → hats.BasePhysicalHAT.shutdownDevice()
```

The threshold constants in `buttons.py`:
- `CHECK_PRESS_THRESHOLD_SEC = 4` — minimum hold time to qualify as a long press
- Loop breaks at `CHECK_PRESS_THRESHOLD_SEC + 1 = 5` seconds

### Path 2 — AXP209 hardware interrupt (hardware trigger)

```
AXP209 EXTEN pin goes LOW (battery below Voff, or PB1 held 8+ sec)
  → GPIO falling-edge interrupt on PIN_AXP_INTERRUPT_LINE
  → hats.BasePhysicalHAT.shutdownDeviceCallback()
  → hats.BasePhysicalHAT.shutdownDevice()
```

The AXP209 Voff threshold is set to 3.0 V during init (register 0x31 = 0x04). The hardware automatically cuts power when battery voltage drops below this level, regardless of whether the software shutdown path works.

---

## shutdownDevice() (`hats.py`, `BasePhysicalHAT`)

```python
def shutdownDevice(self):
    GPIO.output(self.PIN_LED, GPIO.HIGH)   # turn off LED
    self.display.showPoweringOff()          # show "Powering Off" on OLED
    logging.info("Exiting for Shutdown")
    os.system("/usr/local/bin/poweroff/poweroff")
    time.sleep(5)
    while True:
        pass                               # hold interrupt thread; keep display on
```

This runs in the GPIO interrupt callback thread. The `while True: pass` intentionally blocks that thread forever to keep the "Powering Off" display active. The main loop continues running independently. After `DISPLAY_TIMEOUT_SECS = 120` seconds, the main loop will blank the display — this is expected and normal if power has not yet cut.

---

## The poweroff script chain

```
/usr/local/bin/poweroff/poweroff        (symlink or binary)
  → /usr/local/connectbox/bin/shutdownShell.sh
      source /usr/local/connectbox/battery_tool_venv/bin/activate
      python3 /usr/local/connectbox/bin/shutdown.sh
```

### `shutdown.sh` logic

1. Reads `/proc/cpuinfo` to detect device type and select the correct i2c bus:
   - CM4 (Compute Module): i2c-10
   - RM3 (Radxa CM3): i2c-0
   - NEO (default): i2c-0
2. Opens AXP209 on that bus and sets bit 7 of register 0x32 — signals the AXP209 to cut power.
3. **Always** calls `/sbin/shutdown -h now` as a final step, regardless of whether the AXP209 step succeeded. This ensures a clean OS shutdown even if the AXP209 is unreachable.

The entire AXP209 block is wrapped in `try/except` so import failures (e.g. broken venv) or i2c errors do not prevent the OS shutdown from running.

---

## AXP209 configuration (set during `Axp209HAT.__init__`)

| Register | Value | Purpose |
|----------|-------|---------|
| 0x31 | 0x04 | Voff = 3.0 V (hardware auto-shutdown voltage) |
| 0x32 | 0x43 | Shutdown delay = 3 sec; EXTEN output enabled |
| 0x33 | 0xC9 | Charge target = 4.2 V, charge current = 1200 mA |
| 0x36 | 0x5F | PEK long-press time extended |
| 0x82 | 0xF3 | ADC enables (battery voltage, current, APS, temp) |

---

## GPIO pin assignments by HAT and device

| Signal | q3y2018 NEO | q4y2018 NEO | q3y2021 NEO | q4y2018 CM4 |
|--------|-------------|-------------|-------------|-------------|
| LED | 12 (PA6) | 12 (PA6) | 12 (PA6) | 6 (GPIO6) |
| Left button | 8 (PA1) | 8 (PG6) | 8 (PG6) | 3 (GPIO3) |
| Right button | 10 (PG7) | 10 (PG7) | 10 (PG7) | 4 (GPIO4) |
| AXP interrupt | — | 16 (PG8) | 16 (PG8) | 15 (GPIO15) |

All NEO pin numbers are in BOARD format. CM4 pins are in BCM format.

---

## Deployment notes

### Line endings
All shell scripts and Python scripts **must have Unix LF line endings**. Windows CRLF causes `#!/bin/bash^M: bad interpreter` on Linux — the script fails silently, `os.system()` returns an error that `shutdownDevice()` ignores, and the device never shuts down. The `.gitattributes` file at the repo root enforces LF for `*.sh` and `*.py`.

Verify with: `cat -A /usr/local/connectbox/bin/shutdownShell.sh | head -1`
Should show `#!/bin/bash$` — a `^M` before `$` means CRLF.
Fix with: `sed -i 's/\r//' <file>`

### Required filesystem layout
```
/usr/local/bin/poweroff/
  poweroff          ← executable (symlink to shutdownShell.sh, or compiled binary)
  _internal/        ← only needed if poweroff is a PyInstaller-compiled binary

/usr/local/connectbox/bin/
  shutdownShell.sh  ← bash wrapper, activates venv, calls shutdown.sh
  shutdown.sh       ← Python, does AXP209 i2c write + /sbin/shutdown -h now
```

The Ansible bootstrap role creates `/usr/local/bin/poweroff/` and deploys the compiled `poweroff` binary (mode 0755). If that binary is absent, a symlink to `shutdownShell.sh` works as a fallback:
```bash
mkdir -p /usr/local/bin/poweroff
ln -sf /usr/local/connectbox/bin/shutdownShell.sh /usr/local/bin/poweroff/poweroff
chmod +x /usr/local/connectbox/bin/shutdownShell.sh /usr/local/connectbox/bin/shutdown.sh
```
