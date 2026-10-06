# Making a ConnectBox release image

A *release image* is a `.img.xz` file that anyone can burn to a microSD card to get
a ready-made ConnectBox (see the
[releases page](https://github.com/ConnectBox/connectbox-pi/releases)).  It is made
by building one ConnectBox with the playbook in image-preparation mode, then
copying that card into a shrunken image file.

To build a single ConnectBox for your own use, follow
[deployment.md](deployment.md) instead - this guide adds the image steps on top of it.

**Revisions:** 2020-04 to 2021-03, JRA (from Edwin Steele's original notes, see
History).  2026-10-06: rewritten for the current tools and the Raspberry Pi build
machine; the Mac/Vagrant procedure was dropped (its Ubuntu 16.04 VM is no longer
maintained).

## Overview

1. **Build machine** (once): a Linux computer with Ansible, the `connectbox-tools`
   scripts and a USB microSD reader.
2. **Target device**: a fresh base OS on a microSD card, with key-based SSH login
   as `root`.
3. **Build** with `do_image_preparation=true`: the playbook installs ConnectBox,
   strips build tools, removes the SSH key and shuts the device down.
4. **Shrink** the card into an `.img` file and compress it with `xz`.
5. **Test** the image on a fresh card.
6. **Publish** it as a GitHub release.

Allow about an hour for the build on a NanoPi NEO and 30-60 minutes for shrinking
and compressing.

## 1. Build machine

The current build machine is a **Raspberry Pi 4 running Raspberry Pi OS (Bookworm)**
with a desktop; any Debian/Ubuntu machine works the same way.  (macOS and Windows
cannot shrink ext4 cards directly; use a Pi or a Linux PC.)

```bash
sudo apt install git ansible xz-utils parted e2fsprogs \
                 python3-click python3-github python3-requests
mkdir -p ~/connectbox && cd ~/connectbox
git clone https://github.com/ConnectBox/connectbox-tools.git
git clone https://github.com/ConnectBox/connectbox-pi.git
mkdir -p Images
ssh-keygen -t ed25519            # if you have no key yet; accept the defaults
```

Bookworm's `ansible` package (ansible-core 2.14) builds the current playbook.  On
an older system, install Ansible from `connectbox-pi/requirements.txt` in a
virtual environment as described in [deployment.md](deployment.md#3-get-ansible).

You also need a **USB** microSD card reader.  An SD-card adaptor in a laptop slot
does not work for the shrink step.

Before each build, update both repos (`git -C ~/connectbox/connectbox-pi pull`,
same for `connectbox-tools`).

## 2. Prepare the target device

1. Install and boot the base OS for your board as in
   [deployment.md, step 1](deployment.md#1-prepare-the-device) (Armbian Bullseye
   for the NanoPi NEO, Raspberry Pi OS Lite for a Pi).  Use an 8 GB card: the image
   is copied from the whole card, so a bigger one only makes shrinking slower.
2. Plug in the **USB WiFi adapter** the box will use; the build fails without
   the WiFi hardware it expects.
3. Release builds log in as **root** with your SSH key:

   - **Armbian:** `ssh-copy-id root@<device_ip>`
   - **Raspberry Pi OS:** copy the key to `pi`, then give root the same key
     (root may log in with a key but not a password, which is the default):

     ```bash
     ssh-copy-id pi@<device_ip>
     ssh pi@<device_ip> 'sudo mkdir -p /root/.ssh && sudo cp ~/.ssh/authorized_keys /root/.ssh/'
     ```

   Check that `ssh root@<device_ip>` logs in without a password.  If the device's
   IP was used by another box before, remove the old entry first:
   `ssh-keygen -R <device_ip>`.

## 3. Build

Run the playbook from the **`ansible/` folder** (so `ansible/ansible.cfg` applies -
see [deployment.md](deployment.md#4-run-the-playbook)):

```bash
cd ~/connectbox/connectbox-pi/ansible
ansible-playbook -i <device_ip>, site.yml \
    -e ansible_user=root \
    -e do_image_preparation=true \
    -e deploy_sample_content=false \
    -e connectbox_version=v$(date +%Y%m%d) \
    -e wireless_country_code=US
```

`connectbox_version` is the version shown in the admin pages; use the release tag
you will publish.  The run ends with `PLAY RECAP ... failed=0` and the device
**shuts itself down**.  With `do_image_preparation=true` the playbook also:

- removes compilers, development libraries and admin tools that a field unit does
  not need (smaller image);
- resets the WiFi regulatory domain;
- deletes root's `authorized_keys`, so your key is not in the image;
- deletes the admin session key (`/usr/local/connectbox/admin_session.key`), so
  every box made from the image creates its own on first boot.

As on every normal build, sshd is turned off at the end; never build a release
with `developer_mode=true`.

**Alternative:** from `~/connectbox/connectbox-tools/deployment`, run
`python3 make_cb.py`.  It asks whether to fetch a fresh copy of connectbox-pi
(branch or tag, default `master`), the release tag, the device IP and any extra build options (typed as on the
command line, e.g. `-e wireless_country_code=AU`), then runs the same playbook from `ansible/` as
root with `do_image_preparation=True`.  (Fixed in connectbox-tools `5893887`;
earlier versions ran it from the wrong folder and mangled the options.)

## 4. Shrink and compress

1. Wait for the device to power off, take out the card and put it in the **USB**
   reader on the build machine.
2. Find the card and unmount anything the desktop mounted from it:

   ```bash
   lsblk                                   # the card is e.g. sda (Pi) or sdb (PC)
   sudo umount /dev/sda1 /dev/sda2 2>/dev/null
   ```

   **Check the device name carefully** - the next command rewrites that disk.
3. Shrink the file system(s) and copy out the image:

   ```bash
   cd ~/connectbox
   sudo connectbox-tools/deployment/shrink-image.sh /dev/sda \
       Images/connectbox-neo-v$(date +%Y%m%d).img
   ```

   The script refuses non-removable disks and mounted cards, checks the file
   systems, shrinks them to their minimum size and copies just that part of the
   card (10-20 minutes).  It handles cards with 1, 2 or 3 partitions.
4. Compress it (keeps the `.img`):

   ```bash
   xz -k -T0 Images/connectbox-neo-v$(date +%Y%m%d).img
   ```

Name images by board and date, e.g. `connectbox-neo-v20261006.img.xz`.

## 5. Test the image

Burn the `.img.xz` to a **different** card with balenaEtcher or Raspberry Pi
Imager (both read `.xz` directly), boot a device from it and check it as in
[deployment.md, step 5](deployment.md#5-check-the-build): WiFi network and captive
portal, a USB stick with content, the language menus and a ZIM file.  On first
boot the box grows its file system to fill the card.

## 6. Publish

**By hand (usual):** on GitHub open
[connectbox-pi releases](https://github.com/ConnectBox/connectbox-pi/releases) ->
*Draft a new release*, create the tag (e.g. `v20261006`) on `master`, attach the
`.img.xz`, and write release notes: board, base OS image used, and the changes
since the last release (from `CHANGELOG.md` / `Master_Changes_Log.md`).  Mark it
*pre-release* until it has been tested in the field, then publish.

**Automated:** `connectbox-tools/deployment/prepare_release.py` tags every
ConnectBox repo listed in its `CONNECTBOX_REPOS`, creates a draft pre-release,
builds the device, shrinks and compresses the card and uploads the image.  It
needs a GitHub personal access token with write access to all those repos
(`CONNECTBOX_GITHUB_TOKEN=<token> python3 prepare_release.py` from
`connectbox-tools/deployment`; `--use-existing-tag --tag=<tag>` resumes after a
failure).  After the build it waits for the card in the USB reader, **asks you to
confirm the disk** (check with `lsblk`), shrinks it with `shrink-image.sh`, and
leaves the `.img.xz` in `deployment/Images/` before uploading it.  Write the
release notes on GitHub afterwards and publish the draft when tested.  (Since
connectbox-tools `5893887` it runs on the build Pi; before that it only worked in
the old Vagrant VM.)

## History

Edwin Steele wrote most of the original ConnectBox code and image tooling and was
for years the only image builder; JRA turned his notes into the 2020-2021 version
of this guide (Mac/VirtualBox/Vagrant and Raspberry Pi build environments, Armbian
`base-image-190417`, Raspbian Buster).  Both are in this file's git history.
