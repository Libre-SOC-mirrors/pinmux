#!/usr/bin/env python

from interfaces import pins, i2s, emmc, sdmmc, spi, quadspi, i2c
from interfaces import jtag, uart, ulpi, uartfull, rgbttl, rgmii
from interfaces import flexbus1, flexbus2, sdram1, sdram2, mcu8080
from interfaces import eint, pwm, gpio
from interfaces import display, display_fns, check_functions
from interfaces import pinmerge, display_fixed

def pinspec():
    pinouts = {}

    pinbanks = {'A': 16,
                'B': 16,
                'C': 16,
                'D': 16,
                'E': 16,
                'F': 48,
                'G': 24,
              }
    bankspec = {}
    pkeys = pinbanks.keys()
    pkeys.sort()
    offs = 0
    for kn in pkeys:
        bankspec[kn] = offs
        offs += pinbanks[kn]

    # Bank A, 0-15
    pinmerge(pinouts, gpio(bankspec, "", ('A', 0), "A", 0, 16, 0))
    pinmerge(pinouts, spi(bankspec, "0", ('A', 0), "A", 1))
    pinmerge(pinouts, spi(bankspec, "1", ('A', 4), "A", 1))
    pinmerge(pinouts, uart(bankspec, "0", ('A', 8), "A", 1))
    pinmerge(pinouts, uart(bankspec, "1", ('A', 10), "A", 1))
    pinmerge(pinouts, i2c(bankspec, "0", ('A', 12), "A", 1))
    pinmerge(pinouts, i2c(bankspec, "1", ('A', 14), "A", 1))
    for i in range(16):
        pinmerge(pinouts, pwm(bankspec, str(i), ('A', i), "A", mux=2))

    # Bank B, 16-31
    pinmerge(pinouts, gpio(bankspec, "", ('B', 0), "B", 0, 16, 0))
    pinmerge(pinouts, spi(bankspec, "2", ('B', 0), "B", 1))
    pinmerge(pinouts, uart(bankspec, "2", ('B', 4), "B", 1))
    pinmerge(pinouts, uart(bankspec, "3", ('B', 6), "B", 1))
    pinmerge(pinouts, uart(bankspec, "4", ('B', 8), "B", 1))
    pinmerge(pinouts, i2c(bankspec, "2", ('B', 10), "B", 1))
    pinmerge(pinouts, i2c(bankspec, "3", ('B', 12), "B", 1))
    pinmerge(pinouts, uart(bankspec, "5", ('B', 14), "B", 1))
    for i in range(16):
        pinmerge(pinouts, pwm(bankspec, str(i+16), ('B', i), "B", mux=2))

    # Bank C, 32-47
    pinmerge(pinouts, gpio(bankspec, "", ('C', 0), "C", 0, 16, 0))
    pinmerge(pinouts, spi(bankspec, "1", ('C', 0), "C", 1))
    pinmerge(pinouts, spi(bankspec, "2", ('C', 4), "C", 1))
    pinmerge(pinouts, uart(bankspec, "2", ('C', 8), "C", 1))
    pinmerge(pinouts, uart(bankspec, "3", ('C', 10), "C", 1))
    pinmerge(pinouts, i2c(bankspec, "1", ('C', 12), "C", 1))
    pinmerge(pinouts, i2c(bankspec, "3", ('C', 14), "C", 1))

    # Bank D, 48-63
    pinmerge(pinouts, ulpi(bankspec, "0", ('D', 0), "D", 1))
    pinmerge(pinouts, spi(bankspec, "0", ('D', 12), "D", 1))

    # Bank E, 64-80
    pinmerge(pinouts, sdmmc(bankspec, "0", ('E', 0), "E", 1))
    pinmerge(pinouts, jtag(bankspec, "0", ('E', 6), "E", 1))
    pinmerge(pinouts, uart(bankspec, "0", ('E', 10), "E", 1))
    pinmerge(pinouts, i2c(bankspec, "0", ('E', 12), "E", 1))
    pinmerge(pinouts, uart(bankspec, "1", ('E', 14), "E", 1))

    # Bank F, 80-127
    flexspec = {
        'FB_TS': ('FB_ALE', 2, "F"),
        'FB_CS2': ('FB_BWE2', 2, "F"),
        'FB_A0': ('FB_BWE2', 3, "F"),
        'FB_CS3': ('FB_BWE3', 2, "F"),
        'FB_A1': ('FB_BWE3', 3, "F"),
        'FB_TBST': ('FB_OE', 2, "F"),
        'FB_TSIZ0': ('FB_BWE0', 2, "F"),
        'FB_TSIZ1': ('FB_BWE1', 2, "F"),
    }
    pinmerge(pinouts, flexbus1(bankspec, "", ('F', 0), "F", 1))
    pinmerge(pinouts, flexbus2(bankspec, "", ('F', 30), "F", 1, limit=8))

    # Bank G, 128-151

    pinmerge(pinouts, rgmii(bankspec, "", ('G', 0), "G", 1))

    print "# Pinouts (PinMux)"
    print
    print "auto-generated by [[pinouts.py]]"
    print
    print "[[!toc  ]]"
    print
    display(pinouts)
    print

    print "# Pinouts (Fixed function)"
    print

    fixedpins = {
      'CTRL_SYS':
        [
        'TEST', 'BOOT_SEL', 
        'NMI#', 'RESET#', 
        'CLK24M_IN', 'CLK24M_OUT', 
        'CLK32K_IN', 'CLK32K_OUT', 
        'PLLTEST', 'PLLREGIO', 'PLLVP25', 
        'PLLDV', 'PLLVREG', 'PLLGND', 
       ],

      'POWER_CPU':
        ['VDD0_CPU', 'VDD1_CPU', 'VDD2_CPU', 'VDD3_CPU', 'VDD4_CPU', 'VDD5_CPU',
         'GND0_CPU', 'GND1_CPU', 'GND2_CPU', 'GND3_CPU', 'GND4_CPU', 'GND5_CPU',
        ],

      'POWER_DLL':
        ['VDD0_DLL', 'VDD1_DLL', 'VDD2_DLL', 
         'GND0_DLL', 'GND1_DLL', 'GND2_DLL', 
        ],

      'POWER_INT':
        ['VDD0_INT', 'VDD1_INT', 'VDD2_INT', 'VDD3_INT', 'VDD4_INT', 
         'VDD5_INT', 'VDD6_INT', 'VDD7_INT', 'VDD8_INT', 'VDD9_INT', 
         'GND0_INT', 'GND1_INT', 'GND2_INT', 'GND3_INT', 'GND4_INT', 
         'GND5_INT', 'GND6_INT', 'GND7_INT', 'GND8_INT', 'GND9_INT', 
        ],

      'POWER_GPIO':
        ['VDD_GPIOA', 'VDD_GPIOB', 'VDD_GPIOC',
         'VDD_GPIOD', 'VDD_GPIOE', 'VDD_GPIOF',
         'VDD_GPIOG',
         'GND_GPIOA', 'GND_GPIOB', 'GND_GPIOC',
         'GND_GPIOD', 'GND_GPIOE', 'GND_GPIOF',
         'GND_GPIOG',
        ]

      }

    display_fixed(fixedpins, len(pinouts))

    print "# Functions (PinMux)"
    print
    print "auto-generated by [[pinouts.py]]"
    print

    function_names = {'EINT': 'External Interrupt',
                      'FB': 'MC68k FlexBus',
                      'IIS': 'I2S Audio',
                      'JTAG0': 'JTAG',
                      'JTAG1': 'JTAG (same as JTAG2, JTAG_SEL=LOW)',
                      'JTAG2': 'JTAG (same as JTAG1, JTAG_SEL=HIGH)',
                      'LCD': '24-pin RGB/TTL LCD',
                      'RG': 'RGMII Ethernet',
                      'MMC': 'eMMC 1/2/4/8 pin',
                      'PWM': 'PWM (pulse-width modulation)',
                      'SD0': 'SD/MMC 0',
                      'SD1': 'SD/MMC 1',
                      'SD2': 'SD/MMC 2',
                      'SD3': 'SD/MMC 3',
                      'SPI0': 'SPI (Serial Peripheral Interface) 0',
                      'SPI1': 'SPI (Serial Peripheral Interface) 1',
                      'SPI2': 'SPI (Serial Peripheral Interface) 2',
                      'SPI3': 'Quad SPI (Serial Peripheral Interface) 3',
                      'TWI0': 'I2C 0',
                      'TWI1': 'I2C 1',
                      'TWI2': 'I2C 2',
                      'TWI3': 'I2C 3',
                      'UART0': 'UART (TX/RX) 0',
                      'UART1': 'UART (TX/RX) 1',
                      'UART2': 'UART (TX/RX) 2',
                      'UART3': 'UART (TX/RX) 3',
                      'UART4': 'UART (TX/RX) 4',
                      'UART5': 'UART (TX/RX) 5',
                      'ULPI0': 'ULPI (USB Low Pin-count) 0',
                      'ULPI1': 'ULPI (USB Low Pin-count) 1',
                      'ULPI2': 'ULPI (USB Low Pin-count) 2',
                      'ULPI3': 'ULPI (USB Low Pin-count) 3',
                    }
            
    fns = display_fns(bankspec, pinouts, function_names)
    print

    # Scenarios below can be spec'd out as either "find first interface"
    # by name/number e.g. SPI1, or as "find in bank/mux" which must be
    # spec'd as "BM:Name" where B is bank (A-F), M is Mux (0-3)
    # EINT and PWM are grouped together, specially, but may still be spec'd
    # using "BM:Name".  Pins are removed in-order as listed from
    # lists (interfaces, EINTs, PWMs) from available pins.

    # Robotics scenario.  

    robotics = ['FB', 'RG', 'ULPI0/8', 
                'SD0',
                'JTAG0', 'E1:UART0', 
              'D1:SPI0', 'E1:TWI0']
    robotics_pwm = []
    for i in range(32):
        robotics_pwm.append('PWM_%d' % i)
    robotics_eint = ['EINT24', 'EINT25', 'EINT26', 'EINT27',
                       'EINT20', 'EINT21', 'EINT22', 'EINT23']
    robotics_eint = []

    unused_pins = check_functions("Robotics", bankspec, fns, pinouts,
                 robotics, robotics_eint, robotics_pwm)

    print "# Reference Datasheets"
    print
    print "datasheets and pinout links"
    print
    print "* <http://datasheets.chipdb.org/AMD/8018x/80186/amd-80186.pdf>"
    print "* <http://hands.com/~lkcl/eoma/shenzen/frida/FRD144A2701.pdf>"
    print "* <http://pinouts.ru/Memory/sdcard_pinout.shtml>"
    print "* p8 <http://www.onfi.org/~/media/onfi/specs/onfi_2_0_gold.pdf?la=en>"
    print "* <https://www.heyrick.co.uk/blog/files/datasheets/dm9000aep.pdf>"
    print "* <http://cache.freescale.com/files/microcontrollers/doc/app_note/AN4393.pdf>"
    print "* <https://www.nxp.com/docs/en/data-sheet/MCF54418.pdf>"
    print "* ULPI OTG PHY, ST <http://www.st.com/en/interfaces-and-transceivers/stulpi01a.html>"
    print "* ULPI OTG PHY, TI TUSB1210 <http://ti.com/product/TUSB1210/>"

    return pinouts, bankspec, fixedpins
