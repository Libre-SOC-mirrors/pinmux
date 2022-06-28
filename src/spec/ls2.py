#!/usr/bin/env python
# see https://bugs.libre-soc.org/show_bug.cgi?id=739

from spec.base import PinSpec
from parse import Parse

from pprint import pprint
from spec.ifaceprint import display, display_fns, check_functions
from spec.ifaceprint import display_fixed
from collections import OrderedDict

def pinspec():
    pinbanks = OrderedDict((
        ('N', (32, 2)),
        ('E', (32, 2)),
        ('S', (32, 2)),
        ('W', (32, 2)),
    ))
    fixedpins = {
        'CTRL_SYS': [
            'TEST',
            'JTAG_SEL',
            'UBOOT_SEL',
            'NMI#',
            'RESET#',
            'CLK24M_IN',
            'CLK24M_OUT',
            'PLLTEST',
            'PLLREGIO',
            'PLLVP25',
            'PLLDV',
            'PLLVREG',
            'PLLGND',
        ],
        'POWER_GPIO': [
            'VDD_GPIOB',
            'GND_GPIOB',
        ]}
    fixedpins = {}
    function_names = {
                      'RG0': 'Gigabit Ethernet 0',
                      'PWM': 'PWM (pulse-width modulation)',
                      'MSPI0': 'SPI Master 1 (general)',
                      'MSPI1': 'SPI Master 2 (SDCard)',
                      'UART0': 'UART (TX/RX) 1',
                      'SYS': 'System Control',
                      'GPIO': 'GPIO',
                      'EINT': 'External Interrupt',
                      'PWM': 'PWM',
                      'JTAG': 'JTAG',
                      'MTWI': 'I2C Master 1',
                      'SD0': 'SD/MMC 1',
                      'SDR': 'SDRAM',
                      'VDD': 'Power',
                      'VSS': 'GND',
                      #'LPC1': 'Low Pincount Interface 1',
                      #'LPC2': 'Low Pincount Interface 2',
                      }

    ps = PinSpec(pinbanks, fixedpins, function_names)

    ps.sdram1("", ('W', 0), 0, 15, 6, rev=True) # AD4-9, turned round
    ps.vdd("E", ('W', 6), 0, 0, 1)
    ps.vss("E", ('W', 7), 0, 0, 1)
    ps.vdd("I", ('W', 8), 0, 0, 1)
    ps.vss("I", ('W', 9), 0, 0, 1)
    ps.sdram1("", ('W', 10), 0, 0, 15, rev=True) # SDRAM DAM0, D0-7, AD0-3
    ps.mi2c("", ('W', 26), 0, 0, 2)
    ps.vss("I", ('W', 28), 0, 1, 1)
    ps.vdd("I", ('W', 29), 0, 1, 1)
    ps.vss("E", ('W', 30), 0, 1, 1)
    ps.vdd("E", ('W', 31), 0, 1, 1)

    ps.sdram2("", ('S', 0), 0, 0, 4) # 1st 4, AD10-12,DQM1
    ps.vdd("E", ('S', 4), 0, 2, 1)
    ps.vss("E", ('S', 5), 0, 2, 1)
    ps.vdd("I", ('S', 6), 0, 2, 1)
    ps.vss("I", ('S', 7), 0, 2, 1)
    ps.sdram2("", ('S', 8), 0, 4, 8) # D8-15
    ps.sdram1("", ('S', 16), 0, 21, 9) # clk etc.
    ps.vss("I", ('S', 22), 0, 3, 1)
    ps.vdd("I", ('S', 23), 0, 3, 1)
    ps.vss("E", ('S', 24), 0, 3, 1)
    ps.vdd("E", ('S', 25), 0, 3, 1)
    ps.uart("0", ('S', 26), 0)
    ps.mspi("0", ('S', 28), 0)

    ps.gpio("", ('E', 0), 0, 0, 6) # GPIO 0-5
    ps.vss("E", ('E', 6), 0, 4, 1)
    ps.vdd("E", ('E', 7), 0, 4, 1)
    ps.vdd("I", ('E', 8), 0, 4, 1)
    ps.vss("I", ('E', 9), 0, 4, 1)
    ps.gpio("", ('E', 10), 0, 6, 3) # GPIO 6-8
    ps.jtag("", ('E', 13), 0, 0, 4)
    ps.gpio("", ('E', 17), 0, 9, 5) # GPIO 9-13
    ps.vss("I", ('E', 22), 0, 5, 1)
    ps.vdd("I", ('E', 23), 0, 5, 1)
    ps.vss("E", ('E', 24), 0, 5, 1)
    ps.vdd("E", ('E', 25), 0, 5, 1)
    ps.gpio("", ('E', 26), 0, 14, 2) # GPIO 14-15
    ps.eint("", ('E', 28), 0, 0, 3)
    ps.sys("", ('E', 31), 0, 5, 1) # analog VCO out in right top

    ps.vss("E", ('N', 1), 0, 6, 1)
    ps.vdd("E", ('N', 2), 0, 6, 1)
    ps.vdd("I", ('N', 3), 0, 6, 1)
    ps.vss("I", ('N', 4), 0, 6, 1)
    ps.rgmii("0", ('N', 5), 0, 0, 18)
    #ps.pwm("", ('N', 2), 0, 0, 2)  comment out (litex problem 25mar2021)
    #ps.mspi("1", ('N', 7), 0)       comment out (litex problem 25mar2021)
    #ps.sdmmc("0", ('N', 11), 0)     # comment out (litex problem 25mar2021)
    ps.sys("", ('N', 27), 0, 0, 5) # all but analog out in top right
    ps.vss("I", ('N', 23), 0, 7, 1)
    ps.vdd("I", ('N', 24), 0, 7, 1)
    ps.vss("E", ('N', 25), 0, 7, 1)
    ps.vdd("E", ('N', 26), 0, 7, 1)

    #ps.mquadspi("1", ('S', 0), 0)

    print ("ps clocks", ps.clocks)

    # Scenarios below can be spec'd out as either "find first interface"
    # by name/number e.g. SPI1, or as "find in bank/mux" which must be
    # spec'd as "BM:Name" where B is bank (A-F), M is Mux (0-3)
    # EINT and PWM are grouped together, specially, but may still be spec'd
    # using "BM:Name".  Pins are removed in-order as listed from
    # lists (interfaces, EINTs, PWMs) from available pins.

    ls180 = [
            # 'SD0', litex problem 25mar2021
            'UART0', 'GPIOS', 'GPIOE', 'JTAG', 'PWM', 'EINT',
             'VDD', 'VSS', 'SYS',
                'MTWI', 'MSPI0',
                # 'MSPI1', litex problem 25mar2021
                'SDR']
    ls180_eint = []
    ls180_pwm = []#['B0:PWM_0']
    descriptions = {
        'SD0': 'user-facing: internal (on Card), multiplexed with JTAG\n'
        'and UART2, for debug purposes',
        'MTWI': 'I2C.\n',
        'E2:SD1': '',
        'MSPI1': '',
        'UART0': '',
        'LPC1': '',
        'SYS': '',
        'LPC2': '',
        'SDR': '',
        'B1:LCD/22': '18-bit RGB/TTL LCD',
        'ULPI0/8': 'user-facing: internal (on Card), USB-OTG ULPI PHY',
        'ULPI1': 'dual USB2 Host ULPI PHY'
    }

    ps.add_scenario("Libre-SOC 2 (NGI Router) 180nm", ls180, ls180_eint,
                    ls180_pwm, descriptions)

    return ps
