# -*- coding: utf-8 -*-

# hats.py
# Modified 10/17/19 by JRA to add new class q4y2019HAT (HAT 5.0.9 board with OLED but no battery) ie, the NoBatt version
#  11/30/21 JRA - Q4Y2019 Hat class removed - no battery instance handled in battery pages

# 08/05/23  JRA - Configured for RM3 module
#  Note that GPIO setups are done in the init function of each class... specifically, the init
#   of the called class is done first, then (by super __init()__) the init of that class's parent,
#   then the init of the grandparent class.

from contextlib import contextmanager
import logging
import os
import os.path
import io
import sys
import time
import subprocess
import smbus2

from axp209 import AXP209, AXP209_ADDRESS
import neo_batterylevelshutdown.globals as globals
logging.info("...hats.py globals.device_type = %s.", globals.device_type)

comsFileName = "/tmp/creating_menus.txt"
var_Indexing = False


# globals was initiated by cli, so no need to re initialize here
# We do the imports here... but function calls inside of the code
if globals.device_type == "RM3":
    import radxa.CM3    # not required
    import OPi.GPIO as GPIO  # pylint: disable=import-error
elif globals.device_type == "NEO":
    import RPi.GPIO as GPIO  # pylint: disable=import-error
elif globals.device_type == "OZ2":
    import RPi.GPIO as GPIO  # pylint: disable=import-error
    import orangepi.zero2
else:
    import RPi.GPIO as GPIO  # pylint: disable=import-error



from .buttons import BUTTONS
import neo_batterylevelshutdown.usb as usb
import neo_batterylevelshutdown.multiBat_Utilities as mb_utilities



@contextmanager
def min_execution_time(min_time_secs):
    """
    Runs the logic within the context handler for at least min_time_secs

    This function will sleep in order to pad out the execution time if the
    logic within the context handler finishes early
    """
    start_time = time.monotonic()
    yield
    duration = time.monotonic() - start_time
    # If the function has run over the min execution time, don't sleep
    period = max(0, min_time_secs - duration)
    time.sleep(period)

def setup_GPIO():
    GPIO.cleanup()              # remove associations
    GPIO.setwarnings(False)

    if globals.device_type == "RM3":
        GPIO.setmode(radxa.CM3.BOARD)  # not required... already set in cli.py
    elif globals.device_type == "NEO":
        GPIO.setmode(GPIO.BOARD)
    elif globals.device_type == "OZ2":
        GPIO.setmode(orangepi.zero2.BOARD)
    else:
       GPIO.setmode(GPIO.BCM)



class BasePhysicalHAT:

    LED_CYCLE_TIME_SECS = 4

    # pylint: disable=unused-argument
    # This is a standard interface - it's ok not to use
    def __init__(self, displayClass):

#  cli.py wants hats.py to assign GPIO stuff... So we will do that starting here
# imports are done in header... GPIO functions are done here
            # All HATs should turn on their LED on startup. Doing it in the base
            #  class constructor allows us the main loop to focus on transitions
            #  and not worry about initial state (and thus be simpler)
        self.solidLED()

#    @classmethod
# Called when AXP209 signals NEO that power is about to go down
    def shutdownDevice(self):
        # Turn off the LED, as some people associate that with wifi being
        #  active (the HAT can stay powered after shutdown under some
        #  circumstances)
        GPIO.output(self.PIN_LED, GPIO.HIGH)
        self.display.showPoweringOff()
        logging.info("Exiting for Shutdown")
        os.system("/usr/local/bin/poweroff/poweroff")
        time.sleep(5)
        # Stick here to leave the showPoweringOff() display on to the end
        while True:
            pass

    def shutdownDeviceCallback(self, channel):
        logging.info("Triggering device shutdown based on edge detection "
                      "of GPIO %s.", channel)
        print("... IRQ Triggered")
        # do some verification that the signal is still low after 100 ms
        time.sleep(0.1)
        # if interrupt line is high, this was a false trigger... just return
        if GPIO.input(self.PIN_AXP_INTERRUPT_LINE):
            print("...  for more than 0.1 sec....   DEBUG... returning")
            return
        self.shutdownDevice()
        return

    def handleOtgSelect(self, channel):
        logging.debug("OTG edge detected ")
        # OTG ONLY IMPLEMENTED FOR NEO HAT 7.0 ONLY! OTG can be used on a Pi4, PiZero or CM4
        # but also needs to have the correct drivers installed (dtoverlay=dwc2,dr_mode=(host, peripheral,otg)
        # and needs the proper module loaded either on the dtoverlay line, etc. but does not call this
        # interrupt handler.

        # On the Neo we have a signal to detect changes in OTG_ID signal.
        # disable interrupt for a bit to find if the level on channel is HIGH or LOW
        #  and based on that, choose whether to enable or disable OTG service
        # Note that this is a specific case of OTG sense being on PA0...
        #  If another implementation is made for NEO, this will need updating.
        #
        #  FUTURE: make this a general case handler for ANY channel on the NEO
        #
        # Register calculation from Allwinner_H3_Datasheet_v1.1.pdf page 316 ff
        #   Base address = 0x01c20800 ... PA0 is in bits 2:0 of offset 0x00
        # globals.otg =0 for off;  high to enable OTG and "none" for enabled inverted OTG
        # and 'both' for always otg regardless of state
        if globals.otg=='0' or globals.otg == 0:
            retval = os.popen("grep "+globals.g_device).read()
            if retval != "":
                retval = os.popen('modprobe -r '+globals.g_device)     #make sure there is no g_device loaded by default.
            return
        if (globals.device_type == "NEO"):
            cmd = "devmem2 0x01c20800"      #set up to read the config value for PA0
            retval = os.popen(cmd).read()   # the stdout of the command
            init_val = int(retval.split(":")[1],16)     # The initial (integer) value of the register
            write_val = init_val & 0x77777770           # Mask to set the PA0 pin to INPUT
            cmd1 = cmd + " w " + hex(write_val)          # Form the command
            retval = os.popen(cmd1).read()                     # Write the register

            if globals.otg == "none":
                otg_xor = 1
            else:
                otg_xor = 0

            # we are now in input mode for the pin...
            if globals.otg == "both":
                otg_mode = True
                logging.debug("The OTG pin state dosn't matter were enabled in any case")
            else:
                if (globals.otg ^ otg_xor) == 0:
                    logging.debug("The OTG pin is LOW, so leaving OTG mode")
                    otg_mode = False
                else:
                    logging.debug("The OTG pin is HIGH, so entering OTG mode")
                    otg_mode = True

            # we are through with using the OTG pin as an input... put the register back as it was
            if (globals.device_type == "NEO"):
                cmd2 = cmd + " w " + hex(init_val)      #form command to write the orginal value back
                retval = os.popen(cmd2).read()          # the stdout of the command

            # Now we have determined the OTG request, so do the requested work
            if otg_mode == True:
                logging.debug("in OTG set")
                retval = os.popen("grep "+globals.g_device+" /proc/modules").read()
                if retval == "":
                    # module was not loaded we couldn't find it at least.  So lets get to loading
                    retval = os.popen("modprobe "+globals.g_device+" "+globals.enable_mass_storage).read()
                    if retval.find("FATAL") <= 0:
                        logging.info("failed to load the driver "+globals.g_device+" "+globals.enable_mass_storage)
                        return
                    else:
                        retval = os.popen("systemctl daemon-reload").read()
                        if globals.g_device == 'g_serial':
                            retval = os.popen("systemctl restart serial-getty@ttyGS0.service").read()
                            if retval != "":
                                logging.info("load of g_serial serial-getty@ttyGS0.service failed")
                    #######################################################################
                    #What other service needs to be started or checked due to loading a module
                    #We need to figure that out?
                    #######################################################################
                    return
                else:
                    # module was already loaded so wnat do we need to do?
                    if globals.g_device == 'g_serial':
                        retval = os.popen("systemctl status service-getty@ttyGS0.service").read()
                        if retval.find("active (running)") <= 0:
                            retval = os.popen("systemctl restart serial-getty@ttyGS0.service").read()
                            if retval != "":
                                logging.info("load of g_serial serial-getty@ttyGS0.service failed")
                    #######################################################################
                    #What other service needs to be started or checked due to loading a module
                    #We need to figure that out?
                    #######################################################################
                    return
            else:
                logging.debug("not OTG set")
                retval = os.popen("grep "+globals.g_device+" /proc/modules").read()
                if retval.find("filename"):
                    retval = os.popen("modprobe -r "+globals.g_device).read()
                    if retval.find("FATAL"):
                        logging.debug("modprobe operation to remove "+globals.g_device+" failed!")
        return
    # End of the OTG interrupt handler.......


    def check_AP_up(self):
        f = open("/usr/local/connectbox/wificonf.txt", "r")
        wifi = f.read()
        f.close()
        apwifi = wifi.partition("AccessPointIF=")[2].split("\n")[0]
        try:
            AP = int(apwifi.split("wlan")[1])
        except:
            return (0)
        wlanx = "wlan"+str(AP)
        cmd = "iwconfig"
        rv = subprocess.check_output(cmd, stderr=None, shell=False)
        rvs = rv.decode("utf-8").split(wlanx)

        if (len(rvs) >= 2):       # rvs is an array split on wlanx
            wlanx_flags = rvs[1].split("Mode:Master")
            if (len(wlanx_flags)) > 1:
    # we are up
                return(1)
    # we are not up... either iwconfig has no wlanAP or the wlanAP Mode: is wrong
        return (0)



    def blinkLED(self, times, flashDelay=0.3):
        if self.check_AP_up() == 1:
            for _ in range(0, times):
                GPIO.output(self.PIN_LED, GPIO.HIGH)
                time.sleep(flashDelay)
                GPIO.output(self.PIN_LED, GPIO.LOW)
                time.sleep(flashDelay)
        else:
             GPIO.output(self.PIN_LED, GPIO.HIGH)


    def solidLED(self):
        if self.check_AP_up() == 1:
            GPIO.output(self.PIN_LED, GPIO.LOW)
        else:
            GPIO.output(self.PIN_LED, GPIO.HIGH)


class DummyHAT(BasePhysicalHAT):

    def __init__(self, displayClass):
        setup_GPIO()
        super().__init__(displayClass)
        pass

    # pylint: disable=no-self-use
    # This is a standard interface - it's ok not to use self for a dummy impl
    def mainLoop(self):
        logging.info("There is no HAT, so there's nothing to do using DummyHat")
        logging.info("globals.device_type = "+globals.device_type)
        while True:
            if os.path.isfile(comsFileName):
                 f = open(comsFileName, 'r', encoding='utf-8')
                 globals.a = f.read()
                 f.close()
                 self.display.showWaitPage(globals.a)
                 var_Indexing = True
            elif var_Indexing:
                 self.display.showSuccessPage()
                 var_Indexing = False
            time.sleep(3)


class q1y2018HAT(BasePhysicalHAT):
    # The circuitry on the Q1Y2018 HAT had voltage comparators to determine
    # battery voltage. All later HATs use the AXP209 for finding voltages
    # This HAT was ONLY made for NEO


    def __init__(self, displayClass):

        # The circuitry on the HAT triggers a shutdown of the 5V converter
        #  once battery voltage goes below 3.0V. It gives an 8 second grace
        #  period before yanking the power, so if we have a falling edge on
        #  PIN_VOLT_3_0, then we're about to get the power yanked so attempt
        #  a graceful shutdown immediately.

        setup_GPIO()


        if globals.device_type == "NEO":
        # Pin numbers specified in BOARD format
            self.PIN_LED = 12       # PA6
            PIN_VOLT_3_0 =  8       # PG6
            PIN_VOLT_3_45 = 10      # PG7
            PIN_VOLT_3_71 = 16      # PG8
            PIN_VOLT_3_84 = 18      # PG9
            logging.info("Found Q1Y2018HAY for neo")
        else:
            # Pin numbers specified in BCM format
            self.PIN_LED = 6    # GPIO6
            PIN_VOLT_3_0 =  14      # PG6
            PIN_VOLT_3_45 = 15      # PG7
            PIN_VOLT_3_71 = 23      # PG8
            PIN_VOLT_3_84 = 24      # PG9
            logging.info("Found Q1Y2018HAY for Pi")


        if (globals.device_type == "NEO"):
            logging.info("Initializing Pins")
            GPIO.setup(self.PIN_LED, GPIO.OUT)
            GPIO.setup(self.PIN_VOLT_3_0, GPIO.IN)
            GPIO.setup(self.PIN_VOLT_3_45, GPIO.IN)
            GPIO.setup(self.PIN_VOLT_3_71, GPIO.IN)
            GPIO.setup(self.PIN_VOLT_3_84, GPIO.IN)

            # Run parent constructors before adding event detection
            #  as some callbacks require objects only initialised
            #  in parent constructors
            super().__init__(displayClass)
            GPIO.add_event_detect(self.PIN_VOLT_3_0, GPIO.FALLING, \
                              callback=self.shutdownDeviceCallback)
            # We cannot perform edge detection on PG7, PG8 or PG9 because there
            #  is no hardware hysteresis built into those level detectors, so when
            #  charging, the charger chip causes edge transitions (mostly rising
            #  but there are also some falling) at a rate of tens per second which
            #  means the software (and thus the board) is consuming lots of CPU
            #  and thus the charge rate is slower.

    def powerOffDisplay(self, channel):
        """Turn off the display"""
        logging.debug("Processing press on GPIO %s (poweroff).", channel)
        self.display.powerOffDisplay()
        # The display is already off... no need to set the power off time
        #  like we do in other callbacks


    def mainLoop(self):
        """
        monitors battery voltage and shuts down the device when levels are low
        """
        logging.info("Starting Monitoring")
        while True:
            with min_execution_time(min_time_secs=self.LED_CYCLE_TIME_SECS):

                if (time.time() > self.displayPowerOffTime) and (not var_Indexing):
                    self.display.powerOffDisplay()

                if os.path.isfile(comsFileName):
                    f = open(comsFileName, 'r', encoding='utf-8')
                    globals.a = f.read()
                    f.close()
                    self.display.showWaitPage(globals.a)
                    var_Indexing = True
                elif var_Indexing:
                    self.display.showSuccessPage()
                    var_Indexing = False

                if GPIO.input(self.PIN_VOLT_3_84):
                    logging.debug("Battery voltage > 3.84V i.e. > ~63%")
                    self.solidLED()
                    continue

                if GPIO.input(self.PIN_VOLT_3_71):
                    logging.debug("Battery voltage 3.71-3.84V i.e. ~33-63%")
                    self.blinkLED(times=1)
                    continue

                if GPIO.input(self.PIN_VOLT_3_45):
                    logging.debug("Battery voltage 3.45-3.71V i.e. ~3-33%")
                    # Voltage above 3.45V
                    self.blinkLED(times=2)
                    continue

                # If we're here, we can assume that PIN_VOLT_3_0 is high,
                #  otherwise we'd have triggered the falling edge detection
                #  on that pin, and we'd be in the process of shutting down
                #  courtesy of the callback.
                logging.info("Battery voltage < 3.45V i.e. < ~3%")
                self.blinkLED(times=3)


class Axp209HAT(BasePhysicalHAT):
    SHUTDOWN_WARNING_PERIOD_SECS = 60
    BATTERY_CHECK_FREQUENCY_SECS = 30
    MIN_BATTERY_THRESHOLD_PERC_SOLID = 63         # Parity with PIN_VOLT_3_84
    MIN_BATTERY_THRESHOLD_PERC_SINGLE_FLASH = 33  # Parity with PIN_VOLT_3_71
    MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH = 3   # Parity with PIN_VOLT_3_45
    BATTERY_WARNING_THRESHOLD_PERC = MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH
    BATTERY_WARNING_VOLTAGE = 3200                # CM4 warning voltage (mV)
#    BATTERY_SHUTDOWN_VOLTAGE = 3000               # ref only: AXP209 controlled shutdown voltage
#    BATTERY_SHUTDOWN_THRESHOLD_PERC = 1           # no longer used
    # possibly should be moved elsewhere


    def __init__(self, displayClass):

        try:
            bus = smbus2.SMBus(0)
            a = int(bus.read_byte_data(0x34, 0x36))
            print("AXP209 PEK register is: "+str(a))
            bus.write_byte_data(0x34, 0x36, 0x5F)
            print("Wrote PEK register to extend the timeout")
            a = int(bus.read_byte_data(0x34, 0x36))
            print("AXP209 PEK register is now : "+str(a))
#            bus.write_byte_data(0x34,0x32, 0xC3)			#Test power shutdown
#            print("shutdown the AXP209 we think")
            bus.close()
        except Exception as inst:
            print("Error reading/writing the PEK register of the AXP209 : ",type(inst), inst.args, inst)
            bus.close()


        logging.info("Starting AXP209HAT class __init__")
        self.axp = AXP209(globals.port)         # Pass the port number to get the right device
        self.display = displayClass(self)
        self.buttons = BUTTONS(self, self.display)
        # Blank the screen 3 seconds after showing the logo - that's long
        #  enough. While displayPowerOffTime is read and written from both
        #  callback threads and the main loop, there's no TOCTOU race
        #  condition because we're only ever setting an absolute value rather
        #  than incrementing i.e. we're not referencing the old value
        self.displayPowerOffTime = time.time() + 120
        # establish self.nextBatteryChecktime so that if
        #  we have a battery, perform a level check at our first chance
        #  (removed assumption that battery will not be added or removed in
        #   real use case)
        self.nextBatteryCheckTime = 0

        # Write the charge control 1 - limit/ current control register
        #  (Vtarget = 4.1 volts, end charging when below 10% of set charge current,
        #   charge current = 1200 mA )
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x33, 0xC9)    # V(trgt) = 4.2V (was 0x89... 4.1V)

        # Enable AC_IN current and voltage ADCs (also ADCs for Battery voltage, Battery current,
        #  and APS voltage.)
        #  note: APS monitors the IPSOUT voltage and shuts down system if < 2.9 volts.
        #        also, the Battery Temp Sense (TS) ADC is left enabled because disabling it
        #        results in a battery error warning LED (?)
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x82, 0xF3)

        # The Voff level exclusively controls shutdown due to low voltage.
        # The monitoring of voltage by this code for purposes of shutting down due to insufficient
        #  voltage has been DEPRICATED.
        # Change Voff voltage level (level of IPS_OUT below which causes AXP209 to shutdown)
        #  to 3.0V.
        self.axp.bus.write_byte_data(AXP209_ADDRESS,0x31,0x04)  # AXP209 trigger shutdown at Vbatt = 3.0V

        # shutdown delay time to 3 secs (they delay before axp209 yanks power
        #  when it determines a shutdown is required) (default is 2 sec)
        hexval = self.axp.bus.read_byte_data(AXP209_ADDRESS, 0x32)
        hexval = hexval | 0x03
        self.axp.bus.write_byte_data(AXP209_ADDRESS, 0x32, hexval)

        # If processor is CM4, call this to test if ATTiny is still talking
        if globals.device_type == "CM":
            mb_utilities.init_ATTiny_Talking()      # set ATTiny_Talking (global) to true
            mb_utilities.check_ATTiny()
            # Tell ATTiny to cycle through all batteries so AXP209 can read the voltages
            #  Function to reset battery registers moved to multiBat_Utilities.py
            mb_utilities.reset_ATTiny()

        logging.info("AXP209HAT __init__ complete")

        super().__init__(displayClass)


    def batteryLevelAbovePercent(self, level):
        # Battery guage of -1 means that the battery is not attached.
        # Given that amounts to infinite power because a charger is
        #  attached, or the device has found a mysterious alternative
        #  power source, let's say that the level is always above if
        #  we have a negative battery_gauge
        try:
            gaugelevel = self.axp.battery_gauge
        except OSError:
            logging.error("Unable to read from AXP")
            gaugelevel = -1

        return gaugelevel < 0 or \
            gaugelevel > level

    def batteryLevelAboveVoltage(self, level):      # level in mV
        try:
            voltagelevel = self.axp.battery_voltage  # returns mV
        except OSError:
            logging.error("Unable to read from AXP")
            voltagelevel = -1

        return voltagelevel < 1000 or \
            voltagelevel > level             # if <1000 we have no battery so return TRUE so we don't see the low bat warning


    def updateLEDState(self):
        if self.batteryLevelAbovePercent(
                self.MIN_BATTERY_THRESHOLD_PERC_SOLID):
            self.solidLED()
            return

        if self.batteryLevelAbovePercent(
                self.MIN_BATTERY_THRESHOLD_PERC_SINGLE_FLASH):
            self.blinkLED(times=1)
            return

        if self.batteryLevelAbovePercent(
                self.MIN_BATTERY_THRESHOLD_PERC_DOUBLE_FLASH):
            self.blinkLED(times=2)
            return

        # If we're here, we're below the double flash threshold and haven't
        #  yet been shutdown, so flash three times
        self.blinkLED(times=3)


    def mainLoop(self):
#        print("at entry axp209 hat main")
        var_Indexing = False
        while True:
            # The following ensures that the while loop only executes once every
            #  LED_CYCLE_TIME_SECS...
            with min_execution_time(min_time_secs=self.LED_CYCLE_TIME_SECS):
                # Perhaps power off the display
                if (time.time() > self.displayPowerOffTime) and (not var_Indexing):
                    self.display.powerOffDisplay()

                if os.path.isfile(comsFileName):
                    f = open(comsFileName, 'r', encoding='utf-8')
                    globals.a = f.read()
                    f.close()
                    self.display.showWaitPage(globals.a)
                    var_Indexing = True
                elif var_Indexing:
                    self.display.showSuccessPage()
                    var_Indexing = False

                # ATTiny battery handling only in CM4 HAT
                if globals.device_type == "CM":
                    try:
                        batteryVoltage = int(self.axp.battery_voltage)
                    except:
                        batteryVoltage = 3100   # AXP209 i2c fails at 3100 mV

                    # Call this once each loop to test if ATTiny is still talking
                    mb_utilities.check_ATTiny()
                    mb_utilities.v_update_array(batteryVoltage)

                # Here we add a call to update the current page so info is regularly updated
                self.display.redrawCurrentPage()
# DEPRICATED - Voltage monitoring for power down purposes is depricated.
#   We will let AXP209 (exclusively) handle the shutdown via the Voff facility (Reg 0x31 - set to 3.0V).
#     The AXP209 i2C communication becomes unreliable at IPS voltages below 3.1V.
#  Also note... We do NOT have a connection between the AXP209 IRQ line (pin 48) and the NEO so
#    we can't service the LEVEL2 IRQ (or any other AXP209 IRQ) anyway.

                if self.batteryLevelAboveVoltage(
                        self.BATTERY_WARNING_VOLTAGE):
                    # Battery now ok so hide the low battery warning, if we're currently showing it
                    self.display.hideLowBatteryWarning()
                else:
                    logging.info("BATTERY_WARNING_VOLTAGE reached")
                    # show (or keep showing) the low battery warning page
                    self.display.showLowBatteryWarning()
                    # Don't blank the display while we're in the
                    #  warning period so the low battery warning shows to the end
                    self.displayPowerOffTime = sys.maxsize
                    # we are near shutdown... force check every time around loop (5 sec)
                    self.BATTERY_CHECK_FREQUENCY_SECS = 4

                self.nextBatteryCheckTime = \
                    time.time() + self.BATTERY_CHECK_FREQUENCY_SECS

                # Give a rough idea of battery capacity based on the LEDs
                self.updateLEDState()

                # Check to see if anyone changed the brand.j2 file if so we need to reload
                globals.init()
#                print("at end of axp hat main()")


class q3y2018HAT(Axp209HAT):

    # HAT 4.6.7 - This is ONLY a NEO HAT

    def __init__(self, displayClass):

        setup_GPIO()

        if globals.device_type == "NEO":
            self.PIN_LED =        12    # PA6
            self.PIN_L_BUTTON =   8     # PA1
            self.PIN_R_BUTTON =   10    # PG7
    #        self.PIN_AXP_INTERRUPT_LINE = 16
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q3y2018HAT for neo")
        else:
            self.PIN_LED = 6    # GPIO6
            self.PIN_L_BUTTON =   14            #  PA1
            self.PIN_R_BUTTON =   15            #  PG7
    #        self.PIN_AXP_INTERRUPT_LINE = 23
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q3y2018HAT for Pi")

        GPIO.setup(self.PIN_LED, GPIO.OUT)
        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        # Run parent constructors before adding event detection
        #  as some callbacks require objects only initialised
        #  in parent constructors


        super().__init__(displayClass)
        GPIO.add_event_detect(self.PIN_L_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        GPIO.add_event_detect(self.PIN_R_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)

    def powerOffDisplay(self, channel):
        """Turn off the display"""
        logging.debug("Processing press on GPIO %s (poweroff).", channel)
        self.display.powerOffDisplay()
        # The display is already off... no need to set the power off time
        #  like we do in other callbacks


class q4y2018HAT(Axp209HAT):

    # The CM4 & RM3 resolves to this HAT class

    # Q4Y2018 - AXP209/OLED (Anker) Unit run specific pins
    # All pin references are now BCM format


    def __init__(self, displayClass):

#        print("            begin q4y2018HAT __init__")
        setup_GPIO()

        if (globals.device_type == "RM3"):
            self.PIN_LED = 31       # GPIO6
            self.PIN_L_BUTTON = 5              # GPIO3
            self.PIN_R_BUTTON = 7              # GPIO4
            self.PIN_AXP_INTERRUPT_LINE = 10   # GPIO_15
            self.PIN_OTG_SENSE = 11               #GPIO_17  (dummy)
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q4y2018HAT for neo")
        elif (globals.device_type == "NEO"):
            self.PIN_LED =      12              # PA6
            self.PIN_L_BUTTON = 8               # PG6
            self.PIN_R_BUTTON = 10              # PG7
            self.PIN_AXP_INTERRUPT_LINE = 16    # PG8
            self.PIN_OTG_SENSE = 11             # PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q4y2018HAT for neo")
        elif (globals.device_type =="CM"):
            self.PIN_LED = 6    # GPIO6
            self.PIN_L_BUTTON = 3               # GPIO3/56
            self.PIN_R_BUTTON = 4               # GPIO4/54
            self.PIN_AXP_INTERRUPT_LINE = 15    # GPIO15/51
            self.PIN_OTG_SENSE = 17               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q4y2018HAT for CM4")

        # We don't currently have a HAT for RPi... so we will get here if HAT wiring is same as CM4 for GPIO
        #  For the moment, we will assume a HAT with GPIO assignments the same as CM4
        else:                   #device type is Pi
            self.PIN_LED = 6    # GPIO6
            self.PIN_L_BUTTON = 3               # GPIO3
            self.PIN_R_BUTTON = 4               # GPIO4
            self.PIN_AXP_INTERRUPT_LIINE = 15   # GPIO15
            self.PIN_OTG_SENSE = 17               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q4y2018HAT for Pi")

        GPIO.setup(self.PIN_LED, GPIO.OUT)
        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_AXP_INTERRUPT_LINE, GPIO.IN)
        GPIO.setup(self.PIN_OTG_SENSE, GPIO.IN)

        # Run parent constructors before adding event detection
        #  as some callbacks require objects only initialised
        #  in parent constructors
        super().__init__(displayClass)

# we handle interrupt setup different for RM3 because OPi.GPIO requires "lambda x:" in the setup
#   ... but maybe RPi.GPIO will tolerate "lambda x:" ??

# Status: these calls setup successfully... we can gett to the handleButtonPress, but
#  the cancel of the event detect throws an error
        if globals.device_type == "RM3":
            GPIO.add_event_detect(self.PIN_L_BUTTON, GPIO.FALLING,
                              callback= lambda x:self.buttons.handleButtonPress(self.PIN_L_BUTTON),
                              bouncetime=125)
            GPIO.add_event_detect(self.PIN_R_BUTTON, GPIO.FALLING,
                              callback=lambda x: self.buttons.handleButtonPress(self.PIN_R_BUTTON),
                              bouncetime=125)
            GPIO.add_event_detect(self.PIN_OTG_SENSE, GPIO.BOTH,
                               callback=lambda x:self.handleOtgSelect(),
                               bouncetime=125)
            GPIO.add_event_detect(self.PIN_AXP_INTERRUPT_LINE, GPIO.FALLING,
                              callback=lambda x:self.shutdownDeviceCallback(self.PIN_AXP_INTERRUPT_LINE))
#            print("registered button events")

        else:
            GPIO.add_event_detect(self.PIN_L_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
            GPIO.add_event_detect(self.PIN_R_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
            GPIO.add_event_detect(self.PIN_OTG_SENSE, GPIO.BOTH,
                               callback=self.handleOtgSelect,
                               bouncetime=125)
            GPIO.add_event_detect(self.PIN_AXP_INTERRUPT_LINE, GPIO.FALLING,
                              callback=self.shutdownDeviceCallback)


        # We only enable interrupts on this HAT, rather than in the superclass
        #  because not all HATs with AXP209s have a line that we can use to
        #  detect the interrupt.
        # (Note... this is NOT the AXP209 IRQ line... it is the AXP209 power down signal)

    # The PIN_AXP_INTERRUPT_LINE interrupt handler services a powerdown signal from the RC
    #  modified AXP209 EXTEN (pin 20)line.
    #  That line goes low on reaching the Voff (Reg 0x31[0:2]) voltage of 3.0V (see line #347)
    #  or upon detection of the PB1 being held longer than 8 sec.

        self.handleOtgSelect(self.PIN_OTG_SENSE)



class q3y2021HAT(Axp209HAT):

    # Q3Y2021 - HAT 7.0.x (NEO)- Also, NEO V8

    def __init__(self, displayClass):

        setup_GPIO()

        if globals.device_type == "NEO":
            self.PIN_LED =      12                # PA6
            self.PIN_L_BUTTON = 8                 # PG6
            self.PIN_R_BUTTON = 10                # PG7
            self.PIN_AXP_INTERRUPT_LINE = 16      # PG8
            self.PIN_OTG_SENSE = 11               # PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q3y2021HAT for neo")
        else:
            self.PIN_LED = 6    # GPIO6
            self.PIN_L_BUTTON = 14                #PG6
            self.PIN_R_BUTTON = 15                #PG7
            self.PIN_AXP_INTERRUPT_LINE = 23      #PG8
            self.PIN_OTG_SENSE = 17               #PA0
            self.USABLE_BUTTONS = [self.PIN_L_BUTTON, self.PIN_R_BUTTON]  # Used in the checkPressTime method
            logging.info("found q3y2021HAT for Pi")

        GPIO.setup(self.PIN_LED, GPIO.OUT)
        GPIO.setup(self.PIN_L_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_R_BUTTON, GPIO.IN)
        GPIO.setup(self.PIN_AXP_INTERRUPT_LINE, GPIO.IN)
        GPIO.setup(self.PIN_OTG_SENSE, GPIO.IN)
        # Run parent constructors before adding event detection
        #  as some callbacks require objects only initialised
        #  in parent constructors
        super().__init__(displayClass)
        GPIO.add_event_detect(self.PIN_L_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        GPIO.add_event_detect(self.PIN_R_BUTTON, GPIO.FALLING,
                              callback=self.buttons.handleButtonPress,
                              bouncetime=125)
        GPIO.add_event_detect(self.PIN_OTG_SENSE, GPIO.BOTH,
                               callback=self.handleOtgSelect,
                               bouncetime=125)


    # This interrupt handler responds to the EXTEN signal of the AXP209. It gives us
    #  a heads up that power is going down either because the IPS OUT voltage is below Voff (0x31[2:0])
    #  or because the user has pushed PB1 longer than 8 seconds

        GPIO.add_event_detect(self.PIN_AXP_INTERRUPT_LINE, GPIO.FALLING,
                              callback=self.shutdownDeviceCallback)
#        self.handleOtgSelect(self.PIN_OTG_SENSE)
