# ================================== Steps to add peripherals ============
# Step-1:   create interface declaration for the peripheral to be added.
#           Remember these are interfaces defined for the pinmux and hence
#           will be opposite to those defined at the peripheral.
#           For eg. the output TX from the UART will be input (method Action)
#           for the pinmux.
#           These changes will have to be done in interface_decl.py
# Step-2    define the wires that will be required to transfer data from the
#           peripheral interface to the IO cell and vice-versa. Create a
#           mkDWire for each input/output between the peripheral and the
#           pinmux. Also create an implicit wire of GenericIOType for each cell
#           that can be connected to a each bit from the peripheral.
#           These changes will have to be done in wire_def.py
# Step-3:   create the definitions for each of the methods defined above.
#           These changes will have to be done in interface_decl.py
# ========================================================================

# default module imports
import shutil
import os
import os.path
import time

# project module imports
from bsv.interface_decl import Interfaces, mux_interface, io_interface
from parse import Parse
from bsv.actual_pinmux import init
from bsv.bus_transactors import axi4_lite

copyright = '''
/*
   This BSV file has been generated by the PinMux tool available at:
   https://bitbucket.org/casl/pinmux.

   Authors: Neel Gala, Luke
   Date of generation: ''' + time.strftime("%c") + '''
*/
'''
header = copyright + '''
package pinmux;

'''
footer = '''
   endmodule
endpackage
'''


def pinmuxgen(pth=None, verify=True):
    """ populating the file with the code
    """

    p = Parse(pth, verify)
    iocells = Interfaces()
    iocells.ifaceadd('io', p.N_IO, io_interface, 0)
    ifaces = Interfaces(pth)
    #ifaces.ifaceadd('io', p.N_IO, io_interface, 0)
    init(p, ifaces)

    bp = 'bsv_src'
    if pth:
        bp = os.path.join(pth, bp)
    if not os.path.exists(bp):
        os.makedirs(bp)
    bl = os.path.join(bp, 'bsv_lib')
    if not os.path.exists(bl):
        os.makedirs(bl)

    cwd = os.path.split(__file__)[0]

    # copy over template and library files
    shutil.copyfile(os.path.join(cwd, 'Makefile.template'),
                    os.path.join(bp, 'Makefile'))
    cwd = os.path.join(cwd, 'bsv_lib')
    for fname in ['AXI4_Lite_Types.bsv', 'Semi_FIFOF.bsv',
                  'gpio.bsv', 'mux.bsv']:
        shutil.copyfile(os.path.join(cwd, fname),
                        os.path.join(bl, fname))

    bus = os.path.join(bp, 'busenable.bsv')
    pmp = os.path.join(bp, 'pinmux.bsv')
    ptp = os.path.join(bp, 'PinTop.bsv')
    bvp = os.path.join(bp, 'bus.bsv')
    idef = os.path.join(bp, 'instance_defines.bsv')
    slow = os.path.join(bp, 'slow_peripherals.bsv')
    slowt = os.path.join(cwd, 'slow_peripherals_template.bsv')

    write_pmp(pmp, p, ifaces, iocells)
    write_ptp(ptp, p, ifaces)
    write_bvp(bvp, p, ifaces)
    write_bus(bus, p, ifaces)
    write_instances(idef, p, ifaces)
    write_slow(slow, slowt, p, ifaces)


def write_slow(slow, template, p, ifaces):
    """ write out the slow_peripherals.bsv file.
        joins all the peripherals together into one AXI Lite interface
    """
    with open(template) as bsv_file:
        template = bsv_file.read()
    imports = ifaces.slowimport()
    ifdecl = ifaces.slowifdecl()
    regdef = ifaces.axi_reg_def()
    slavedecl = ifaces.axi_slave_idx()
    fnaddrmap = ifaces.axi_addr_map()
    mkslow = ifaces.mkslow_periph()
    with open(slow, "w") as bsv_file:
        bsv_file.write(template.format(imports, ifdecl, regdef, slavedecl,
                                       fnaddrmap, mkslow))


def write_bus(bus, p, ifaces):
    # package and interface declaration followed by
    # the generic io_cell definition
    with open(bus, "w") as bsv_file:
        ifaces.busfmt(bsv_file)


def write_pmp(pmp, p, ifaces, iocells):
    # package and interface declaration followed by
    # the generic io_cell definition
    with open(pmp, "w") as bsv_file:
        bsv_file.write(header)

        cell_bit_width = 'Bit#(%d)' % p.cell_bitwidth
        bsv_file.write('''\
   interface MuxSelectionLines;

      // declare the method which will capture the user pin-mux
      // selection values.The width of the input is dependent on the number
      // of muxes happening per IO. For now we have a generalized width
      // where each IO will have the same number of muxes.''')

        for cell in p.muxed_cells:
            bsv_file.write(mux_interface.ifacefmt(cell[0], cell_bit_width))

        bsv_file.write("\n      endinterface\n")

        bsv_file.write('''

      interface IOCellSide;
      // declare the interface to the IO cells.
      // Each IO cell will have 1 input field (output from pin mux)
      // and an output and out-enable field (input to pinmux)''')

        # == create method definitions for all iocell interfaces ==#
        iocells.ifacefmt(bsv_file)

        # ===== finish interface definition and start module definition=======
        bsv_file.write("\n      endinterface\n")

        # ===== io cell definition =======
        bsv_file.write('''

      interface PeripheralSide;
      // declare the interface to the peripherals
      // Each peripheral's function will be either an input, output
      // or be bi-directional.  an input field will be an output from the
      // peripheral and an output field will be an input to the peripheral.
      // Bi-directional functions also have an output-enable (which
      // again comes *in* from the peripheral)''')
        # ==============================================================

        # == create method definitions for all peripheral interfaces ==#
        ifaces.ifacefmt(bsv_file)
        bsv_file.write("\n      endinterface\n")

        # ===== finish interface definition and start module definition=======
        bsv_file.write('''

   interface Ifc_pinmux;
      // this interface controls how each IO cell is routed.  setting
      // any given IO cell's mux control value will result in redirection
      // of not just the input or output to different peripheral functions
      // but also the *direction* control - if appropriate - as well.
      interface MuxSelectionLines mux_lines;

      // this interface contains the inputs, outputs and direction-control
      // lines for all peripherals.  GPIO is considered to also be just
      // a peripheral because it also has in, out and direction-control.
      interface PeripheralSide peripheral_side;

      // this interface is to be linked to the individual IO cells.
      // if looking at a "non-muxed" GPIO design, basically the
      // IO cell input, output and direction-control wires are cut
      // (giving six pairs of dangling wires, named left and right)
      // these iocells are routed in their place on one side ("left")
      // and the matching *GPIO* peripheral interfaces in/out/dir
      // connect to the OTHER side ("right").  the result is that
      // the muxer settings end up controlling the routing of where
      // the I/O from the IOcell actually goes.
      interface IOCellSide iocell_side;
   endinterface
   (*synthesize*)
   module mkpinmux(Ifc_pinmux);
''')
        # ====================================================================

        # ======================= create wire and registers =================#
        bsv_file.write('''
      // the followins wires capture the pin-mux selection
      // values for each mux assigned to a CELL
''')
        for cell in p.muxed_cells:
            bsv_file.write(mux_interface.wirefmt(
                cell[0], cell_bit_width))

        iocells.wirefmt(bsv_file)
        ifaces.wirefmt(bsv_file)

        bsv_file.write("\n")
        # ====================================================================
        # ========================= Actual pinmuxing ========================#
        bsv_file.write('''
      /*====== This where the muxing starts for each io-cell======*/
      Wire#(Bit#(1)) val0<-mkDWire(0); // need a zero
''')
        bsv_file.write(p.pinmux)
        bsv_file.write('''
      /*============================================================*/
''')
        # ====================================================================
        # ================= interface definitions for each method =============#
        bsv_file.write('''
    interface mux_lines = interface MuxSelectionLines
''')
        for cell in p.muxed_cells:
            bsv_file.write(
                mux_interface.ifacedef(
                    cell[0], cell_bit_width))
        bsv_file.write("\n    endinterface;")

        bsv_file.write('''
    interface iocell_side = interface IOCellSide
''')
        iocells.ifacedef(bsv_file)
        bsv_file.write("\n     endinterface;")

        bsv_file.write('''
    interface peripheral_side = interface PeripheralSide
''')
        ifaces.ifacedef(bsv_file)
        bsv_file.write("\n     endinterface;")

        bsv_file.write(footer)
        print("BSV file successfully generated: bsv_src/pinmux.bsv")
        # ======================================================================


def write_ptp(ptp, p, ifaces):
    with open(ptp, 'w') as bsv_file:
        bsv_file.write(copyright + '''
package PinTop;
    import pinmux::*;
    interface Ifc_PintTop;
        method ActionValue#(Bool) write(Bit#({0}) addr, Bit#({1}) data);
        method Tuple2#(Bool,Bit#({1})) read(Bit#({0}) addr);
        interface PeripheralSide peripheral_side;
    endinterface

    module mkPinTop(Ifc_PintTop);
        // instantiate the pin-mux module here
        Ifc_pinmux pinmux <-mkpinmux;

        // declare the registers which will be used to mux the IOs
'''.format(p.ADDR_WIDTH, p.DATA_WIDTH))

        cell_bit_width = str(p.cell_bitwidth)
        for cell in p.muxed_cells:
            bsv_file.write('''
                Reg#(Bit#({0})) rg_muxio_{1} <-mkReg(0);'''.format(
                cell_bit_width, cell[0]))

        bsv_file.write('''
        // rule to connect the registers to the selection lines of the
        // pin-mux module
        rule connect_selection_registers;''')

        for cell in p.muxed_cells:
            bsv_file.write('''
          pinmux.mux_lines.cell{0}_mux(rg_muxio_{0});'''.format(cell[0]))

        bsv_file.write('''
        endrule
        // method definitions for the write user interface
        method ActionValue#(Bool) write(Bit#({2}) addr, Bit#({3}) data);
          Bool err=False;
          case (addr[{0}:{1}])'''.format(p.upper_offset, p.lower_offset,
                                         p.ADDR_WIDTH, p.DATA_WIDTH))
        index = 0
        for cell in p.muxed_cells:
            bsv_file.write('''
            {0}: rg_muxio_{1}<=truncate(data);'''.format(index, cell[0]))
            index = index + 1

        bsv_file.write('''
            default: err=True;
          endcase
          return err;
        endmethod''')

        bsv_file.write('''
        // method definitions for the read user interface
        method Tuple2#(Bool,Bit#({3})) read(Bit#({2}) addr);
          Bool err=False;
          Bit#(32) data=0;
          case (addr[{0}:{1}])'''.format(p.upper_offset, p.lower_offset,
                                         p.ADDR_WIDTH, p.DATA_WIDTH))
        index = 0
        for cell in p.muxed_cells:
            bsv_file.write('''
                {0}: data=zeroExtend(rg_muxio_{1});'''.format(index, cell[0]))
            index = index + 1

        bsv_file.write('''
            default:err=True;
          endcase
          return tuple2(err,data);
        endmethod
        interface peripheral_side=pinmux.peripheral_side;
    endmodule
endpackage
''')


def write_bvp(bvp, p, ifaces):
    # ######## Generate bus transactors ################
    gpiocfg = '\t\tinterface GPIO_config#({4}) bank{3}_config;\n' \
              '\t\tinterface AXI4_Lite_Slave_IFC#({0},{1},{2}) bank{3}_slave;'
    muxcfg = '\t\tinterface MUX_config#({4}) muxb{3}_config;\n' \
        '\t\tinterface AXI4_Lite_Slave_IFC#({0},{1},{2}) muxb{3}_slave;'

    gpiodec = '\tGPIO#({0}) mygpio{1} <- mkgpio();'
    muxdec = '\tMUX#({0}) mymux{1} <- mkmux();'
    gpioifc = '\tinterface bank{0}_config=mygpio{0}.pad_config;\n' \
              '\tinterface bank{0}_slave=mygpio{0}.axi_slave;'
    muxifc = '\tinterface muxb{0}_config=mymux{0}.mux_config;\n' \
        '\tinterface muxb{0}_slave=mymux{0}.axi_slave;'
    with open(bvp, 'w') as bsv_file:
        # assume here that all muxes have a 1:1 gpio
        cfg = []
        decl = []
        idec = []
        iks = sorted(ifaces.keys())
        for iname in iks:
            if not iname.startswith('gpio'):  # TODO: declare other interfaces
                continue
            bank = iname[4:]
            ifc = ifaces[iname]
            npins = len(ifc.pinspecs)
            cfg.append(gpiocfg.format(p.ADDR_WIDTH, p.DATA_WIDTH,
                                      0,  # USERSPACE
                                      bank, npins))
            cfg.append(muxcfg.format(p.ADDR_WIDTH, p.DATA_WIDTH,
                                     0,  # USERSPACE
                                     bank, npins))
            decl.append(gpiodec.format(npins, bank))
            decl.append(muxdec .format(npins, bank))
            idec.append(gpioifc.format(bank))
            idec.append(muxifc.format(bank))
        print dir(ifaces)
        print ifaces.items()
        print dir(ifaces['gpioa'])
        print ifaces['gpioa'].pinspecs
        gpiodecl = '\n'.join(decl) + '\n' + '\n'.join(idec)
        gpiocfg = '\n'.join(cfg)
        bsv_file.write(axi4_lite.format(gpiodecl, gpiocfg))
    # ##################################################


def write_instances(idef, p, ifaces):
    with open(idef, 'w') as bsv_file:
        txt = '''\
    `define ADDR {0}
    `define DATA {1}
    `define USERSPACE 0
'''
        bsv_file.write(txt.format(p.ADDR_WIDTH, p.DATA_WIDTH))
