#!/usr/bin/env python

from spec.base import PinSpec

from spec.ifaceprint import display, display_fns, check_functions
from spec.ifaceprint import display_fixed


def pinspec():
    pinbanks = {
        'A': 28,
        'B': 18,
        'C': 24,
    }
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
    function_names = {'EINT': 'External Interrupt',
                      'FB': 'MC68k FlexBus',
                      'IIS': 'I2S Audio',
                      'JTAG': 'JTAG (JTAG_SEL=HI/LO)',
                      'LCD': '24-pin RGB/TTL LCD',
                      'RG': 'RGMII Ethernet',
                      'MMC': 'eMMC 1/2/4/8 pin',
                      'PWM': 'PWM (pulse-width modulation)',
                      'SD0': 'SD/MMC 0',
                      'SD1': 'SD/MMC 1',
                      'SD2': 'SD/MMC 2',
                      'MSPI0': 'SPI (Serial Peripheral Interface) Master 0',
                      'MSPI1': 'SPI (Serial Peripheral Interface) Master 1',
                      'MQSPI': 'Quad SPI Master 0',
                      'TWI0': 'I2C 0',
                      'TWI1': 'I2C 1',
                      'TWI2': 'I2C 2',
                      'QUART0': 'UART (TX/RX/CTS/RTS) 0',
                      'QUART1': 'UART (TX/RX/CTS/RTS) 1',
                      'UART0': 'UART (TX/RX) 0',
                      'UART1': 'UART (TX/RX) 1',
                      'UART2': 'UART (TX/RX) 2',
                      'ULPI0': 'ULPI (USB Low Pin-count) 0',
                      'ULPI1': 'ULPI (USB Low Pin-count) 1',
                      'ULPI2': 'ULPI (USB Low Pin-count) 2',
                      }

    ps = PinSpec(pinbanks, fixedpins, function_names,
                 ['lcd', 'jtag', 'fb'])

    # Bank A, 0-27
    ps.gpio("", ('A', 0), 0, 0, 28)
    ps.rgbttl("", ('A', 0), 1, limit=22)
    ps.mspi("0", ('A', 10), 2)
    ps.mquadspi("", ('A', 4), 2)
    ps.uart("0", ('A', 16), 2)
    ps.i2c("1", ('A', 18), 2)
    ps.pwm("", ('A', 21), 2, 0, 3)
    ps.sdmmc("0", ('A', 22), 3)
    ps.eint("", ('A', 0), 3, 0, 4)
    ps.eint("", ('A', 20), 2, 4, 1)
    ps.eint("", ('A', 23), 1, 5, 1)
    ps.sdmmc("1", ('A', 4), 3)
    ps.jtag("", ('A', 10), 3)
    ps.uartfull("0", ('A', 14), 3)
    ps.uartfull("1", ('A', 18), 3)
    ps.jtag("", ('A', 24), 2)
    ps.mspi("1", ('A', 24), 1)
    ps.i2c("0", ('A', 0), 2)
    ps.uart("1", ('A', 2), 2)
    ps.uart("2", ('A', 14), 2)

    # see comment in spec.interfaces.PinGen, this is complicated.
    flexspec = {
        #'FB_TS': ('FB_ALE', 2), # commented out for now
        'FB_CS2': ('FB_BWE2', 2),
        'FB_AD0': ('FB_BWE2', 3),
        'FB_CS3': ('FB_BWE3', 2),
        'FB_AD1': ('FB_BWE3', 3),
        'FB_TBST': ('FB_OE', 2),
        'FB_TSIZ0': ('FB_BWE0', 2),
        'FB_TSIZ1': ('FB_BWE1', 2),
    }
    ps.gpio("", ('B', 0), 0, 0, 18)
    ps.flexbus1("", ('B', 0), 1, spec=flexspec)

    ps.gpio("", ('C', 0), 0, 0, 24)
    ps.flexbus2("", ('C', 0), 1)

    # Scenarios below can be spec'd out as either "find first interface"
    # by name/number e.g. SPI1, or as "find in bank/mux" which must be
    # spec'd as "BM:Name" where B is bank (A-F), M is Mux (0-3)
    # EINT and PWM are grouped together, specially, but may still be spec'd
    # using "BM:Name".  Pins are removed in-order as listed from
    # lists (interfaces, EINTs, PWMs) from available pins.

    i_class = ['ULPI0/8', 'ULPI1', 'MMC', 'SD0', 'UART0',
               'TWI0', 'MSPI0', 'B3:SD1', ]
    i_class_eint = ['EINT_0', 'EINT_1', 'EINT_2', 'EINT_3', 'EINT_4']
    i_class_pwm = ['B2:PWM_0']
    descriptions = {
        'MMC': 'internal (on Card)',
        'SD0': 'user-facing: internal (on Card), multiplexed with JTAG\n'
        'and UART2, for debug purposes',
        'TWI2': 'I2C.\n',
        'E2:SD1': '',
        'MSPI1': '',
        'UART0': '',
        'B1:LCD/22': '18-bit RGB/TTL LCD',
        'ULPI0/8': 'user-facing: internal (on Card), USB-OTG ULPI PHY',
        'ULPI1': 'dual USB2 Host ULPI PHY'
    }

    ps.add_scenario("I-Class", i_class, i_class_eint, i_class_pwm,
                    descriptions)

    return ps
