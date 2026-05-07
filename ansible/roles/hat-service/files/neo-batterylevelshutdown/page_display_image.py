# -*- coding: utf-8 -*-

"""
===========================================
  page_display_image.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  Clayton Bradley - Feb 2019
===========================================
"""

import os.path
import logging
from PIL import Image, ImageFont, ImageDraw
from .HAT_Utilities import get_device


try:
    import psutil
except ImportError:
    print("The psutil library was not found. "
          "Run 'sudo -H pip install psutil' to install it.")
    sys.exit()

class PageDisplayImage:
    def __init__(self, device, imageName='error.png', devicename=''):
        self.device = device
        self.imageName = imageName
        self.devicename = devicename

    def draw_page(self):
        # display a specified impage
        logging.debug("Showing %s", self.imageName)
        dir_path = os.path.dirname(os.path.abspath(__file__))
        img_path = dir_path + '/assets/' + self.imageName
        if not os.path.isfile(img_path):
            img_path = dir_path + '/assets/error.png'

        base = Image.open(img_path).convert('RGBA')
        fff = Image.new(base.mode, base.size, (255,) * 4)
        img = Image.composite(base, fff, base)
        # make a blank image for the text, initialized as transparent
        txt = Image.new('RGBA', base.size, (255, 255, 255, 0))

        # get a font
        font_path = dir_path + '/assets/HaxM-12.pil'
        font14 = ImageFont.load(font_path)
        # get a drawing context
        d = ImageDraw.Draw(txt)

        #device that is offending
        if self.devicename != "":
            if self.imageName.startswith('wait'):
                d.text((5, 15), "{:<}".format(self.devicename), font=font14, fill="black")
            elif self.imageName== 'error.png':
                d.text((5, 20), "{:<}".format(self.devicename), font=font14, fill="black")
            else:
                d.text((33, 20), "{:<}".format(self.devicename), font=font14, fill="black")
        out = Image.alpha_composite(img, txt)
        self.device.display(out.convert(self.device.mode))
        self.device.show()



if __name__ == "__main__":
    try:
        PageDisplayImage(get_device()).draw_page()
    except KeyboardInterrupt:
        pass
