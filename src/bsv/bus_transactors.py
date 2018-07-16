
axi4_lite = '''
// this file is auto-generated, please do not edit
package gpio_instance;
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
    interface GPIO_real;
        interface PeripheralSide peripheral_side;
{1}
    endinterface
  (*synthesize*)
  module mkgpio_real(GPIO_real);
    Ifc_pinmux pinmux <-mkpinmux;
    // gpio/mux declarations
{0}
    interface peripheral_side=pinmux.peripheral_side;
  endmodule
endpackage
'''
