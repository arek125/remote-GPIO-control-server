#!/usr/bin/python
#
# Copyright (c) 2015 Iain Colledge for Adafruit Industries
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""
Python library for the TSL2561 digital luminosity (light) sensors.

This library is heavily based on the Arduino library for the TSL2561 digital
luminosity (light) sensors. It is basically a simple translation from C++ to
Python.

The thread on the Adafruit forum helped a lot to do this.  Thanks to static,
huelke, pandring, adafruit_support_rick, scortier, bryand, csalty, lenos and
of course to Adafruit

Source for the Arduino library:
https://github.com/adafruit/TSL2561-Arduino-Library

Adafruit forum thread:
http://forums.adafruit.com/viewtopic.php?f=8&t=34922&sid=8336d566f2f03c25882aaf34c8a15a92

Original code posted here:
http://forums.adafruit.com/viewtopic.php?f=8&t=34922&start=75#p222877

This was checked against a 10 UKP lux meter from Amazon and was withing 10% up
and down the range, the meter had a stated accuracy of 5% but then again, 10
UKP meter.

Changelog:

1.2 - Additional clean-up - Chris Satterlee
    Added underscore back into class name
    Removed unnecessary inheritance from Adafruit_I2C
    Removed vestigial trailing */ from comments
    Removed (now unnecessary) autogain hack
    Fold (most) long lines to comply with col 80 limit
    Added BSD license header comment
1.1 - Fixes from
      https://forums.adafruit.com/viewtopic.php?f=8&t=34922&p=430795#p430782
      - Iain Colledge
    Bug #1: The class name has the middle two digits transposed -
            Adafruit_TSL2651 should be Adafruit_TSL2561
    Bug #2: The read8 and read16 methods (functions) call the I2C readS8 and
            readS16 methods respectively.  They should call the readU8 and
            readU16 (i.e. unsigned) methods.
    Minor fixes and changes due to Pycharm and SonarQube recommendations, it
      looks like Python more than C++ now
    Added Exception thrown on sensor saturation
1.0 - Initial release - Iain Colledge
    Removed commented out C++ code
    Added calculate_avg_lux
    Changed main method to use calculate_avg_lux and loop argument support
       added.
    Ported "Extended delays to take into account loose timing with 'delay'"
       update from CPP code
    Added hack so that with autogain every sample goes from 1x to 16x as going
       from 16x to 1x does not work
"""

from __future__ import print_function
import logging
import sys
import time
from Adafruit_I2C import Adafruit_I2C

# Logging needs to be set at top after imports
# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

class Adafruit_TSL2561(object):
    TSL2561_VISIBLE           = 2       # channel 0 - channel 1
    TSL2561_INFRARED          = 1       # channel 1
    TSL2561_FULLSPECTRUM      = 0       # channel 0

    # I2C address options
    TSL2561_ADDR_LOW          = 0x29
    TSL2561_ADDR_FLOAT        = 0x39    # Default address (pin left floating)
    TSL2561_ADDR_HIGH         = 0x49

    # Lux calculations differ slightly for CS package
    TSL2561_PACKAGE_CS        = 0
    TSL2561_PACKAGE_T_FN_CL   = 1

    TSL2561_COMMAND_BIT       = 0x80    # Must be 1
    TSL2561_CLEAR_BIT         = 0x40    # Clears any pending interrupt (write 1 to clear)
    TSL2561_WORD_BIT          = 0x20    # 1 = read/write word (rather than byte)
    TSL2561_BLOCK_BIT         = 0x10    # 1 = using block read/write

    TSL2561_CONTROL_POWERON   = 0x03
    TSL2561_CONTROL_POWEROFF  = 0x00

    TSL2561_LUX_LUXSCALE      = 14      # Scale by 2^14
    TSL2561_LUX_RATIOSCALE    = 9       # Scale ratio by 2^9
    TSL2561_LUX_CHSCALE       = 10      # Scale channel values by 2^10
    TSL2561_LUX_CHSCALE_TINT0 = 0x7517  # 322/11 * 2^TSL2561_LUX_CHSCALE
    TSL2561_LUX_CHSCALE_TINT1 = 0x0FE7  # 322/81 * 2^TSL2561_LUX_CHSCALE

    # T, FN and CL package values
    TSL2561_LUX_K1T           = 0x0040  # 0.125 * 2^RATIO_SCALE
    TSL2561_LUX_B1T           = 0x01f2  # 0.0304 * 2^LUX_SCALE
    TSL2561_LUX_M1T           = 0x01be  # 0.0272 * 2^LUX_SCALE
    TSL2561_LUX_K2T           = 0x0080  # 0.250 * 2^RATIO_SCALE
    TSL2561_LUX_B2T           = 0x0214  # 0.0325 * 2^LUX_SCALE
    TSL2561_LUX_M2T           = 0x02d1  # 0.0440 * 2^LUX_SCALE
    TSL2561_LUX_K3T           = 0x00c0  # 0.375 * 2^RATIO_SCALE
    TSL2561_LUX_B3T           = 0x023f  # 0.0351 * 2^LUX_SCALE
    TSL2561_LUX_M3T           = 0x037b  # 0.0544 * 2^LUX_SCALE
    TSL2561_LUX_K4T           = 0x0100  # 0.50 * 2^RATIO_SCALE
    TSL2561_LUX_B4T           = 0x0270  # 0.0381 * 2^LUX_SCALE
    TSL2561_LUX_M4T           = 0x03fe  # 0.0624 * 2^LUX_SCALE
    TSL2561_LUX_K5T           = 0x0138  # 0.61 * 2^RATIO_SCALE
    TSL2561_LUX_B5T           = 0x016f  # 0.0224 * 2^LUX_SCALE
    TSL2561_LUX_M5T           = 0x01fc  # 0.0310 * 2^LUX_SCALE
    TSL2561_LUX_K6T           = 0x019a  # 0.80 * 2^RATIO_SCALE
    TSL2561_LUX_B6T           = 0x00d2  # 0.0128 * 2^LUX_SCALE
    TSL2561_LUX_M6T           = 0x00fb  # 0.0153 * 2^LUX_SCALE
    TSL2561_LUX_K7T           = 0x029a  # 1.3 * 2^RATIO_SCALE
    TSL2561_LUX_B7T           = 0x0018  # 0.00146 * 2^LUX_SCALE
    TSL2561_LUX_M7T           = 0x0012  # 0.00112 * 2^LUX_SCALE
    TSL2561_LUX_K8T           = 0x029a  # 1.3 * 2^RATIO_SCALE
    TSL2561_LUX_B8T           = 0x0000  # 0.000 * 2^LUX_SCALE
    TSL2561_LUX_M8T           = 0x0000  # 0.000 * 2^LUX_SCALE

    # CS package values
    TSL2561_LUX_K1C           = 0x0043  # 0.130 * 2^RATIO_SCALE
    TSL2561_LUX_B1C           = 0x0204  # 0.0315 * 2^LUX_SCALE
    TSL2561_LUX_M1C           = 0x01ad  # 0.0262 * 2^LUX_SCALE
    TSL2561_LUX_K2C           = 0x0085  # 0.260 * 2^RATIO_SCALE
    TSL2561_LUX_B2C           = 0x0228  # 0.0337 * 2^LUX_SCALE
    TSL2561_LUX_M2C           = 0x02c1  # 0.0430 * 2^LUX_SCALE
    TSL2561_LUX_K3C           = 0x00c8  # 0.390 * 2^RATIO_SCALE
    TSL2561_LUX_B3C           = 0x0253  # 0.0363 * 2^LUX_SCALE
    TSL2561_LUX_M3C           = 0x0363  # 0.0529 * 2^LUX_SCALE
    TSL2561_LUX_K4C           = 0x010a  # 0.520 * 2^RATIO_SCALE
    TSL2561_LUX_B4C           = 0x0282  # 0.0392 * 2^LUX_SCALE
    TSL2561_LUX_M4C           = 0x03df  # 0.0605 * 2^LUX_SCALE
    TSL2561_LUX_K5C           = 0x014d  # 0.65 * 2^RATIO_SCALE
    TSL2561_LUX_B5C           = 0x0177  # 0.0229 * 2^LUX_SCALE
    TSL2561_LUX_M5C           = 0x01dd  # 0.0291 * 2^LUX_SCALE
    TSL2561_LUX_K6C           = 0x019a  # 0.80 * 2^RATIO_SCALE
    TSL2561_LUX_B6C           = 0x0101  # 0.0157 * 2^LUX_SCALE
    TSL2561_LUX_M6C           = 0x0127  # 0.0180 * 2^LUX_SCALE
    TSL2561_LUX_K7C           = 0x029a  # 1.3 * 2^RATIO_SCALE
    TSL2561_LUX_B7C           = 0x0037  # 0.00338 * 2^LUX_SCALE
    TSL2561_LUX_M7C           = 0x002b  # 0.00260 * 2^LUX_SCALE
    TSL2561_LUX_K8C           = 0x029a  # 1.3 * 2^RATIO_SCALE
    TSL2561_LUX_B8C           = 0x0000  # 0.000 * 2^LUX_SCALE
    TSL2561_LUX_M8C           = 0x0000  # 0.000 * 2^LUX_SCALE

    # Auto-gain thresholds
    TSL2561_AGC_THI_13MS      = 4850    # Max value at Ti 13ms = 5047
    TSL2561_AGC_TLO_13MS      = 100
    TSL2561_AGC_THI_101MS     = 36000   # Max value at Ti 101ms = 37177
    TSL2561_AGC_TLO_101MS     = 200
    TSL2561_AGC_THI_402MS     = 63000   # Max value at Ti 402ms = 65535
    TSL2561_AGC_TLO_402MS     = 500

    # Clipping thresholds
    TSL2561_CLIPPING_13MS     = 4900
    TSL2561_CLIPPING_101MS    = 37000
    TSL2561_CLIPPING_402MS    = 65000

    TSL2561_REGISTER_CONTROL          = 0x00
    TSL2561_REGISTER_TIMING           = 0x01
    TSL2561_REGISTER_THRESHHOLDL_LOW  = 0x02
    TSL2561_REGISTER_THRESHHOLDL_HIGH = 0x03
    TSL2561_REGISTER_THRESHHOLDH_LOW  = 0x04
    TSL2561_REGISTER_THRESHHOLDH_HIGH = 0x05
    TSL2561_REGISTER_INTERRUPT        = 0x06
    TSL2561_REGISTER_CRC              = 0x08
    TSL2561_REGISTER_ID               = 0x0A
    TSL2561_REGISTER_CHAN0_LOW        = 0x0C
    TSL2561_REGISTER_CHAN0_HIGH       = 0x0D
    TSL2561_REGISTER_CHAN1_LOW        = 0x0E
    TSL2561_REGISTER_CHAN1_HIGH       = 0x0F

    TSL2561_INTEGRATIONTIME_13MS      = 0x00    # 13.7ms
    TSL2561_INTEGRATIONTIME_101MS     = 0x01    # 101ms
    TSL2561_INTEGRATIONTIME_402MS     = 0x02    # 402ms

    TSL2561_DELAY_INTTIME_13MS        = 0.015
    TSL2561_DELAY_INTTIME_101MS       = 0.120
    TSL2561_DELAY_INTTIME_402MS       = 0.450

    TSL2561_GAIN_1X                   = 0x00    # No gain
    TSL2561_GAIN_16X                  = 0x10    # 16x gain

    TSL2561_NO_OF_AVG_SAMPLES         = 25      # How many samples to make an average reading

    def write8(self, reg, value):
        """
        Writes a register and an 8 bit value over I2C

        :param reg: Register / Address to write value to
        :param value: Byte to write to Address
        """
        logging.debug('write8')
        self._i2c.write8(reg, value)
        logging.debug('write8_end')

    def read8(self, reg):
        """
        Reads an 8 bit value over I2C

        :param reg: Register / Address to read value from
        :return: Unsigned byte
        """
        logging.debug('read8')
        return self._i2c.readU8(reg)

    def read16(self, reg):
        """
        Reads a 16 bit values over I2C

        :param reg: Register / Address to read value from
        :return: Unsigned word
        """
        logging.debug('read16')
        return self._i2c.readU16(reg)

    def enable(self):
        """
        Enables the device
        """
        logging.debug('enable')
        # Enable the device by setting the control bit to 0x03
        self._i2c.write8(self.TSL2561_COMMAND_BIT |
                         self.TSL2561_REGISTER_CONTROL,
                         self.TSL2561_CONTROL_POWERON)
        logging.debug('enable_end')

    def disable(self):
        """
        Disables the device (putting it in lower power sleep mode)
        """
        logging.debug('disable')
        # Turn the device off to save power
        self._i2c.write8(self.TSL2561_COMMAND_BIT |
                         self.TSL2561_REGISTER_CONTROL,
                         self.TSL2561_CONTROL_POWEROFF)
        logging.debug('disable_end')

    def get_data(self):
        """
        Private function to read luminosity on both channels
        """
        logging.debug('get_data')

        # Enables the device by setting the control bit to 0x03
        self.enable()

        # Wait x ms for ADC to complete
        if self._tsl2561IntegrationTime == self.TSL2561_INTEGRATIONTIME_13MS:
            time.sleep(self.TSL2561_DELAY_INTTIME_13MS)
        elif self._tsl2561IntegrationTime == self.TSL2561_INTEGRATIONTIME_101MS:
            time.sleep(self.TSL2561_DELAY_INTTIME_101MS)
        else:
            time.sleep(self.TSL2561_DELAY_INTTIME_402MS)

        # Reads a two byte value from channel 0 (visible + infrared)
        # noinspection PyPep8
        self._broadband = self.read16(self.TSL2561_COMMAND_BIT |
                                      self.TSL2561_WORD_BIT |
                                      self.TSL2561_REGISTER_CHAN0_LOW)

        # Reads a two byte value from channel 1 (infrared)
        self._ir = self.read16(self.TSL2561_COMMAND_BIT |
                               self.TSL2561_WORD_BIT |
                               self.TSL2561_REGISTER_CHAN1_LOW)

        # Turn the device off to save power
        self.disable()
        logging.debug('getData_end"')

    # noinspection PyMissingConstructor
    def __init__(self, address=TSL2561_ADDR_FLOAT, debug=False):
        """
        Constructor

        :param address: I2C address of TSL2561, defaults to 0x39
        :param debug: Turn on debugging, defaults to False
        """
        self._debug = debug
        logging.debug('__init__"')
        self._address = address
        self._tsl2561Initialised = False
        self._tsl2561AutoGain = False
        self._tsl2561IntegrationTime = self.TSL2561_INTEGRATIONTIME_13MS
        self._tsl2561Gain = self.TSL2561_GAIN_1X
        self._i2c = Adafruit_I2C(self._address)
        self._luminosity = 0
        self._broadband = 0
        self._ir = 0
        logging.debug('__init___end')

    def begin(self):
        """
        Initializes I2C and configures the sensor (call this function before
        doing anything else)

        Note: by default, the device is in power down mode on bootup

        :return: True if connected to a TSL2561
        """
        logging.debug('begin')
        # Make sure we're actually connected
        x = self.read8(self.TSL2561_REGISTER_ID)
        if not(x & 0x0A):
            return False
        self._tsl2561Initialised = True

        # Set default integration time and gain
        self.set_integration_time(self._tsl2561IntegrationTime)
        self.set_gain(self._tsl2561Gain)

        # Note: by default, the device is in power down mode on bootup
        self.disable()
        logging.debug('begin_end')

        return True

    def enable_auto_gain(self, enable):
        """
        Enables or disables the auto-gain settings when reading
        data from the sensor

        :param enable: True to enable
        """
        logging.debug('enable_auto_gain')
        if enable:
            self._tsl2561AutoGain = enable
        else:
            self._tsl2561AutoGain = False
        logging.debug('enableAutoGain_end')

    def set_integration_time(self, integration_time):
        """
        Sets the integration integration_time for the TSL2561

        :param integration_time:
        :return:
        """
        logging.debug('set_integration_time')
        if not self._tsl2561Initialised:
            self.begin()

        # Enable the device by setting the control bit to 0x03
        self.enable()

        # Update the timing register
        self.write8(self.TSL2561_COMMAND_BIT |
                    self.TSL2561_REGISTER_TIMING, integration_time |
                    self._tsl2561Gain)

        # Update value placeholders
        self._tsl2561IntegrationTime = integration_time

        # Turn the device off to save power
        self.disable()
        logging.debug('setIntegrationTime_end')

    def set_gain(self, gain):
        """
        Adjusts the gain on the TSL2561 (adjusts the sensitivity to light)

        :param gain:
        """
        logging.debug('set_gain')
        if not self._tsl2561Initialised:
            self.begin()

        # Enable the device by setting the control bit to 0x03
        self.enable()

        # Update the timing register
        self.write8(self.TSL2561_COMMAND_BIT |
                    self.TSL2561_REGISTER_TIMING,
                    self._tsl2561IntegrationTime | gain)

        # Update value placeholders
        self._tsl2561Gain = gain

        # Turn the device off to save power
        self.disable()
        logging.debug('setGain_end')

    def get_luminosity(self):
        """
        Gets the broadband (mixed lighting) and IR only values from
        the TSL2561, adjusting gain if auto-gain is enabled

        """

        logging.debug('get_luminosity')
        valid = False

        if not self._tsl2561Initialised:
            self.begin()

        # If Auto gain disabled get a single reading and continue
        if not self._tsl2561AutoGain:
            self.get_data()
            return

        # Read data until we find a valid range
        agc_check = False
        while not valid:
            _it = self._tsl2561IntegrationTime

            # Get the hi/low threshold for the current integration time
            if _it==self.TSL2561_INTEGRATIONTIME_13MS:
                _hi = self.TSL2561_AGC_THI_13MS
                _lo = self.TSL2561_AGC_TLO_13MS
            elif _it==self.TSL2561_INTEGRATIONTIME_101MS:
                _hi = self.TSL2561_AGC_THI_101MS
                _lo = self.TSL2561_AGC_TLO_101MS
            else:
                _hi = self.TSL2561_AGC_THI_402MS
                _lo = self.TSL2561_AGC_TLO_402MS

            self.get_data()

            # Run an auto-gain check if we haven't already done so ...
            if not agc_check:
                if (self._broadband < _lo) and \
                        (self._tsl2561Gain == self.TSL2561_GAIN_1X):
                    # Increase the gain and try again
                    self.set_gain(self.TSL2561_GAIN_16X)
                    # Drop the previous conversion results
                    self.get_data()
                    # Set a flag to indicate we've adjusted the gain
                    agc_check = True
                elif (self._broadband > _hi) and \
                        (self._tsl2561Gain == self.TSL2561_GAIN_16X):
                    # Drop gain to 1x and try again
                    self.set_gain(self.TSL2561_GAIN_1X)
                    # Drop the previous conversion results
                    self.get_data()
                    # Set a flag to indicate we've adjusted the gain
                    agc_check = True
                else:
                    # Nothing to look at here, keep moving ....
                    # Reading is either valid, or we're already at the chip's
                    # limits
                    valid = True
            else:
                # If we've already adjusted the gain once, just return the new
                # results.  This avoids endless loops where a value is at one
                # extreme pre-gain, and the the other extreme post-gain
                valid = True
        logging.debug('getLuminosity_end')

    def calculate_lux(self):
        """
        Converts the raw sensor values to the standard SI lux equivalent.
        Returns 0 if the sensor is saturated and the values are unreliable.

        :return: lux value, unsigned 16bit word (0 - 65535)
        :raises: OverflowError when TSL2561 sensor is saturated

        """
        logging.debug('calculate_lux')
        self.get_luminosity()
        # Make sure the sensor isn't saturated!
        if self._tsl2561IntegrationTime == self.TSL2561_INTEGRATIONTIME_13MS:
            clip_threshold = self.TSL2561_CLIPPING_13MS
        elif self._tsl2561IntegrationTime == self.TSL2561_INTEGRATIONTIME_101MS:
            clip_threshold = self.TSL2561_CLIPPING_101MS
        else:
            clip_threshold = self.TSL2561_CLIPPING_402MS

        # Raise exception if either or both sensor channels are saturated
        if (self._broadband > clip_threshold) and (self._ir > clip_threshold):
            raise OverflowError('TSL2561 Sensor Saturated (both channels)')
        elif (self._broadband > clip_threshold):
            raise OverflowError('TSL2561 Sensor Saturated (broadband channel)')
        elif (self._ir > clip_threshold):
            raise OverflowError('TSL2561 Sensor Saturated (IR channel)')

        # Get the correct scale depending on the integration time
        if self._tsl2561IntegrationTime ==self.TSL2561_INTEGRATIONTIME_13MS:
            ch_scale = self.TSL2561_LUX_CHSCALE_TINT0
        elif self._tsl2561IntegrationTime ==self.TSL2561_INTEGRATIONTIME_101MS:
            ch_scale = self.TSL2561_LUX_CHSCALE_TINT1
        else:
            ch_scale = 1 << self.TSL2561_LUX_CHSCALE

        # Scale for gain (1x or 16x)
        if not self._tsl2561Gain:
            ch_scale <<= 4

        # Scale the channel values
        channel0 = (self._broadband * ch_scale) >> self.TSL2561_LUX_CHSCALE
        channel1 = (self._ir * ch_scale) >> self.TSL2561_LUX_CHSCALE

        # Find the ratio of the channel values (Channel1/Channel0)
        ratio1 = 0
        if channel0 != 0:
            ratio1 = (channel1 << (self.TSL2561_LUX_RATIOSCALE + 1)) / channel0

        # round the ratio value
        ratio = (ratio1 + 1) >> 1

        if self.TSL2561_PACKAGE_CS == 1:
            if (ratio >= 0) and (ratio <= self.TSL2561_LUX_K1C):
                b=self.TSL2561_LUX_B1C
                m=self.TSL2561_LUX_M1C
            elif ratio <= self.TSL2561_LUX_K2C:
                b=self.TSL2561_LUX_B2C
                m=self.TSL2561_LUX_M2C
            elif ratio <= self.TSL2561_LUX_K3C:
                b=self.TSL2561_LUX_B3C
                m=self.TSL2561_LUX_M3C
            elif ratio <= self.TSL2561_LUX_K4C:
                b=self.TSL2561_LUX_B4C
                m=self.TSL2561_LUX_M4C
            elif ratio <= self.TSL2561_LUX_K5C:
                b=self.TSL2561_LUX_B5C
                m=self.TSL2561_LUX_M5C
            elif ratio <= self.TSL2561_LUX_K6C:
                b=self.TSL2561_LUX_B6C
                m=self.TSL2561_LUX_M6C
            elif ratio <= self.TSL2561_LUX_K7C:
                b=self.TSL2561_LUX_B7C
                m=self.TSL2561_LUX_M7C
            elif ratio > self.TSL2561_LUX_K8C:
                b=self.TSL2561_LUX_B8C
                m=self.TSL2561_LUX_M8C
        elif self.TSL2561_PACKAGE_T_FN_CL == 1:
            if (ratio >= 0) and (ratio <= self.TSL2561_LUX_K1T):
                b=self.TSL2561_LUX_B1T
                m=self.TSL2561_LUX_M1T
            elif ratio <= self.TSL2561_LUX_K2T:
                b=self.TSL2561_LUX_B2T
                m=self.TSL2561_LUX_M2T
            elif ratio <= self.TSL2561_LUX_K3T:
                b=self.TSL2561_LUX_B3T
                m=self.TSL2561_LUX_M3T
            elif ratio <= self.TSL2561_LUX_K4T:
                b=self.TSL2561_LUX_B4T
                m=self.TSL2561_LUX_M4T
            elif ratio <= self.TSL2561_LUX_K5T:
                b=self.TSL2561_LUX_B5T
                m=self.TSL2561_LUX_M5T
            elif ratio <= self.TSL2561_LUX_K6T:
                b=self.TSL2561_LUX_B6T
                m=self.TSL2561_LUX_M6T
            elif ratio <= self.TSL2561_LUX_K7T:
                b=self.TSL2561_LUX_B7T
                m=self.TSL2561_LUX_M7T
            elif ratio > self.TSL2561_LUX_K8T:
                b=self.TSL2561_LUX_B8T
                m=self.TSL2561_LUX_M8T
        # endif

        # noinspection PyUnboundLocalVariable,PyUnboundLocalVariable
        temp = (channel0 * b) - (channel1 * m)

        # Do not allow negative lux value
        if temp < 0:
            temp = 0

        # Round lsb (2^(LUX_SCALE-1))
        temp += 1 << (self.TSL2561_LUX_LUXSCALE - 1)

        # Strip off fractional portion
        lux = temp >> self.TSL2561_LUX_LUXSCALE

        # Signal I2C had no errors
        logging.debug('calculateLux_end')
        return lux

    def calculate_avg_lux(self, testavg=TSL2561_NO_OF_AVG_SAMPLES):
        """
        Calculates an averaged Lux value, useful for flickering lights and for
        smoothing values due to noise

        :param testavg: Number of samples to take in a reading, defaults to 25
        :return: lux value, unsigned 16bit word (0 - 65535)
        """
        # Set initial vars
        count = 0
        luxavgtotal = 0
        # Create a cumulative total of values for 'testavg' tests
        while True:
            capture = self.calculate_lux()
            luxavgtotal += capture
            count += 1
            # Once we reach the number of required tests, work out the average
            if count >= testavg:
                luxavg = round(luxavgtotal / testavg)
                return luxavg

if __name__ == "__main__":
    LightSensor = Adafruit_TSL2561()
    LightSensor.enable_auto_gain(True)

    # See if "loop" has been passed as an arg.
    try:
        arg = sys.argv[1]
        if arg == "loop":
            while True:
                try:
                    print(int(LightSensor.calculate_avg_lux()))
                except OverflowError as e:
                    print(e)
                except KeyboardInterrupt:
                    quit()
        else:
            print("Invalid arg(s):", sys.argv[1])
    except IndexError:
        print(int(LightSensor.calculate_avg_lux()))
