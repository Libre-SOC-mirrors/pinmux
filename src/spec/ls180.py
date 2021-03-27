#!/usr/bin/env python
# see https://bugs.libre-soc.org/show_bug.cgi?id=304

from spec.base import PinSpec
from parse import Parse
import json

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

    ps.vss("E", ('N', 0), 0, 0, 1)
    ps.vdd("E", ('N', 1), 0, 0, 1)
    ps.sdram1("", ('N', 2), 0, 0, 30)
    ps.vss("I", ('N', 30), 0, 0, 1)
    ps.vdd("I", ('N', 31), 0, 0, 1)

    ps.vss("E", ('E', 0), 0, 1, 1)
    ps.vdd("E", ('E', 1), 0, 1, 1)
    ps.sdram2("", ('E', 2), 0, 0, 12)
    ps.vss("I", ('E', 14), 0, 1, 1)
    ps.vdd("I", ('E', 15), 0, 1, 1)
    ps.gpio("", ('E', 16), 0, 8, 8)
    ps.jtag("", ('E', 25), 0, 0, 4)

    ps.vss("I", ('S', 0), 0, 2, 1)
    ps.vdd("I", ('S', 1), 0, 2, 1)
    ps.mi2c("", ('S', 2), 0, 0, 2)
    ps.mspi("0", ('S', 8), 0)
    ps.uart("0", ('S', 13), 0)
    ps.gpio("", ('S', 15), 0, 0, 8)
    ps.sys("", ('S', 23), 0, 0, 7)
    ps.vss("I", ('S', 30), 0, 3, 1)
    ps.vdd("I", ('S', 31), 0, 3, 1)

    ps.vss("E", ('W', 0), 0, 2, 1)
    ps.vdd("E", ('W', 1), 0, 2, 1)
    #ps.pwm("", ('W', 2), 0, 0, 2)  comment out (litex problem 25mar2021)
    ps.eint("", ('W', 4), 0, 0, 3)
    #ps.mspi("1", ('W', 7), 0)       comment out (litex problem 25mar2021)
    ps.sdmmc("0", ('W', 11), 0)     # comment out (litex problem 25mar2021)
    ps.vss("I", ('W', 30), 0, 4, 1)
    ps.vdd("I", ('W', 31), 0, 4, 1)

    #ps.mquadspi("1", ('S', 0), 0)

    print "ps clocks", ps.clocks

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

    ps.add_scenario("Libre-SOC 180nm", ls180, ls180_eint, ls180_pwm,
                    descriptions)

    return ps


# map pins to litex name conventions, primarily for use in coriolis2
# yes this is a mess.  it'll do the job though.  improvements later
def pinparse(psp, pinspec):
    p = Parse(pinspec, verify=False)
    pinmap = {}

    print p.muxed_cells
    print p.muxed_cells_bank

    ps = [''] * 32
    pn = [''] * 32
    pe = [''] * 32
    pw = [''] * 32
    pads = {'N': pn, 'S': ps, 'E': pe, 'W': pw}

    iopads = []
    domains = {}
    clocks = {}

    n_intpower = 0
    n_extpower = 0
    for (padnum, name, x), bank in zip(p.muxed_cells, p.muxed_cells_bank):
        orig_name = name
        domain = None # TODO, get this from the PinSpec.  sigh
        padnum = int(padnum)
        start = p.bankstart[bank]
        banknum = padnum - start
        print "bank", bank, banknum, "padname", name, padnum, x
        padbank = pads[bank]
        pad = None
        # VSS
        if name.startswith('vss'):
            name = 'p_%s_' % name[:-2] + name[-1]
            if 'i' in name:
                name = 'ground_' + name[-1]
                name2 = 'vss'
            else:
                name = 'ioground_' + name[-1]
                name2 = 'iovss'
            pad = [name, name2]
        # VDD
        elif name.startswith('vdd'):
            if 'i' in name:
                n_intpower += 1
                name = 'power_' + name[-1]
                name2 = 'vdd'
            else:
                n_extpower += 1
                name = 'iopower_' + name[-1]
                name2 = 'iovdd'
            pad = [name, name2]
        # SYS
        elif name.startswith('sys'):
            domain = 'SYS'
            if name == 'sys_clk':
                pad = ["p_"+name, name, name]
            elif name == 'sys_rst':
                #name = 'p_sys_rst_1'
                pad = [name, name, name]
                padbank[banknum] = name
                print "sys_rst add", bank, banknum, name
                name = None
            elif name == 'sys_pllclk':
                name = None # ignore
            elif name == 'sys_pllock':
                name = 'sys_pll_lck_o'
                pad = ['p_' + name, name, name]
            elif name == 'sys_pllout':
                name = 'sys_pll_18_o'
                pad = ['p_' + name, name, name]
            elif name.startswith('sys_csel'):
                i = name[-1]
                name2 = 'sys_clksel_i(%s)' % i
                name = 'p_sys_clksel_' + i
                pad = [name, name2, name2]
            #if name:
            #    iopads.append([pname, name, name])
            print "sys pad", name
        # SPI Card
        elif name.startswith('mspi0') or name.startswith('mspi1'):
            domain = 'MSPI'
            suffix = name[6:]
            if suffix == 'ck':
                suffix = 'clk'
            elif suffix == 'nss':
                suffix = 'cs_n'
            if name.startswith('mspi0'):
                prefix = 'spimaster_'
            else:
                prefix = 'spisdcard_'
            name = prefix + suffix
            pad = ['p_' + name, name, name]
        # SD/MMC
        elif name.startswith('sd0'):
            domain = 'SD'
            if name.startswith('sd0_d'):
                i = name[5:]
                name = 'sdcard_data' + i
                name2 = 'sdcard_data_%%s(%s)' % i
                pad = ['p_' + name, name, name2 % 'o', name2 % 'i',
                            'sdcard_data_oe']
            elif name.startswith('sd0_cmd'):
                name = 'sdcard_cmd'
                name2 = 'sdcard_cmd_%s'
                pad = ['p_'+name, name, name2 % 'o', name2 % 'i', name2 % 'oe']
            else:
                name = 'sdcard_' + name[4:]
                pad = ['p_' + name, name, name]
        # SDRAM
        elif name.startswith('sdr'):
            domain = 'SDR'
            if name == 'sdr_clk':
                name = 'sdram_clock'
                pad = ['p_' + name, name, name]
            elif name.startswith('sdr_ad'):
                i = name[6:]
                name = 'sdram_a_' + i
                name2 = 'sdram_a(%s)' % i
                pad = ['p_' + name, name2, name2]
            elif name.startswith('sdr_ba'):
                i = name[-1]
                name = 'sdram_ba_' + i
                name2 = 'sdram_ba(%s)' % i
                pad = ['p_' + name, name2, name2]
            elif name.startswith('sdr_dqm'):
                i = name[-1]
                name = 'sdram_dm_' + i
                name2 = 'sdram_dm(%s)' % i
                pad = ['p_' + name, name2, name2]
            elif name.startswith('sdr_d'):
                i = name[5:]
                name = 'sdram_dq_' + i
                name2 = 'sdram_dq_%%s(%s)' % i
                pad = ['p_'+name, name, name2 % 'o', name2 % 'i', 'sdram_dq_oe']
            elif name == 'sdr_csn0':
                name = 'sdram_cs_n'
                pad = ['p_' + name, name, name]
            elif name[-1] == 'n':
                name = 'sdram_' + name[4:-1] + '_n'
                pad = ['p_' + name, name, name]
            else:
                name = 'sdram_' + name[4:]
                pad = ['p_' + name, name, name]
        # UART
        elif name.startswith('uart'):
            domain = 'UART'
            name = 'uart_' + name[6:]
            pad = ['p_' + name, name, name]
        # GPIO
        elif name.startswith('gpio'):
            domain = 'GPIO'
            i = name[7:]
            name = 'gpio_' + i
            name2 = 'gpio_%%s(%s)' % i
            pad = ['p_' + name, name, name2 % 'o', name2 % 'i', name2 % 'oe']
            print ("GPIO pad", name, pad)
        # I2C master-only
        elif name.startswith('mtwi'):
            domain = 'MTWI'
            name = 'i2c' + name[4:]
            if name.startswith('i2c_sda'):
                name2 = 'i2c_sda_%s'
                pad = ['p_'+name, name, name2 % 'o', name2 % 'i', name2 % 'oe']
                print ("I2C pad", name, pad)
            else:
                pad = ['p_' + name, name, name]
        # I2C bi-directional
        elif name.startswith('twi'):
            domain = 'TWI'
            name = 'i2c' + name[3:]
            name2 = name + '_%s'
            pad = ['p_'+name, name, name2 % 'o', name2 % 'i', name2 % 'oe']
            print ("I2C pad", name, pad)
        # EINT
        elif name.startswith('eint'):
            domain = 'EINT'
            i = name[-1]
            name = 'eint_%s' % i
            name2 = 'eint_%s' % i
            pad = ['p_' + name, name2, name2]
        # PWM
        elif name.startswith('pwm'):
            domain = 'PWM'
            name = name[:-4]
            i = name[3:]
            name2 = 'pwm(%s)' % i
            pad = ['p_' + name, name2, name2]
        else:
            pad = ['p_' + name, name, name]
            print ("GPIO pad", name, pad)

        # JTAG domain
        if name and name.startswith('jtag'):
            domain = 'JTAG'

        if name and not name.startswith('p_'):
            if 'power' not in name and 'ground' not in name:
                name = 'p_' + name
        if name is not None:
            padbank[banknum] = name
            # create domains
            if domain is not None:
                if domain not in domains:
                    domains[domain] = []
                domains[domain].append(name)
                dl = domain.lower()
                if domain in psp.clocks and orig_name.startswith(dl):
                    clk = psp.clocks[domain]
                    if clk.lower() in orig_name: # TODO, might over-match
                        clocks[domain] = name
            # record remap
            pinmap[orig_name] = name

        # add pad to iopads
        if domain and pad is not None:
            # append direction from spec/domain.  damn awkward processing
            # to find it.
            fn, name = orig_name.split("_")
            if domain == 'PWM':
                name = fn[3:]
            print psp.byspec
            spec = None
            for k in psp.byspec.keys():
                if k.startswith(domain):
                    spec = psp.byspec[k]
            print "spec found", domain, spec
            assert spec is not None
            found = None
            for pname in spec:
                if pname.lower().startswith(name):
                    found = pname
            print "found spec", found
            assert found is not None
            # whewwww.  add the direction onto the pad spec list
            pad.append(found[-1])
            iopads.append(pad)
        elif pad is not None:
            iopads.append(pad)

    # not connected
    nc_idx = 0
    for pl in [pe, pw, pn, ps]:
        for i in range(len(pl)):
            if pl[i] == '':
                name = 'nc_%d' % nc_idx
                name2 = 'nc(%d)' % nc_idx
                pl[i] = name
                pinmap[name] = name
                iopads.append([name, name2, name2, "-"])
                nc_idx += 1

    print p.bankstart
    pprint(psp.clocks)

    print
    print "N pads", pn
    print "S pads", ps
    print "E pads", pe
    print "W pads", pw

    # do not want these
    del clocks['SYS']
    del domains['SYS']

    print "chip domains (excluding sys-default)"
    pprint(domains)
    print "chip clocks (excluding sys-default)"
    pprint(clocks)
    print "pin spec"
    pprint(psp.byspec)

    chip = {
             'pads.south'      : ps,
              'pads.east'       : pe,
              'pads.north'      : pn,
              'pads.west'       : pw,
              'pads.instances' : iopads,
              'pins.specs' : psp.byspec,
              'pins.map' : pinmap,
              'chip.domains' : domains,
              'chip.clocks' : clocks,
              'chip.n_intpower': n_intpower,
              'chip.n_extpower': n_extpower,
           }

    chip = json.dumps(chip)
    with open("ls180/litex_pinpads.json", "w") as f:
        f.write(chip)

    return pinmap
