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
| Raspberry Pi models and Compute Module 4 | Raspberry Pi OS **Lite** (Bullseye) | `pi` |

The playbook knows Buster and Bullseye (see the comment at the top of
`site.yml`).  The current test unit is a NanoPi NEO on Armbian Bullseye
(kernel 5.15); the other boards have not been rebuilt recently, and newer
releases (Bookworm) are untested.

Use a microSD card of at least 8 GB.  The device needs a wired (Ethernet) or
second WiFi connection to the internet during the build, because its main WiFi
adapter becomes the access point.

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

1. Write **Raspberry Pi OS Lite** (Bullseye) with Raspberry Pi Imager.  In the
   Imager's settings: enable SSH, create the user **`pi`** with a password (newer
   images no longer have a default `pi`/`raspberry` account), and set your WiFi
   country.  If you choose another user name, add `ansible_user=<name>` to the
   Ansible command or inventory.
2. Boot the Pi on Ethernet and find its IP address.

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
```

To make more units, copy the finished microSD card - there is no need to run
the playbook again for each one (see `do_image_preparation` below for making a
distributable image).

## Options

Add to the inventory line, or as `-e name=value` on the command line.

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
