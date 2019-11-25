#!/usr/bin/env python
# aardonyx file
from spec.base import PinSpec

from spec.ifaceprint import display, display_fns, check_functions
from spec.ifaceprint import display_fixed


def pinspec():
    pinbanks = {
        'A': (16, 4),
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
                      }

    ps = PinSpec(pinbanks, fixedpins, function_names)

    ps.gpio("", ('A', 1), 0, 0, 1)
    ps.gpio("", ('A', 0), 0, 1, 1)
    ps.gpio("", ('A', 3), 0, 2, 1)
    ps.gpio("", ('A', 2), 0, 3, 1)
    ps.gpio("", ('A', 4), 0, 5, 2)
    ps.gpio("", ('A', 6), 0, 9, 1)

    ps.gpio("", ('A', 7), 0, 13, 1)
    ps.gpio("", ('A', 8), 0, 10, 1)
    ps.gpio("", ('A', 9), 0, 12, 1)
    ps.gpio("", ('A', 10), 0, 11, 1)

    ps.gpio("", ('A', 11), 0, 4, 1)
    ps.gpio("", ('A', 12), 0, 7, 2)
    ps.gpio("", ('A', 14), 0, 14, 2)





    ps.pwm("", ('A', 2), 2, 0, 1)
    ps.pwm("", ('A', 4), 2, 1, 3)
    ps.pwm("", ('A', 8), 2, 4, 1)
    ps.pwm("", ('A', 10), 2, 5, 1)
    #ps.pwm("", ('A', 13), 2, 5, 1)
    ps.mspi("2", ('A', 7), 1)
    ps.uart("1", ('A', 0), 1)
    ps.uart("3", ('A', 2), 1)

    #ps.mquadspi("1", ('B', 0), 0)

    # Scenarios below can be spec'd out as either "find first interface"
    # by name/number e.g. SPI1, or as "find in bank/mux" which must be
    # spec'd as "BM:Name" where B is bank (A-F), M is Mux (0-3)
    # EINT and PWM are grouped together, specially, but may still be spec'd
    # using "BM:Name".  Pins are removed in-order as listed from
    # lists (interfaces, EINTs, PWMs) from available pins.

    minitest = ['ULPI0/8', 'ULPI1', 'MMC', 'SD0', 'UART0',
                'TWI0', 'MSPI0', 'B3:SD1', ]
    minitest_eint = []
    minitest_pwm = ['B2:PWM_0']
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

    ps.add_scenario("MiniTest", minitest, minitest_eint, minitest_pwm,
                    descriptions)

    return ps
