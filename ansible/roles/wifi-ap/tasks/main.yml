# -*- coding: utf-8 -*-


"""
===========================================
  branding.py
  https://github.com/ConnectBox/NEO_BatteryLevelShutdown
  License: MIT
  Version 1.0
  DorJamJr - July 2021
===========================================
"""

import neo_batterylevelshutdown.globals as globals


# Maximum 10 characters
global  brand_name
# png file of logo 
global  logo_image


class Brand:

    def __init__(self):
        with open('/usr/local/connectbox/brand_name.txt', encoding='utf-8') as f:
        self.brand_name = f.read()
        f.close()
        with open('/usr/local/connectbox/logo_image.txt') as f:
        self.logo_image = f.read()
        f.close()

    def name(self):    
        return "%s" % self.brand_name

    def splash(self):                    #For screen display
        a = Brand.name(self)
        position_x = 7
        position_y = 0
        font = 26
        return (a, font, position_x, position_y)
    
    def image(self):                     #Boot up Logo on screen
        return "%s" % self.logo_image


