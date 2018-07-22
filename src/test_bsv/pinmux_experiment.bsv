
/*
   This BSV file has been generated by the PinMux tool available at:
   https://bitbucket.org/casl/pinmux.

   Authors: Neel Gala, Luke
   Date of generation: Sun Jul 22 05:31:10 2018
*/

package pinmux;

   interface MuxSelectionLines;

      // declare the method which will capture the user pin-mux
      // selection values.The width of the input is dependent on the number
      // of muxes happening per IO. For now we have a generalized width
      // where each IO will have the same number of muxes.
     method  Action cell0_mux (Bit#(2) in);
     method  Action cell1_mux (Bit#(2) in);
     method  Action cell2_mux (Bit#(2) in);
      endinterface


      interface IOCellSide;
      // declare the interface to the IO cells.
      // Each IO cell will have 1 input field (output from pin mux)
      // and an output and out-enable field (input to pinmux)
          // interface declaration between IO-0 and pinmux
    (*always_ready,always_enabled*) method  Bit#(1) io0_cell_out;
    (*always_ready,always_enabled*) method  Bit#(1) io0_cell_outen;
    (*always_ready,always_enabled,result="io"*) method 
                       Action io0_cell_in (Bit#(1) in);
          // interface declaration between IO-1 and pinmux
    (*always_ready,always_enabled*) method  Bit#(1) io1_cell_out;
    (*always_ready,always_enabled*) method  Bit#(1) io1_cell_outen;
    (*always_ready,always_enabled,result="io"*) method 
                       Action io1_cell_in (Bit#(1) in);
          // interface declaration between IO-2 and pinmux
    (*always_ready,always_enabled*) method  Bit#(1) io2_cell_out;
    (*always_ready,always_enabled*) method  Bit#(1) io2_cell_outen;
    (*always_ready,always_enabled,result="io"*) method 
                       Action io2_cell_in (Bit#(1) in);
      endinterface


      interface PeripheralSideUART;
          // interface declaration between UART and pinmux
    (*always_ready,always_enabled*) method  Action tx (Bit#(1) in);
    (*always_ready,always_enabled*) method  Bit#(1) rx;
      endinterface

      interface PeripheralSideGPIOA;
          // interface declaration between GPIOA-0 and pinmux
    (*always_ready,always_enabled*) method  Action a0_out (Bit#(1) in);
    (*always_ready,always_enabled*) method  Action a0_outen (Bit#(1) in);
    (*always_ready,always_enabled*) method  Bit#(1) a0_in;
    (*always_ready,always_enabled*) method  Action a1_out (Bit#(1) in);
    (*always_ready,always_enabled*) method  Action a1_outen (Bit#(1) in);
    (*always_ready,always_enabled*) method  Bit#(1) a1_in;
    (*always_ready,always_enabled*) method  Action a2_out (Bit#(1) in);
    (*always_ready,always_enabled*) method  Action a2_outen (Bit#(1) in);
    (*always_ready,always_enabled*) method  Bit#(1) a2_in;
        endinterface

      interface PeripheralSideTWI;
          // interface declaration between TWI and pinmux
    (*always_ready,always_enabled*) method  Action sda_out (Bit#(1) in);
    (*always_ready,always_enabled*) method  Action sda_outen (Bit#(1) in);
    (*always_ready,always_enabled*) method  Bit#(1) sda_in;
    (*always_ready,always_enabled*) method  Action scl_out (Bit#(1) in);
    (*always_ready,always_enabled*) method  Action scl_outen (Bit#(1) in);
    (*always_ready,always_enabled*) method  Bit#(1) scl_in;
      endinterface

      interface PeripheralSide;
      // declare the interface to the peripherals
      // Each peripheral's function will be either an input, output
      // or be bi-directional.  an input field will be an output from the
      // peripheral and an output field will be an input to the peripheral.
      // Bi-directional functions also have an output-enable (which
      // again comes *in* from the peripheral)
          // interface declaration between UART-0 and pinmux
            interface PeripheralSideUART uart;
            interface PeripheralSideGPIOA gpioa;
            interface PeripheralSideTWI twi;
      endinterface


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

   module mkgpioa(PeripheralSideGPIOA);

      // allotted to it
      Wire#(Bit#(1)) wr_a0_out<-mkDWire(0);
      Wire#(Bit#(1)) wr_a0_outen<-mkDWire(0);
      Wire#(Bit#(1)) wr_a0_in<-mkDWire(0);
      Wire#(Bit#(1)) wr_a1_out<-mkDWire(0);
      Wire#(Bit#(1)) wr_a1_outen<-mkDWire(0);
      Wire#(Bit#(1)) wr_a1_in<-mkDWire(0);
      Wire#(Bit#(1)) wr_a2_out<-mkDWire(0);
      Wire#(Bit#(1)) wr_a2_outen<-mkDWire(0);
      Wire#(Bit#(1)) wr_a2_in<-mkDWire(0);

    interface gpioa = interface PeripheralSideGPIOA

      method Action  a0_out(Bit#(1) in);
         wr_a0_out<=in;
      endmethod
      method Action  a0_outen(Bit#(1) in);
         wr_a0_outen<=in;
      endmethod
      method a0_in=wr_a0_in;
      method Action  a1_out(Bit#(1) in);
         wr_a1_out<=in;
      endmethod
      method Action  a1_outen(Bit#(1) in);
         wr_a1_outen<=in;
      endmethod
      method a1_in=wr_a1_in;
      method Action  a2_out(Bit#(1) in);
         wr_a2_out<=in;
      endmethod
      method Action  a2_outen(Bit#(1) in);
         wr_a2_outen<=in;
      endmethod
      method a2_in=wr_a2_in;
    endinterface

   endmodule

   module mkuart(PeripheralSideUART);

      Wire#(Bit#(1)) wr_tx<-mkDWire(0);
      Wire#(Bit#(1)) wr_rx<-mkDWire(0);

    interface uart = interface PeripheralSideUART

      method Action  tx(Bit#(1) in);
         wr_tx<=in;
      endmethod
      method rx=wr_rx;
     endinterface

   endmodule


   module mktwi(PeripheralSideTWI);

      // following wires capture signals to IO CELL if twi-0 is
      // allotted to it
      Wire#(Bit#(1)) wr_sda_out<-mkDWire(0);
      Wire#(Bit#(1)) wr_sda_outen<-mkDWire(0);
      Wire#(Bit#(1)) wr_sda_in<-mkDWire(0);
      Wire#(Bit#(1)) wr_scl_out<-mkDWire(0);
      Wire#(Bit#(1)) wr_scl_outen<-mkDWire(0);
      Wire#(Bit#(1)) wr_scl_in<-mkDWire(0);


    interface twi = interface PeripheralSideTWI

      method Action  sda_out(Bit#(1) in);
         wr_sda_out<=in;
      endmethod
      method Action  sda_outen(Bit#(1) in);
         wr_sda_outen<=in;
      endmethod
      method sda_in=wr_sda_in;
      method Action  scl_out(Bit#(1) in);
         wr_scl_out<=in;
      endmethod
      method Action  scl_outen(Bit#(1) in);
         wr_scl_outen<=in;
      endmethod
      method scl_in=wr_scl_in;

     endinterface;

   endmodule


   module mkpinmux(Ifc_pinmux);

      // the followins wires capture the pin-mux selection
      // values for each mux assigned to a CELL

      Wire#(Bit#(2)) wrcell0_mux<-mkDWire(0);
      Wire#(Bit#(2)) wrcell1_mux<-mkDWire(0);
      Wire#(Bit#(2)) wrcell2_mux<-mkDWire(0);
      // following wires capture signals to IO CELL if io-0 is
      // allotted to it
      Wire#(Bit#(1)) cell0_mux_out<-mkDWire(0);
      Wire#(Bit#(1)) cell0_mux_outen<-mkDWire(0);
      Wire#(Bit#(1)) cell0_mux_in<-mkDWire(0);

      // following wires capture signals to IO CELL if io-1 is
      // allotted to it
      Wire#(Bit#(1)) cell1_mux_out<-mkDWire(0);
      Wire#(Bit#(1)) cell1_mux_outen<-mkDWire(0);
      Wire#(Bit#(1)) cell1_mux_in<-mkDWire(0);

      // following wires capture signals to IO CELL if io-2 is
      // allotted to it
      Wire#(Bit#(1)) cell2_mux_out<-mkDWire(0);
      Wire#(Bit#(1)) cell2_mux_outen<-mkDWire(0);
      Wire#(Bit#(1)) cell2_mux_in<-mkDWire(0);

      // following wires capture signals to IO CELL if uart-0 is
      // allotted to it
      Wire#(Bit#(1)) wruart_tx<-mkDWire(0);
      Wire#(Bit#(1)) wruart_rx<-mkDWire(0);

      // following wires capture signals to IO CELL if gpioa-0 is
      // allotted to it
      Wire#(Bit#(1)) wrgpioa_a0_out<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a0_outen<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a0_in<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a1_out<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a1_outen<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a1_in<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a2_out<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a2_outen<-mkDWire(0);
      Wire#(Bit#(1)) wrgpioa_a2_in<-mkDWire(0);

      // following wires capture signals to IO CELL if twi-0 is
      // allotted to it
      Wire#(Bit#(1)) wrtwi_sda_out<-mkDWire(0);
      Wire#(Bit#(1)) wrtwi_sda_outen<-mkDWire(0);
      Wire#(Bit#(1)) wrtwi_sda_in<-mkDWire(0);
      Wire#(Bit#(1)) wrtwi_scl_out<-mkDWire(0);
      Wire#(Bit#(1)) wrtwi_scl_outen<-mkDWire(0);
      Wire#(Bit#(1)) wrtwi_scl_in<-mkDWire(0);


      /*====== This where the muxing starts for each io-cell======*/
      Wire#(Bit#(1)) val0<-mkDWire(0); // need a zero
       // output muxer for cell idx 0
      cell0_mux_out=
			wrcell0_mux==0?wrgpioa_a0_out:
			wrcell0_mux==1?wruart_tx:
			wrcell0_mux==2?val0: // unused
			wrtwi_sda_out;

      // outen muxer for cell idx 0
      cell0_mux_outen=
			wrcell0_mux==0?wrgpioa_a0_outen: // bi-directional
			wrcell0_mux==1?wrgpioa_a0_outen: // uart_tx is an output
			wrcell0_mux==2?val0: // unused
			wrtwi_sda_outen; // bi-directional

      // priority-in-muxer for cell idx 0
      rule assign_wrgpioa_a0_in_on_cell0(wrcell0_mux==0);
        wrgpioa_a0_in<=cell0_mux_in;
      endrule

      rule assign_wrtwi_sda_in_on_cell0(wrcell0_mux==3);
        wrtwi_sda_in<=cell0_mux_in;
      endrule

      // output muxer for cell idx 1
      cell1_mux_out=
			wrcell1_mux==0?wrgpioa_a1_out:
			wrcell1_mux==1?val0: // uart_rx is an input
			wrcell1_mux==2?wrtwi_sda_out:
			val0; // unused

      // outen muxer for cell idx 1
      cell1_mux_outen=
			wrcell1_mux==0?wrgpioa_a1_outen: // bi-directional
			wrcell1_mux==1?val0: // uart_rx is an input
			wrcell1_mux==2?wrtwi_sda_outen: // bi-directional
			val0; // unused

      // priority-in-muxer for cell idx 1
      rule assign_wrgpioa_a1_in_on_cell1(wrcell1_mux==0);
        wrgpioa_a1_in<=cell1_mux_in;
      endrule

      rule assign_wruart_rx_on_cell1(wrcell1_mux==1);
        wruart_rx<=cell1_mux_in;
      endrule

      rule assign_wrtwi_sda_in_on_cell1(wrcell1_mux==2);
        wrtwi_sda_in<=cell1_mux_in;
      endrule

      // output muxer for cell idx 2
      cell2_mux_out=
			wrcell2_mux==0?wrgpioa_a2_out:
			wrcell2_mux==1?val0: // unused
			wrcell2_mux==2?wrtwi_scl_out:
			val0; // unused

      // outen muxer for cell idx 2
      cell2_mux_outen=
			wrcell2_mux==0?wrgpioa_a2_outen: // bi-directional
			wrcell2_mux==1?val0: // unused
			wrcell2_mux==2?wrtwi_scl_outen: // bi-directional
			val0; // unused

      // priority-in-muxer for cell idx 2
      rule assign_wrgpioa_a2_in_on_cell2(wrcell2_mux==0);
        wrgpioa_a2_in<=cell2_mux_in;
      endrule

      rule assign_wrtwi_scl_in_on_cell2(wrcell2_mux==2);
        wrtwi_scl_in<=cell2_mux_in;
      endrule


      /*=========================================*/
      // dedicated cells


      /*============================================================*/

    interface mux_lines = interface MuxSelectionLines

      method Action  cell0_mux(Bit#(2) in);
         wrcell0_mux<=in;
      endmethod

      method Action  cell1_mux(Bit#(2) in);
         wrcell1_mux<=in;
      endmethod

      method Action  cell2_mux(Bit#(2) in);
         wrcell2_mux<=in;
      endmethod

    endinterface;

    interface iocell_side = interface IOCellSide

      method io0_cell_out=cell0_mux_out;
      method io0_cell_outen=cell0_mux_outen;
      method Action  io0_cell_in(Bit#(1) in);
         cell0_mux_in<=in;
      endmethod

      method io1_cell_out=cell1_mux_out;
      method io1_cell_outen=cell1_mux_outen;
      method Action  io1_cell_in(Bit#(1) in);
         cell1_mux_in<=in;
      endmethod

      method io2_cell_out=cell2_mux_out;
      method io2_cell_outen=cell2_mux_outen;
      method Action  io2_cell_in(Bit#(1) in);
         cell2_mux_in<=in;
      endmethod

     endinterface;

    interface peripheral_side_uart = interface PeripheralSideUART

      method Action  tx(Bit#(1) in);
         wruart_tx<=in;
      endmethod
      method rx=wruart_rx;
     endinterface

    interface peripheral_side_gpioa = interface PeripheralSideGPIOA

      method Action  a0_out(Bit#(1) in);
         wrgpioa_a0_out<=in;
      endmethod
      method Action  a0_outen(Bit#(1) in);
         wrgpioa_a0_outen<=in;
      endmethod
      method a0_in=wrgpioa_a0_in;
      method Action  a1_out(Bit#(1) in);
         wrgpioa_a1_out<=in;
      endmethod
      method Action  a1_outen(Bit#(1) in);
         wrgpioa_a1_outen<=in;
      endmethod
      method a1_in=wrgpioa_a1_in;
      method Action  a2_out(Bit#(1) in);
         wrgpioa_a2_out<=in;
      endmethod
      method Action  a2_outen(Bit#(1) in);
         wrgpioa_a2_outen<=in;
      endmethod
      method a2_in=wrgpioa_a2_in;
    endinterface

    interface peripheral_side_twi = interface PeripheralSideTWI

      method Action  sda_out(Bit#(1) in);
         wrtwi_sda_out<=in;
      endmethod
      method Action  sda_outen(Bit#(1) in);
         wrtwi_sda_outen<=in;
      endmethod
      method sda_in=wrtwi_sda_in;
      method Action  scl_out(Bit#(1) in);
         wrtwi_scl_out<=in;
      endmethod
      method Action  scl_outen(Bit#(1) in);
         wrtwi_scl_outen<=in;
      endmethod
      method scl_in=wrtwi_scl_in;

     endinterface;

    interface peripheral_side = interface PeripheralSide

      interface uart = uart.mkuart();
      interface gpioa = gpioa.mkgpioa();
      interface twi = twi.mktwi();

     endinterface;
   endmodule
endpackage
