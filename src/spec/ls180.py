#!/usr/bin/env python
# see https://bugs.libre-soc.org/show_bug.cgi?id=304

from spec.base import PinSpec
from parse import Parse
import json

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
                      'SYS': 'System Control',
                      'GPIO': 'GPIO',
                      'EINT': 'External Interrupt',
                      'PWM': 'PWM',
                      'JTAG': 'JTAG',
                      'TWI': 'I2C Master 1',
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
    ps.sys("", ('S', 1), 0, 0, 7)
    ps.vdd("", ('S', 8), 0, 4, 1)
    ps.i2c("", ('S', 9), 0, 0, 2)
    ps.mspi("0", ('S', 15), 0)
    ps.uart("0", ('S', 20), 0)
    ps.vss("", ('S', 22), 0, 5, 1)
    ps.gpio("", ('S', 23), 0, 0, 8)
    ps.vdd("", ('S', 31), 0, 5, 1)

    ps.vss("", ('W', 0), 0, 6, 1)
    ps.pwm("", ('W', 1), 0, 0, 2)
    ps.eint("", ('W', 3), 0, 0, 3)
    ps.mspi("1", ('W', 6), 0)
    ps.vdd("", ('W', 10), 0, 6, 1)
    ps.sdmmc("0", ('W', 11), 0)
    ps.vss("", ('W', 17), 0, 7, 1)
    ps.vdd("", ('W', 31), 0, 7, 1)
    #ps.mspi("0", ('W', 8), 0)
    #ps.mspi("1", ('W', 8), 0)

    #ps.mquadspi("1", ('S', 0), 0)

    print "ps clocks", ps.clocks

    # Scenarios below can be spec'd out as either "find first interface"
    # by name/number e.g. SPI1, or as "find in bank/mux" which must be
    # spec'd as "BM:Name" where B is bank (A-F), M is Mux (0-3)
    # EINT and PWM are grouped together, specially, but may still be spec'd
    # using "BM:Name".  Pins are removed in-order as listed from
    # lists (interfaces, EINTs, PWMs) from available pins.

    ls180 = ['SD0', 'UART0', 'GPIOS', 'GPIOE', 'JTAG', 'PWM', 'EINT',
             'VDD', 'VSS', 'SYS',
                'TWI', 'MSPI0', 'MSPI1', 'SDR']
    ls180_eint = []
    ls180_pwm = []#['B0:PWM_0']
    descriptions = {
        'SD0': 'user-facing: internal (on Card), multiplexed with JTAG\n'
        'and UART2, for debug purposes',
        'TWI': 'I2C.\n',
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

    ps.add_scenario("Libre-SOC 180nm", ls180, ls180_eint, ls180_pwm,
                    descriptions)

    return ps


# map pins to litex name conventions, primarily for use in coriolis2
def pinparse(pinspec):
    p = Parse(pinspec, verify=False)

    print p.muxed_cells
    print p.muxed_cells_bank

    ps = [''] * 32
    pn = [''] * 32
    pe = [''] * 32
    pw = [''] * 32
    pads = {'N': pn, 'S': ps, 'E': pe, 'W': pw}

    iopads = []

    for (padnum, name, _), bank in zip(p.muxed_cells, p.muxed_cells_bank):
        padnum = int(padnum)
        start = p.bankstart[bank]
        banknum = padnum - start
        print banknum, name, bank
        padbank = pads[bank]
        # VSS
        if name.startswith('vss'):
            #name = 'p_vssick_' + name[-1]
            #name = 'p_vsseck_0'
            #name = 'vss'
            name = ''
        # VDD
        elif name.startswith('vdd'):
            #name = 'p_vddick_' + name[-1]
            #name = 'p_vddeck_0'
            #name = 'vdd'
            name = ''
        # SYS
        elif name.startswith('sys'):
            if name == 'sys_clk':
                name = 'p_sys_clk_0'
            elif name == 'sys_rst':
                #name = 'p_sys_rst_1'
                iopads.append([name, name, name])
                padbank[banknum] = name
                print "sys_rst add", bank, banknum, name
                name = None
            elif name == 'sys_pllclk':
                name = None # ignore
            elif name == 'sys_pllout':
                name = 'sys_pll_48_o'
                iopads.append(['p_' + name, name, name])
            elif name.startswith('sys_csel'):
                i = name[-1]
                name2 = 'sys_clksel_i(%s)' % i
                name = 'p_sys_clksel_' + i
                iopads.append([name, name2, name2])
            #if name:
            #    iopads.append([pname, name, name])
            print "sys pad", name
        # SPI Card
        elif name.startswith('mspi0') or name.startswith('mspi1'):
            suffix = name[6:]
            if suffix == 'ck':
                suffix = 'clk'
            elif suffix == 'nss':
                suffix = 'cs_n'
            if name.startswith('mspi1'):
                prefix = 'spi_master_'
            else:
                prefix = 'spisdcard_'
            name = prefix + suffix
            iopads.append(['p_' + name, name, name])
        # SD/MMC
        elif name.startswith('sd0'):
            if name.startswith('sd0_d'):
                i = name[5:]
                name = 'sdcard_data' + i
                name2 = 'sdcard_data_%%s(%s)' % i
                pad = ['p_' + name, name, name2 % 'o', name2 % 'i',
                            'sdcard_data_oe']
                iopads.append(pad)
            elif name.startswith('sd0_cmd'):
                name = 'sdcard_cmd'
                name2 = 'sdcard_cmd_%s'
                pad = ['p_' + name, name, name2 % 'o', name2 % 'i', name2 % 'oe']
                iopads.append(pad)
            else:
                name = 'sdcard_' + name[4:]
                iopads.append(['p_' + name, name, name])
        # SDRAM
        elif name.startswith('sdr'):
            if name == 'sdr_clk':
                name = 'sdram_clock'
                iopads.append(['p_' + name, name, name])
            elif name.startswith('sdr_ad'):
                i = name[6:]
                name = 'sdram_a_' + i
                name2 = 'sdram_a(%s)' % i
                iopads.append(['p_' + name, name2, name2])
            elif name.startswith('sdr_ba'):
                i = name[-1]
                name = 'sdram_ba_' + i
                name2 = 'sdram_ba(%s)' % i
                iopads.append(['p_' + name, name2, name2])
            elif name.startswith('sdr_dqm'):
                i = name[-1]
                name = 'sdram_dm_' + i
                name2 = 'sdram_dm(%s)' % i
                iopads.append(['p_' + name, name2, name2])
            elif name.startswith('sdr_d'):
                i = name[5:]
                name = 'sdram_dq_' + i
                name2 = 'sdram_dq_%%s(%s)' % i
                pad = ['p_' + name, name, name2 % 'o', name2 % 'i', 'sdram_dq_oe']
                iopads.append(pad)
            elif name == 'sdr_csn0':
                name = 'sdram_cs_n'
                iopads.append(['p_' + name, name, name])
            elif name[-1] == 'n':
                name = 'sdram_' + name[4:-1] + '_n'
                iopads.append(['p_' + name, name, name])
            else:
                name = 'sdram_' + name[4:]
                iopads.append(['p_' + name, name, name])
        # UART
        elif name.startswith('uart'):
            name = 'uart_' + name[6:]
            iopads.append(['p_' + name, name, name])
        # GPIO
        elif name.startswith('gpio'):
            i = name[7:]
            name = 'gpio_' + i
            name2 = 'gpio_%%s(%s)' % i
            pad = ['p_' + name, name, name2 % 'o', name2 % 'i', name2 % 'oe']
            print ("GPIO pad", name, pad)
            iopads.append(pad)
        # I2C
        elif name.startswith('twi'):
            name = 'i2c' + name[3:]
            if name.startswith('i2c_sda'):
                name2 = 'i2c_sda_%s'
                pad = ['p_' + name, name, name2 % 'o', name2 % 'i', name2 % 'oe']
                print ("I2C pad", name, pad)
                iopads.append(pad)
            else:
                iopads.append(['p_' + name, name, name])
        # EINT
        elif name.startswith('eint'):
            i = name[-1]
            name = 'eint_%s' % i
            name2 = 'eint(%s)' % i
            pad = ['p_' + name, name2, name2]
            iopads.append(pad)
        # PWM
        elif name.startswith('pwm'):
            name = name[:-4]
            pad = ['p_' + name, name, name]
            iopads.append(pad)
        else:
            pad = ['p_' + name, name, name]
            iopads.append(pad)
            print ("GPIO pad", name, pad)
        if name and not name.startswith('p_'):
            name = 'p_' + name
        if name is not None:
            padbank[banknum] = name

    #pw[25] = 'p_sys_rst_1'
    pe[13] = 'p_vddeck_0'
    pe[23] = 'p_vsseck_0'
    pw[10] = 'p_vddick_0'
    pw[17] = 'p_vssick_0'

    nc_idx = 0
    for pl in [pe, pw, pn, ps]:
        for i in range(len(pl)):
            if pl[i] == '':
                pl[i] = 'nc_%d' % nc_idx
                nc_idx += 1

    print p.bankstart
    print pn
    print ps
    print pe
    print pw

    chip = {
             'pads.south'      : ps,
              'pads.east'       : pe,
              'pads.north'      : pn,
              'pads.west'       : pw,
              'pads.instances' : iopads
           }

    chip = json.dumps(chip)
    with open("ls180/litex_pinpads.json", "w") as f:
        f.write(chip)

