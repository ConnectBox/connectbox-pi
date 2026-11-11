#!/usr/bin/env python3
"""Make the HDMI idle ("splash") screen for a Raspberry Pi ConnectBox.

The HDMI player (hdmi_player.py) shows this picture whenever nothing is
playing: no playlist, or between a visitor's item and the playlist.  Kirk's
design (2026-11-11): black background, red text, the default ConnectBox logo
at the top left, the box name, and the Wi-Fi name so people know what to join.

The logo's box is dark blue on a transparent background, which hardly shows
on black, so it is drawn on a white rounded tile.

usage: hdmi_splash.py [--out FILE] [--width W --height H] [--name NAME] [--ssid SSID]
Without --name/--ssid they are read from brand.j2 ("Brand") and hostapd.conf
("ssid=").  Needs Pillow (the hat service's virtualenv has it).
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

BRAND_FILE = "/usr/local/connectbox/brand.j2"
HOSTAPD_CONF = "/etc/hostapd/hostapd.conf"
LOGO_FILES = ["/var/www/enhanced/content/www/assets/imgs/logo.png",
              "/usr/local/connectbox/battery_tool_venv/lib/python3.13/site-packages/"
              "neo_batterylevelshutdown/assets/connectbox_logo.png"]
FONT_FILES = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
RED = (230, 30, 30)
DEFAULT_OUT = "/usr/local/connectbox/hdmi/splash.png"


def read_box_name():
    """Return the box name ("Brand" in brand.j2), or "ConnectBox" if it cannot be read."""
    try:
        with open(BRAND_FILE, encoding="utf-8") as f:
            name = str(json.load(f).get("Brand", "")).strip()
        return name or "ConnectBox"
    except (OSError, ValueError):
        return "ConnectBox"


def read_ssid():
    """Return the access point's Wi-Fi name from hostapd.conf, or "" if not found."""
    try:
        with open(HOSTAPD_CONF, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("ssid="):
                    return line[5:].strip()
    except OSError:
        pass
    return ""


def font(size, bold=True):
    """Load DejaVu Sans (bold or regular) at the given pixel size, or Pillow's default."""
    for path in (FONT_FILES if bold else FONT_FILES[::-1]):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def fit_font(draw, text, max_width, start, minimum=20, bold=True):
    """Largest font (from start down to minimum) at which text fits in max_width."""
    size = start
    while size > minimum:
        f = font(size, bold)
        if draw.textlength(text, font=f) <= max_width:
            return f
        size -= 4
    return font(minimum, bold)


def make_splash(width, height, name, ssid, out):
    """Draw the splash picture and write it atomically to out (PNG)."""
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = height // 18

    # Logo at the top left, on a white rounded tile so the dark blue box shows
    logo_path = next((p for p in LOGO_FILES if os.path.exists(p)), None)
    tile = height // 4
    if logo_path:
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((tile - tile // 8, tile - tile // 8))
        draw.rounded_rectangle([margin, margin, margin + tile, margin + tile],
                               radius=tile // 8, fill=(255, 255, 255))
        img.paste(logo, (margin + (tile - logo.width) // 2, margin + (tile - logo.height) // 2), logo)

    # Box name, big and red, centred in the space below the logo
    usable = width - 2 * margin
    name_font = fit_font(draw, name, usable, start=height // 6)
    nb = draw.textbbox((0, 0), name, font=name_font)
    name_y = height // 2 - (nb[3] - nb[1])
    draw.text(((width - (nb[2] - nb[0])) // 2 - nb[0], name_y - nb[1]), name, font=name_font, fill=RED)

    # The Wi-Fi to join, under the name
    if ssid:
        lines = [("Join the Wi-Fi:", False), (ssid, True)]
        y = name_y + (nb[3] - nb[1]) + height // 12
        for text, bold in lines:
            f = fit_font(draw, text, usable, start=height // 16, bold=bold)
            b = draw.textbbox((0, 0), text, font=f)
            draw.text(((width - (b[2] - b[0])) // 2 - b[0], y - b[1]), text, font=f, fill=RED)
            y += (b[3] - b[1]) + height // 40

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    tmp = out + ".tmp.png"
    img.save(tmp)
    os.replace(tmp, out)            # never leave a half-written picture for the player


def main():
    """Parse the arguments and write the splash picture."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--name")
    ap.add_argument("--ssid")
    a = ap.parse_args()
    make_splash(a.width, a.height, a.name if a.name is not None else read_box_name(),
                a.ssid if a.ssid is not None else read_ssid(), a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
