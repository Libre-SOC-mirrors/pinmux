#!/usr/bin/env python
# see https://bugs.libre-soc.org/show_bug.cgi?id=303

from spec.base import PinSpec

from spec.ifaceprint import display, display_fns, check_functions
from spec.ifaceprint import display_fixed


def pinspec():
    pinbanks = {
        'A': (16, 4),
        'B': (16, 4),
        'C': (16, 4),
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
    function_names = {
                      'PWM': 'PWM (pulse-width modulation)',
                      'MSPI2': 'SPI (Serial Peripheral Interface) Master 1',
                      'UART1': 'UART (TX/RX) 1',
                      'UART3': 'UART (TX/RX) 2',
                      'MMC1': 'SD/MMC 1',
                      'MMC2': 'SD/MMC 2',
                      'LPC1': 'Low Pincount Interface 1',
                      'LPC2': 'Low Pincount Interface 2',
                      }

    ps = PinSpec(pinbanks, fixedpins, function_names)

    ps.gpio("", ('A', 0), 0, 0, 16)

    ps.pwm("", ('B', 0), 0, 0, 2)
    ps.eint("", ('B', 2), 0, 0, 6)
    ps.mspi("2", ('B', 8), 0)
    ps.uart("1", ('B', 12), 0)
    ps.uart("3", ('B', 14), 0)
    ps.i2c("1", ('C', 0), 0)
    ps.i2c("2", ('C', 2), 0)
    ps.lpc("1", ('C', 4), 0)
    ps.lpc("2", ('C', 10), 1)

    #ps.mquadspi("1", ('B', 0), 0)

    # Scenarios below can be spec'd out as either "find first interface"
    # by name/number e.g. SPI1, or as "find in bank/mux" which must be
    # spec'd as "BM:Name" where B is bank (A-F), M is Mux (0-3)
    # EINT and PWM are grouped together, specially, but may still be spec'd
    # using "BM:Name".  Pins are removed in-order as listed from
    # lists (interfaces, EINTs, PWMs) from available pins.

    ls180 = ['ULPI0/8', 'ULPI1', 'MMC1', 'MMC2', 'SD0', 'UART0', 'LPC1',
                'LPC2',
                'TWI0', 'MSPI0', 'B3:SD1', ]
    ls180_eint = []
    ls180_pwm = []#['B0:PWM_0']
    descriptions = {
        'MMC': 'internal (on Card)',
        'SD0': 'user-facing: internal (on Card), multiplexed with JTAG\n'
        'and UART2, for debug purposes',
        'TWI2': 'I2C.\n',
        'E2:SD1': '',
        'MSPI1': '',
        'UART0': '',
        'LPC1': '',
        'LPC2': '',
        'MMC0': '',
        'B1:LCD/22': '18-bit RGB/TTL LCD',
        'ULPI0/8': 'user-facing: internal (on Card), USB-OTG ULPI PHY',
        'ULPI1': 'dual USB2 Host ULPI PHY'
    }

    ps.add_scenario("Libre-SOC 180nm", ls180, ls180_eint, ls180_pwm,
                    descriptions)

    return ps
