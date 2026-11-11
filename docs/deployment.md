# Making a ConnectBox

A ConnectBox is built by running this repo's Ansible playbook from a computer
(the *workstation*) against a freshly installed single-board computer (the
*device*) over the network.  The playbook detects the board, installs and
configures everything, and leaves a working ConnectBox.  Pre-made images are
also available for some boards.

## Pre-made images

Release images are on GitHub: https://github.com/ConnectBox/connectbox-pi/releases .
Burn one to a microSD card and boot.  If there is none for your board, build
from scratch as below.

`sshd` is off on release images.  To turn it on, create a folder `.connectbox`
on a USB stick with an empty file `enable-ssh` in it and insert the stick; you can
then log in as `root` / `connectbox`.  Change the root password straight away.

## Supported devices and operating systems

`ansible/site.yml` reads the board model from `/sys/firmware/devicetree/base/model`
and handles:

| Board | Operating system | Ansible logs in as |
|-------|------------------|--------------------|
| NanoPi NEO | Armbian, Debian 11 (Bullseye) - tested | `root` |
| Orange Pi Zero 2 | Armbian | `root` |
| Radxa CM3 | Armbian | `root` |
| Raspberry Pi models, Compute Module 4 and Compute Module 5 | Raspberry Pi OS **Lite**: Trixie (64-bit) tested on a CM4 and a CM5 Lite, Bullseye before | `root` (key from `setup_raspbian_host.sh`, see below) |

The playbook knows Buster and Bullseye (see the comment at the top of
`site.yml`), and since November 2026 Raspberry Pi OS Lite **Trixie** (Debian 13,
kernel 6.18, Python 3.13): it was built and tested on a CM4 Lite on the ConnectBox
carrier board (see [Raspberry Pi OS Trixie](#raspberry-pi-os-trixie-cm4)).  The
other main test unit is a NanoPi NEO on Armbian Bullseye (kernel 5.15).  Orange Pi
Zero 2 and Radxa CM3 have not been rebuilt recently, and Bookworm is untested.

Use a microSD card of at least 8 GB.  The device needs a wired (Ethernet) or
second WiFi connection to the internet during the build, because its main WiFi
adapter becomes the access point.

A plain Raspberry Pi board without the ConnectBox front panel (OLED, buttons, AXP209
battery board) also works: the front-panel service finds no AXP209 and runs without
it.

Use **one or two** USB WiFi adapters.  With two, PxUSBm puts the access point on the
adapter that can run one (a Realtek RTL88xx first) and uses the other as the client;
with three or more it leaves the configuration alone ("must be manually managed"),
and the access point can end up on an adapter that cannot run one (an MT7601U, for
example).

The admin back end (connectbox-manage) runs on **Node.js 22 LTS**, installed by the
playbook from the nodejs.org tarball into `/usr/local` (Node 24 and later have no
32-bit ARM build).  `/usr/bin/node`, `npm`, `npx` and `pm2` link there, because
PxUSBm calls `/usr/bin/pm2`.  On Raspberry Pi OS the build currently installs
Debian's own `nodejs` package instead (20.19 on Trixie; which Node to use there is
still open).

## 1. Prepare the device

### Armbian boards (NanoPi NEO, Orange Pi Zero 2, Radxa CM3)

1. Download an Armbian **Bullseye** image for your board (ConnectBox base images:
   https://github.com/ConnectBox/armbian-build/releases , otherwise
   https://www.armbian.com/download/) and write it to the microSD card, e.g. with
   balenaEtcher or Raspberry Pi Imager.
2. Boot the device on Ethernet, find its IP address (router, or `ping connectbox.local`
   on later runs) and log in as `root` with password `1234`.  Armbian asks you to
   set a new root password and create a user on first login; do that and change
   nothing else - the playbook expects a fresh system.

### Raspberry Pi

1. Write **Raspberry Pi OS Lite** (Trixie, 64-bit, for a CM4; Bullseye for older
   builds) with Raspberry Pi Imager.  In the Imager's settings: enable SSH, create a
   user (e.g. **`pi`**) with a password (current images have no default
   `pi`/`raspberry` account), and set your WiFi country.  Any WiFi network you
   enter in the Imager is removed by the build (its name and password are not left
   in the box or an image).
2. Plug in the WiFi hardware the box will use (on the CM4 carrier: the RTL8812AU
   USB adapter, which becomes the access point; the CM4's built-in WiFi is the
   client).  Boot the Pi on Ethernet and find its IP address.
3. From the build machine give your SSH key to that user **and to root** (the
   build logs in as root; root keeps password logins off):

   ```bash
   cd ~/connectbox/connectbox-tools/deployment
   ./setup_raspbian_host.sh <device_ip> <user>      # user defaults to pi
   ```

   It asks for the user's password once (and sudo may ask again) and ends with
   "Successful test".

## 2. SSH key

Ansible connects over SSH.  A key avoids password prompts, which can time out a
long run.  On the workstation:

```bash
ssh-keygen -t ed25519            # only if you have no key yet; accept the defaults
ssh-copy-id root@<device_ip>     # Armbian
ssh-copy-id pi@<device_ip>       # Raspberry Pi
```

Check that `ssh root@<device_ip>` (or `pi@`) now logs in without a password.

## 3. Get Ansible

Ansible runs on Linux or macOS (on Windows, use WSL or a Linux VM).  Install it
with this repo's pinned requirements, in a virtual environment:

```bash
git clone https://github.com/ConnectBox/connectbox-pi.git
cd connectbox-pi
python3 -m venv ~/.virtualenvs/connectbox-pi
. ~/.virtualenvs/connectbox-pi/bin/activate
pip install -r requirements.txt
```

Build from `master`; it is what the test unit runs.  To build an exact,
known version, check out its commit or tag after cloning.

## 4. Run the playbook

**Run it from the `ansible/` folder.**  `ansible/ansible.cfg` only applies there,
and it sets `force_handlers`, which the end-of-run steps (such as turning off
sshd) rely on.

```bash
cd ansible
ansible -i <device_ip>, all -m ping                 # expect "pong"
ansible-playbook -i <device_ip>, site.yml -e wireless_country_code=US
```

The comma after the IP address makes Ansible treat it as a one-host list.  For
repeat builds you can instead copy `inventory.example` to `inventory`, put the
device on one line with its options, and use `-i inventory`:

```
192.168.1.50 wireless_country_code=US connectbox_default_hostname=Connectbox
```

**Set `wireless_country_code`** to your two-letter country code (it decides the
legal WiFi channels and power; default `US`).

The run takes a long time (much longer on a NEO or Pi Zero).  It ends with a
`PLAY RECAP`; `failed=0` means success.  If a run fails part-way, fix the cause and
run it again - the playbook can be re-run.

If it stops at **"Download kiwix-tools"** with "checksum ... did not match", the
Kiwix mirror was too slow and the device got a short file (November 2026: about
10 KB/s for the 20 MB file).  The checksum itself comes from Kiwix's own `.md5`
file.  Run the build again later, or download the file on another machine
(`https://download.kiwix.org/release/kiwix-tools/kiwix-tools_linux-aarch64-3.8.2.tar.gz`,
`linux-armv6` on 32-bit boards), check it against the `.md5` and copy it to `/tmp`
on the device under the same name; the download step then finds it and goes on.
The build's reboot empties `/tmp` on Raspberry Pi OS, so copy it after that reboot.

**By default the playbook turns off sshd at the end** (production mode).  For a
unit you will keep working on, add `-e developer_mode=true` (insecure - not for
units going into the field).

## 5. Check the build

1. Join the WiFi network **"Connectbox - Free Media"** (or `<hostname> - Free Media`)
   and open any web page: the captive portal should appear, then the media menu.
2. Insert a USB stick with content (`content/<language code>/...`; see
   [mmiLoader-usb-structure.md](mmiLoader-usb-structure.md)).  The OLED shows
   progress; the menus fill in when indexing finishes.
3. If you kept SSH (`developer_mode=true`), check the services:

```bash
systemctl status PxUSBm kiwix-serve nginx
node --version          # v22.x
/usr/bin/pm2 status     # connectbox-manage ("index") online
```

   The Box ID (Configuration → *Cloud Server Connection*) should stay the same
   after a reboot.
4. On a box with the front panel, the amber LED is lit (solid, or blinking to show
   a low battery) only while the access point is really transmitting, so you can
   join it.  It is off while the WiFi is still starting or has failed.

To make more units, copy the finished microSD card - there is no need to run
the playbook again for each one (see `do_image_preparation` below for making a
distributable image).

## Raspberry Pi OS Trixie (CM4)

Build Raspberry Pi OS Trixie targets with **`make_cb-rpi.py`** from connectbox-tools,
not with the system Ansible: Raspberry Pi OS Bookworm's ansible-core 2.14 cannot run
the playbook's downloads (`get_url`) on a target with Python 3.12 or later, so the
build stops at the first download.  `make_cb-rpi.py` asks the same questions as
`make_cb.py` but runs ansible-core 2.17.14 from its own virtual environment.

```bash
cd ~/connectbox/connectbox-tools/deployment
python3 make_cb-rpi.py --setup      # once per build machine (needs internet)
python3 make_cb-rpi.py              # answer Y to update, branch master
```

It refuses a target that is not a Raspberry Pi; NanoPi NEO builds keep using
`make_cb.py`.  The playbook reboots the device once during the build (new interface
names and `config.txt`), also when the build runs unattended.

What the build does differently on Raspberry Pi OS Trixie:

- `net.ifnames=0` in `cmdline.txt` (names `eth0`, `wlan0`, `wlan1`) and a
  `# BEGIN/END CONNECTBOX` block in `/boot/firmware/config.txt`: on a CM4
  `dtparam=i2c_vc=on` (front panel on I2C bus 10), `dtparam=i2c_arm=off` (the left
  button is on GPIO3), `dtparam=ant2`, and USB on the DWC2 controller
  (`otg_mode=0`, `dtoverlay=dwc2,dr_mode=host`: on the other controller the
  RTL8812AU kept dropping off USB).
  On a CM5 (November 2026, CM5 Lite on the same carrier) the `[cm5]` part has
  `dtparam=i2c_csi_dsi0=on` (the front panel on GPIO38/39, which is I2C bus 10),
  `dtparam=i2c_arm=off`, `dtparam=ant2` and `gpio=22=ip,pu` (the ATtiny's reset
  line: without the pull-up the ATtiny does not answer); USB is already on DWC2
  through the OS's own `[cm5]` line.  The playbook treats a CM5 like a CM4 otherwise.
- NetworkManager, netplan and cloud-init's network settings are replaced by
  ifupdown, isc-dhcp-client and dhcpcd, as on Armbian; systemd-networkd stays off.
- The RTL8812AU access point uses the `8812au` driver (DKMS, morrownr
  8812au-20210820); the kernel's `rtw88_8812au` is blacklisted.
- hostapd is not started by systemd at boot: the access point's `ifup` runs
  wifi-configurator, which scans for free channels, writes `hostapd.conf` and starts
  hostapd once; PxUSBm restarts it if the radio is not really transmitting.
- The firewall uses the nftables-based `iptables` (this kernel has no legacy
  `ip_tables`); Armbian boards keep legacy iptables.
- The front panel uses `rpi-lgpio` instead of RPi.GPIO, and the multi-battery page
  is on when the ATtiny battery controller answers on I2C.
- Before the hat service starts, `i2c_bus_recover.sh` frees the front panel's I2C
  bus if a device is holding SDA low (seen after a restart and after a reboot).
- **HDMI screen** (role `hdmi-screen`, Raspberry Pi only): a screen on the HDMI port
  shows a playlist set in Configuration → Advanced → HDMI Screen, a file chosen with
  "Play on HDMI" on a media page (visitors only if the admin allows it), or a splash
  with the box name and Wi-Fi name.  Needs `mpv` (installed by the role) and no
  desktop.
- Python packages are installed with `--break-system-packages` where the OS marks
  Python as externally managed.

## Options

Add to the inventory line, or as `-e name=value` on the command line.  `true`/`false`
work in either form (the playbook reads them with `| bool`; before November 2026 an
explicit `-e developer_mode=false` or `-e do_image_preparation=False` was taken as
true).

| Option | Default | What it does |
|--------|---------|--------------|
| `wireless_country_code` | `US` | WiFi regulatory country (two letters). |
| `connectbox_default_hostname` | `Connectbox` | Host name shown in the browser's address bar; also used in the default SSID. |
| `ssid` | `<hostname> - Free Media` | WiFi network name (can also be changed in the admin pages). |
| `developer_mode` | `false` | `true` keeps sshd running and lets dnsmasq answer DNS on every interface. Insecure: test units only. |
| `enhanced_interface` | `true` | The current media interface (menus, languages, ZIM files). `false` installs the old icon-only interface and the sample content. |
| `do_image_preparation` | `false` | Prepares the card for distribution as a release image and halts the device at the end. |

## Administration

After the build, see [administration.md](administration.md) (admin pages at
`http://connectbox/admin`, default login `admin` / `connectbox` - change it).
For developing the playbooks or the software, see [development.md](development.md).
