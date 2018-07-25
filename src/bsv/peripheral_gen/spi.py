from bsv.peripheral_gen.nspi import nspi


class mspi(nspi):
    def __init__(self, name):
        nspi.__init__(self, name, True)


class spi(nspi):
    def __init__(self, name):
        nspi.__init__(self, name, False)
