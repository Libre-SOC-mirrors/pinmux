#!/usr/bin/env python

""" define functions here, with their pin names and the pin type.

    each function returns a pair of lists
    (or objects with a __getitem__ function)

    the first list (or object) contains pin name plus type specifications.

    the type is:

    * "-" for an input pin,
    * "+" for an output pin,
    * "*" for an in/out pin

    each function is then added to the pinspec tuple, below, as a ("NAME",
    function) entry.

    different functions may be added multiple times under the same NAME,
    so that complex (or large) functions can be split into one or more
    groups (and placed on different pinbanks).

    eint, pwm and gpio are slightly odd in that instead of a fixed list
    an object is returned with a __getitem__ function that accepts a
    slice object.  in this way the actual generation of the pin name
    is delayed until it is known precisely how many pins are to be
    generated, and that's not known immediately (or it would be if
    every single one of the functions below had a start and end parameter
    added).  see spec.interfaces.PinGen class slice on pingroup

    the second list is the names of pins that are part of an inout bus.
    this list of pins (a ganged group) will need to be changed under
    the control of the function, as a group.  for example: sdmmc's
    D0-D3 pins are in-out, they all change from input to output at
    the same time under the control of the function, therefore there's
    no point having multiple in-out switch/control wires, as the
    sdmmc is never going to do anything other than switch this entire
    bank all at once.  so in this particular example, sdmmc returns:

    (['CMD+', 'CLK+', 'D0*', 'D1*', 'D2*', 'D3*'] # pin names
     ['D0*', 'D1*', 'D2*', 'D3*'])                # ganged bus names

    addition:

    3rd item in list gives the name of the clock.
"""


def i2s(suffix, bank):
    return (['MCK+', 'BCK+', 'LRCK+', 'DI-', 'DO+'],
            [], "MCK")


# XXX TODO: correct these.  this is a stub for now
# https://bugs.libre-soc.org/show_bug.cgi?id=303
def lpc(suffix, bank, pincount=4):
    lpcpins = ['CMD*', 'CLK+']
    inout = []
    for i in range(pincount):
        pname = "D%d*" % i
        lpcpins.append(pname)
        inout.append(pname)
    return (lpcpins, inout, 'CLK')


def emmc(suffix, bank, pincount=8):
    emmcpins = ['CMD*', 'CLK+']
    inout = []
    for i in range(pincount):
        pname = "D%d*" % i
        emmcpins.append(pname)
        inout.append(pname)
    return (emmcpins, inout, 'CLK')


def sdmmc(suffix, bank):
    return emmc(suffix, bank, pincount=4)


def nspi(suffix, bank, iosize, masteronly=True):
    if masteronly:
        qpins = ['CK+', 'NSS+']
    else:
        qpins = ['CK*', 'NSS*']
    inout = []
    if iosize == 2:
        qpins += ['MOSI+', 'MISO-']
    else:
        for i in range(iosize):
            pname = "IO%d*" % i
            qpins.append(pname)
            inout.append(pname)
    return (qpins, inout, 'CK')


def mspi(suffix, bank):
    return nspi(suffix, bank, 2, masteronly=True)


def mquadspi(suffix, bank):
    return nspi(suffix, bank, 4, masteronly=True)


def spi(suffix, bank):
    return nspi(suffix, bank, 2)


def quadspi(suffix, bank):
    return nspi(suffix, bank, 4)


def i2c(suffix, bank):
    """bi-directional (reversible, master-slave) I2C
    """
    return (['SDA*', 'SCL*'], [], 'SCL')


def mi2c(suffix, bank):
    """master-only I2C (clock is output only)
    """
    return (['SDA*', 'SCL+'], [], 'SCL')


def jtag(suffix, bank):
    return (['TMS-', 'TDI-', 'TDO+', 'TCK+'], [], 'TCK')


def uart(suffix, bank):
    return (['TX+', 'RX-'], [], None)


def ulpi(suffix, bank):
    ulpipins = ['CK+', 'DIR+', 'STP+', 'NXT+']
    for i in range(8):
        ulpipins.append('D%d*' % i)
    return (ulpipins, [], 'CK')


def uartfull(suffix, bank):
    return (['TX+', 'RX-', 'CTS-', 'RTS+'], [], None)


def rgbttl(suffix, bank):
    ttlpins = ['CK+', 'DE+', 'HS+', 'VS+']
    for i in range(24):
        ttlpins.append("OUT%d+" % i)
    return (ttlpins, [], 'CK')


def rgmii(suffix, bank):
    buspins = []
    for i in range(4):
        buspins.append("ERXD%d-" % i)
    buspins += ['ERXCK-', 'ERXERR-']
    for i in range(4):
        buspins.append("ETXD%d+" % i)
    buspins += ['ETXCK-', 'ETXERR-',
                'ETXEN+', 'ERXDV-',
                'EMDC+', 'EMDIO*',
                'ECRS-', 'ECOL+']
    return (buspins, [], ['ERXCK', 'ETXCK'])


def flexbus1(suffix, bank):
    buspins = []
    inout = []
    for i in range(8):
        pname = "AD%d*" % i
        buspins.append(pname)
        inout.append(pname)
    for i in range(2):
        buspins.append("CS%d+" % i)
    buspins += ['ALE+', 'OE+', 'RW+', 'TA-',
                # 'TS+',  commented out for now, mirrors ALE, for mux'd mode
                'TBST+',
                'TSIZ0+', 'TSIZ1+']
    for i in range(4):
        buspins.append("BWE%d+" % i)
    for i in range(2, 6):
        buspins.append("CS%d+" % i)
    return (buspins, inout, None)


def flexbus2(suffix, bank):
    buspins = []
    for i in range(8, 32):
        buspins.append("AD%d*" % i)
    return (buspins, buspins, None)


def sdram1(suffix, bank, n_adr=10):
    buspins = []
    inout = []
    for i in range(1):
        pname = "DQM%d+" % i
        buspins.append(pname)
    for i in range(8):
        pname = "D%d*" % i
        buspins.append(pname)
        inout.append(pname)
    for i in range(2):
        buspins.append("BA%d+" % i)
    for i in range(n_adr):
        buspins.append("AD%d+" % i)
    buspins += ['CLK+', 'CKE+', 'RASn+', 'CASn+', 'WEn+',
                'CSn0+']
    return (buspins, inout, 'CLK')


def sdram2(suffix, bank):
    buspins = []
    inout = []
    for i in range(10, 13):
        buspins.append("AD%d+" % i)
    for i in range(1, 2):
        pname = "DQM%d+" % i
        buspins.append(pname)
    for i in range(8, 16):
        pname = "D%d*" % i
        buspins.append(pname)
        inout.append(pname)
    return (buspins, inout, None)


def sdram3(suffix, bank):
    buspins = []
    inout = []
    for i in range(1, 6):
        buspins.append("CSn%d+" % i)
    for i in range(13, 14):
        buspins.append("AD%d+" % i)
    for i in range(1, 4):
        pname = "DQM%d+" % i
    for i in range(8, 32):
        pname = "D%d*" % i
        buspins.append(pname)
        inout.append(pname)
    return (buspins, inout, None)


def mcu8080(suffix, bank):
    buspins = []
    inout = []
    for i in range(8):
        pname = "D%d*" % i
        buspins.append(pname)
        inout.append(pname)
    for i in range(8):
        buspins.append("AD%d+" % (i + 8))
    for i in range(6):
        buspins.append("CS%d+" % i)
    for i in range(2):
        buspins.append("NRB%d+" % i)
    buspins += ['CD+', 'RD+', 'WR+', 'CLE+', 'ALE+',
                'RST+']
    return (buspins, inout, None)


class RangePin(object):
    def __init__(self, suffix, prefix=None):
        self.suffix = suffix
        self.prefix = prefix or ''

    def __getitem__(self, s):
        res = []
        for idx in range(s.start or 0, s.stop or -1, s.step or 1):
            res.append("%s%d%s" % (self.prefix, idx, self.suffix))
        return res


def eint(suffix, bank):
    return (RangePin("-"), [], None)


def pwm(suffix, bank):
    return (RangePin("+"), [], None)


def gpio(suffix, bank):
    return (("GPIO%s" % bank, RangePin(prefix=bank, suffix="*")), [], None)

def vss(suffix, bank):
    return (RangePin("-"), [], None)

def vdd(suffix, bank):
    return (RangePin("-"), [], None)

def sys(suffix, bank):
    return (['RST-',                       # reset line
             'PLLCLK-',                       # incoming clock (to PLL)
             'PLLSELA0-', 'PLLSELA1-',     # PLL divider-selector
             'PLLTESTOUT+',                # divided-output (for testing)
             'PLLVCOUT+',                  # PLL VCO analog out (for testing)
             ], [], 'CLK')

# list functions by name here

pinspec = (('IIS', i2s),
           ('LPC', lpc),
           ('EMMC', emmc),
           ('SD', sdmmc),
           ('MSPI', mspi),
           ('MQSPI', mquadspi),
           ('SPI', spi),
           ('QSPI', quadspi),
           ('TWI', i2c),
           ('MTWI', mi2c),
           ('JTAG', jtag),
           ('UART', uart),
           ('QUART', uartfull),
           ('LCD', rgbttl),
           ('ULPI', ulpi),
           ('RG', rgmii),
           ('FB', flexbus1),
           ('FB', flexbus2),
           ('SDR', sdram1),
           ('SDR', sdram2),
           ('SDR', sdram3),
           ('VSS', vss),
           ('VDD', vdd),
           ('SYS', sys),
           ('EINT', eint),
           ('PWM', pwm),
           ('GPIO', gpio),
           )
