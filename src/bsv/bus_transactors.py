
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
    interface GPIO_config#(32) bankA_config;
        interface AXI4_Lite_Slave_IFC#({0},{1},{2}) bankA_slave;
    interface GPIO_config#(15) bankB_config;
        interface AXI4_Lite_Slave_IFC#({0},{1},{2}) bankB_slave;

    interface MUX_config#(32) muxbankA_config;
        interface AXI4_Lite_Slave_IFC#({0},{1},{2}) muxbankA_slave;
    interface MUX_config#(15) muxbankB_config;
        interface AXI4_Lite_Slave_IFC#({0},{1},{2}) muxbankB_slave;
    endinterface
  (*synthesize*)
  module mkgpio_real(GPIO_real);
    Ifc_pinmux pinmux <-mkpinmux;
    // gpio/mux declarations
{3}
    interface peripheral_side=pinmux.peripheral_side;
  endmodule
endpackage
'''
