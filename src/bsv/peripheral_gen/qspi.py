from bsv.peripheral_gen.nspi import nspi


class mqspi(nspi):
    def __init__(self, name):
        nspi.__init__(self, name, True)


class qspi(nspi):
    def __init__(self, name):
        nspi.__init__(self, name, False)
