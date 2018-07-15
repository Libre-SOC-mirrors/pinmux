# mux.py

from myhdl import *
from myhdl._block import _Block
from mux import mux4
from functools import wraps, partial
import inspect

period = 20  # clk frequency = 50 MHz


class IO(object):
    def __init__(self, typ, name):
        self.typ = typ
        self.name = name
        if typ == 'in' or typ == 'inout':
            self.inp = Signal(bool(0))
        if typ == 'out' or typ == 'inout':
            self.out = Signal(bool(0))
        if typ == 'inout':
            self.dirn = Signal(bool(0))


class Mux(object):
    def __init__(self, bwidth=2):
        self.sel = Signal(intbv(0)[bwidth:0])


def f(obj):
    print('attr =', obj.attr)


@classmethod
def cvt(self, *args, **kwargs):
    print('args', self, args, kwargs)
    return block(test2)(*self._args).convert(*args, **kwargs)


def Test(*args):
    Foo = type(
        'Foo',
        (block,),
        {
            'test2': test2,
            'convert': cvt,
            '_args': args
        }
    )
    return Foo(test2)


def create_test(fncls, npins=2, nfns=4):
    x = """\
from myhdl import block
@block
def test(testfn, clk, fncls, num_pins, num_fns, {0}):
    args = [{0}]
    return testfn(clk, fncls, num_pins, num_fns, args)
"""

    args = []
    for pnum in range(npins):
        args.append("sel%d" % pnum)
        args.append("pin%d" % pnum)
    #for pnum in range(nfns):
    #    args.append("fn%d" % pnum)
    args = ','.join(args)
    x = x.format(args)
    print x
    print repr(x)
    with open("testmod.py", "w") as f:
        f.write(x)
    x = "from testmod import test"
    code = compile(x, '<string>', 'exec')
    y = {}
    exec code in y
    x = y["test"]

    def fn(*args):
        return block(x)
    return x


def proxy(func):
    def wrapper(*args):
        return func(args[0], args[1], args[2], args[3])
    return wrapper

class FnCls(object):
    def __init__(self):
        self.attrs = ['uart', 'i2c', 'spi', 'gpio']

    def setfn(self, idx, fn):
        return setattr(self, self.attrs[idx], fn)

    def getfn(self, idx):
        return getattr(self, self.attrs[idx])

@block
def muxer(clk, p, ifaces, args):
    muxes = []
    pins = []
    fns = []
    for i in range(len(p.muxed_cells)):
        pins.append(args.pop(0))
        muxes.append(args.pop(0))
    kl = sorted(ifaces.keys())
    for i in range(len(p.myhdlifaces)):
        fns.append(args.pop(0))

    muxinst = []

    inputs = []
    for i in range(2):
        x = getattr(fns[i], fns[i].pnames[0])
        print x, dir(x)
        inputs.append(getattr(fns[i], fns[i].pnames[0]).out)
        inputs.append(getattr(fns[i], fns[i].pnames[0]).out)

    print "inputs", inputs

    for i in range(len(muxes)):
        mux = muxes[i]
        pin = pins[i]
        print "mux", mux
        print mux4
        inst = mux4(clk, inputs, mux.sel, pin.out)
        muxinst.append(inst)

    return muxinst


@block
def test2(clk, fncls, num_pins, num_fns, args):
    muxes = []
    pins = []
    for i in range(num_pins):
        muxes.append(args.pop(0))
        pins.append(args.pop(0))

    muxinst = []

    inputs = []
    inputs.append(fncls.uart.out)
    inputs.append(fncls.i2c.out)
    inputs.append(fncls.spi.out)
    inputs.append(fncls.gpio.out)
    #for i in range(4):
        #inputs.append(fncls.getfn(i).out)

    for i in range(len(muxes)):
        mux = muxes[i]
        pin = pins[i]
        inst = mux4(clk, inputs, mux.sel, pin.out)
        muxinst.append(inst)

    return muxinst


# testbench


@block
def mux_tb(fncls):

    muxvals = []
    muxes = []
    pins = []
    ins = []
    outs = []
    dirs = []
    args = []
    for i in range(2):
        m = Mux()
        muxes.append(m)
        muxvals.append(m.sel)
        args.append(m)
        pin = IO("inout", "name%d" % i)
        pins.append(pin)
        args.append(pin)
        ins.append(pin.inp)
        outs.append(pin.out)
        dirs.append(pin.dirn)
    fns = []
    clk = Signal(bool(0))

    mux_inst = test(test2, clk, fncls, 2, 4, *args)

    @instance
    def clk_signal():
        while True:
            clk.next = not clk
            yield delay(period // 2)

    @always(clk.posedge)
    def print_data():
        # print on screen
        # print.format is not supported in MyHDL 1.0
        for i in range(len(muxes)):
            sel = muxvals[i]
            out = outs[i]
            print ("%d: %s %s" % (i, sel, out))

    return instances()


class Deco(object):
    def __init__(self):
        self.calls = 0


def test_mux(fncls):

    muxvals = []
    muxes = []
    pins = []
    ins = []
    outs = []
    dirs = []
    fins = []
    fouts = []
    fdirs = []
    args = []
    for i in range(2):
        m = Mux()
        muxes.append(m)
        muxvals.append(m.sel)
        args.append(m)
        pin = IO("inout", "name%d" % i)
        pins.append(pin)
        args.append(pin)
        ins.append(pin.inp)
        outs.append(pin.out)
        dirs.append(pin.dirn)
    clk = Signal(bool(0))

    mux_inst = test(test2, clk, fncls, 2, 4, *args)
    mux_inst.convert(hdl="Verilog", initial_values=True, testbench=False)
    #mux_inst = Test(clk, muxes, pins, fns)
    #toVerilog(mux_inst, clk, muxes, pins, fns)
    #deco = Deco()
    #b = _Block(mux_inst, deco, "test", "test.py", 1, clk, muxes, pins, fns)
    #b.convert(hdl="Verilog", name="test", initial_values=True)
    #mux_inst.convert(hdl="Verilog", initial_values=True)
    #block(mux_inst).convert(hdl="Verilog", initial_values=True)

    # test bench
    tb = mux_tb(fncls)
    tb.convert(hdl="Verilog", initial_values=True, testbench=True)
    # keep following lines below the 'tb.convert' line
    # otherwise error will be reported
    tb.config_sim(trace=True)
    tb.run_sim(66 * period)  # run for 15 clock cycle


def muxgen(fn, p, ifaces):
    args = []
    for i in range(len(p.muxed_cells)):
        args.append(p.muxers[i])
        args.append(p.muxsel[i])
    for i in p.myhdlifaces:
        args.append(i)
    clk = Signal(bool(0))

    mux_inst = fn(muxer, clk, p, ifaces, *args)
    mux_inst.convert(hdl="Verilog", initial_values=True, testbench=False)




if __name__ == '__main__':
    fncls = FnCls()
    num_fns = 4
    for i in range(num_fns):
        fn = IO("inout", fncls.attrs[i])
        fncls.setfn(i, fn)
    test = create_test(fncls)
    test_mux(fncls)
