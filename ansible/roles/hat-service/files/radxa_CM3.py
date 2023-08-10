# -*- coding: utf-8 -*-
# Copyright (c) 2018 Richard Hull & Contributors
# See LICENSE.md for details.

# copied and modified by JRA - 073123

"""
Alternative pin mappings for Radxa Zero
(see https://wiki.radxa.com/Zero/hardware/gpio)

Usage:

.. code:: python
   import radxa.CM3
   from RPi import GPIO

   GPIO.setmode(radxa.CM3.BOARD) or GPIO.setmode(radxa.CM3.BCM)
"""

# Formula for converting from GPIOx_yz go IO number:
#  IO = 32 * x  + 8 * y  +  z
#   where y = 0,1,2,3 for A,B,C,D

# Radxa CM3 physical board pin to GPIO pin
BOARD = {
    3:      14,     # GPIO0_B6  | 
    5:      13,     # GPIO0_B5  | 
    7:      125,    # GPIO3_D5  | 
    8:      25,     # GPIO0_D1  | 
    10:     24,     # GPIO0_D0  | 
    11:     23,     # GPIO0_C7  | 
    12:     119,    # GPIO3_C7  | 
    13:     15,     # GPIO0_B7  | 
    15:     19,     # GPIO0_C3  | 
    16:     124,    # GPIO3_D4  | 
    18:     123,    # GPIO3_D3  | 
    19:     138,    # GPIO4_B2  | 
    21:     136,    # GPIO4_B0  |
    22:     118,    # GPIO3_C6  |
    23:     139,    # GPIO4_B3  | 
    24:     134,    # GPIO4_A6  |
    27:     140,    # GPIO4_B4  |
    28:     141,    # GPIO4_B5  |
    29:     137,    # GPIO4_B1  |
    31:     21,     # GPIO0_C5  |
    32:     144,    # GPIO4_C0  |
    33:     22,     # GPIO0_C6  |
    35:     120,    # GPIO3_D0  |
    36:     135,    # GPIO4_A7  |
    37:     18,     # GPIO0_C2  | 
    38:     122,    # GPIO3_D2  |
    40:     121,    # GPIO3_D1  |
}

# No reason for BCM mapping, keeping it for compatibility
BCM = BOARD
