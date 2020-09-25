#!/usr/bin/env python
# see https://bugs.libre-soc.org/show_bug.cgi?id=304

from spec.base import PinSpec

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
                      'PWM': 'PWM (pulse-width modulation)',
                      'MSPI0': 'SPI Master 1 (general)',
                      'MSPI1': 'SPI Master 2 (SDCard)',
                      'UART0': 'UART (TX/RX) 1',
                      'CLK': 'System Clock',
                      'RST': 'Reset',
                      'GPIO': 'GPIO',
                      'EINT': 'External Interrupt',
                      'PWM': 'PWM',
                      'JTAG': 'JTAG',
                      'SD0': 'SD/MMC 1',
                      'SDR': 'SDRAM',
                      'VDD': 'Power',
                      'VSS': 'GND',
                      #'LPC1': 'Low Pincount Interface 1',
                      #'LPC2': 'Low Pincount Interface 2',
                      }

    ps = PinSpec(pinbanks, fixedpins, function_names)

    ps.vss("", ('N', 0), 0, 0, 1)
    ps.vdd("", ('N', 1), 0, 0, 1)
    ps.sdram1("", ('N', 2), 0, 0, 30)
    ps.vss("", ('N', 30), 0, 1, 1)
    ps.vdd("", ('N', 31), 0, 1, 1)

    ps.vss("", ('E', 0), 0, 2, 1)
    ps.sdram2("", ('E', 1), 0, 0, 12)
    ps.vdd("", ('E', 13), 0, 2, 1)
    ps.gpio("", ('E', 14), 0, 8, 8)
    ps.vss("", ('E', 23), 0, 3, 1)
    ps.jtag("", ('E', 24), 0, 0, 4)
    ps.vdd("", ('E', 31), 0, 3, 1)

    ps.vss("", ('S', 0), 0, 4, 1)
    ps.clk("", ('S', 1), 0, 0, 1)
    ps.rst("", ('S', 2), 0, 0, 1)
    ps.mspi("0", ('S', 4), 0)
    ps.uart("0", ('S', 8), 0)
    ps.gpio("", ('S', 14), 0, 0, 8)
    ps.vdd("", ('S', 31), 0, 4, 1)

    ps.vss("", ('W', 0), 0, 5, 1)
    ps.pwm("", ('W', 1), 0, 0, 2)
    ps.eint("", ('W', 3), 0, 0, 3)
    ps.mspi("1", ('W', 6), 0)
    ps.vdd("", ('W', 10), 0, 5, 1)
    ps.sdmmc("0", ('W', 11), 0)
    ps.vss("", ('W', 17), 0, 6, 1)
    ps.vdd("", ('W', 31), 0, 6, 1)
    #ps.mspi("0", ('W', 8), 0)
    #ps.mspi("1", ('W', 8), 0)

    #ps.mquadspi("1", ('S', 0), 0)

    # Scenarios below can be spec'd out as either "find first interface"
    # by name/number e.g. SPI1, or as "find in bank/mux" which must be
    # spec'd as "BM:Name" where B is bank (A-F), M is Mux (0-3)
    # EINT and PWM are grouped together, specially, but may still be spec'd
    # using "BM:Name".  Pins are removed in-order as listed from
    # lists (interfaces, EINTs, PWMs) from available pins.

    ls180 = ['SD0', 'UART0', 'GPIOS', 'GPIOE', 'JTAG', 'PWM', 'EINT',
             'VDD', 'VSS', 'CLK', 'RST',
                'TWI0', 'MSPI0', 'MSPI1', 'SDR']
    ls180_eint = []
    ls180_pwm = []#['B0:PWM_0']
    descriptions = {
        'SD0': 'user-facing: internal (on Card), multiplexed with JTAG\n'
        'and UART2, for debug purposes',
        'TWI2': 'I2C.\n',
        'E2:SD1': '',
        'MSPI1': '',
        'UART0': '',
        'LPC1': '',
        'CLK': '',
        'RST': '',
        'LPC2': '',
        'SDR': '',
        'B1:LCD/22': '18-bit RGB/TTL LCD',
        'ULPI0/8': 'user-facing: internal (on Card), USB-OTG ULPI PHY',
        'ULPI1': 'dual USB2 Host ULPI PHY'
    }

    ps.add_scenario("Libre-SOC 180nm", ls180, ls180_eint, ls180_pwm,
                    descriptions)

    return ps
