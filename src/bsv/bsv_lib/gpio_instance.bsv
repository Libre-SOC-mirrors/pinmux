/*
Copyright (c) 2013, IIT Madras
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

*  Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
*  Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
*  Neither the name of IIT Madras  nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. 
---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
*/
package gpio_instance;
	/*==== Package imports ==== */
	import TriState          ::*;
	import Vector				 ::*;
	import BUtils::*;
	import ConfigReg			::*;
	/*============================ */
	/*===== Project Imports ===== */
	import Semi_FIFOF        :: *;
	import AXI4_Lite_Types   :: *;
	import gpio   :: *;
	import mux   :: *;
	/*============================ */
      `include "instance_defines.bsv"

  // instantiation template
	interface GPIO_real;
    interface GPIO_config#(32) bankA_config;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USERSPACE) bankA_slave;
    interface GPIO_config#(15) bankB_config;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USERSPACE) bankB_slave;

    interface MUX_config#(32) muxbankA_config;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USERSPACE) muxbankA_slave;
    interface MUX_config#(15) muxbankB_config;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USERSPACE) muxbankB_slave;
	endinterface
  (*synthesize*)
  module mkgpio_real(GPIO_real);
    GPIO#(32) mygpioA <- mkgpio();
    GPIO#(15) mygpioB <- mkgpio();
    MUX#(32)  mymuxA <- mkmux();
    MUX#(15)  mymuxB <- mkmux();
    interface bankA_config=mygpioA.pad_config;
    interface bankB_config=mygpioB.pad_config;
    interface bankA_slave=mygpioA.axi_slave;
    interface bankB_slave=mygpioB.axi_slave;
    interface muxbankA_config=mymuxA.mux_config;
    interface muxbankB_config=mymuxB.mux_config;
    interface muxbankA_slave=mymuxA.axi_slave;
    interface muxbankB_slave=mymuxB.axi_slave;
  endmodule
endpackage

