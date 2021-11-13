#!/usr/bin/env python
#from pinfunctions import i2s, lpc, emmc, sdmmc, mspi, mquadspi, spi, quadspi, i2c, mi2c, jtag, uart, uartfull, rgbttl, ulpi, rgmii, flexbus1, flexbus2, sdram1, sdram2, sdram3, vss, vdd, sys, eint, pwm, gpio

# File for stage 1 pinmux tested proposed by Luke, https://bugs.libre-soc.org/show_bug.cgi?id=50#c10

def dummy_pinset():
    # sigh this needs to come from pinmux.
    num_gpios = 16
    num_eint = 3
    num_pow3v3 = 10
    num_pow1v8 = 13

    gpios = []
    for i in range(num_gpios):
        gpios.append("%d*" % i)
    
    eint = []
    for i in range(num_eint):
        eint.append("%d-" % i)

    vdd3v3 = []
    vss3v3 = []
    vdd1v8 = []
    vss1v8 = []
    for i in range(num_pow3v3):
        vdd3v3.append("%d-" % i)
        vss3v3.append("%d-" % i)
    for i in range(num_pow1v8):
        vdd1v8.append("%d-" % i)
        vss1v8.append("%d-" % i)

    rgmii = ['erxd0-', 'erxd1-', 'erxd2-', 'erxd3-', 'etxd0+', 'etxd1+', 'etxd2+', 'etxd3+', 'erxck-', 'erxerr-', 'erxdv-', 'emdc+', 'emdio*', 'etxen+', 'etxck+', 'ecrs-', 'ecol+', 'etxerr+']
    ulpi = ['CK+', 'DIR+', 'STP+', 'NXT+', 'D0*', 'D1*', 'D2*', 'D3*', 'D4*', 'D5*', 'D6*', 'D7*']
    
    sdr = ['DQM0+', 'D0*', 'D1*', 'D2*', 'D3*', 'D4*', 'D5*', 'D6*', 'D7*', 'BA0+', 'BA1+', 'AD0+', 'AD1+', 'AD2+', 'AD3+', 'AD4+', 'AD5+', 'AD6+', 'AD7+', 'AD8+', 'AD9+', 'CLK+', 'CKE+', 'RASn+', 'CASn+', 'WEn+', 'CSn0+']
    return {'uart': ['tx+', 'rx-'],
            'gpio': gpios,
            'i2c': ['sda*', 'scl+'],
            'rg0': rgmii,
            'rg1': rgmii,
            'rg2': rgmii,
            'rg3': rgmii,
            'rg4': rgmii,
            'ulpi0': ulpi,
            'ulpi1': ulpi,
            'sdr': sdr,
            'jtag': ['TMS-', 'TDI-', 'TDO+', 'TCK+'],
            'vdd3v3': vdd3v3,
            'vss3v3': vss3v3,
            'vdd1v8': vdd1v8,
            'vss1v8': vss1v8,
            'sys': ['RST-', 'PLLCLK-', 'PLLSELA0-', 'PLLSELA1-', 'PLLTESTOUT+', 'PLLVCOUT+'],
            'mspi0': ['CK+', 'NSS+', 'MOSI+', 'MISO-'],
            'eint': eint,
            'qspi': ['CK+', 'NSS+', 'IO0*', 'IO1*', 'IO2*', 'IO3*'],
            'sd0': ['CMD*', 'CLK+', 'D0*', 'D1*', 'D2*', 'D3*'],
           }

# testing .....
resources = dummy_pinset()
print(resources)