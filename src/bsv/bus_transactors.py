
axi4_lite = '''
// this file is auto-generated, please do not edit
package bus;
    /*==== Package imports ==== */
    import TriState          ::*;
    import Vector                ::*;
    import BUtils::*;
    import ConfigReg            ::*;
    /*============================ */
    /*===== Project Imports ===== */
    import Semi_FIFOF        :: *;
    import AXI4_Lite_Types   :: *;
    import gpio   :: *;
    import mux   :: *;
    import pinmux   :: *;
    /*============================ */

  // instantiation template
    interface BUS;
        interface PeripheralSide peripheral_side;
        interface IOCellSide iocell_side;
{1}
    endinterface
  (*synthesize*)
  module mkbus(BUS);
    Ifc_pinmux pinmux <-mkpinmux;
    // gpio/mux declarations
{0}
    interface peripheral_side=pinmux.peripheral_side;
    interface iocell_side=pinmux.iocell_side;
  endmodule
endpackage
'''
