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
	/*============================ */
      `include "instance_defines.bsv"

  // instantiation template
	interface GPIO_real;
		method Action gpio_in (Vector#(32,Bit#(1)) inp);
		method Vector#(32,Bit#(1))   gpio_out;
		method Vector#(32,Bit#(1))   gpio_out_en;
		method Vector#(32,Bit#(1))   gpio_DRV0;
		method Vector#(32,Bit#(1))   gpio_DRV1;
		method Vector#(32,Bit#(1))   gpio_DRV2;
		method Vector#(32,Bit#(1))   gpio_PD;
		method Vector#(32,Bit#(1))   gpio_PPEN;
		method Vector#(32,Bit#(1))   gpio_PRG_SLEW;
		method Vector#(32,Bit#(1))   gpio_PUQ;
		method Vector#(32,Bit#(1))   gpio_PWRUPZHL;
		method Vector#(32,Bit#(1))   gpio_PWRUP_PULL_EN;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USERSPACE) axi_slave;
	endinterface
  (*synthesize*)
  module mkgpio_real(GPIO_real);
    GPIO#(32) mygpioA <-mkgpio();
    method  gpio_out              =mygpioA.gpio_out ;
    method  gpio_out_en           =mygpioA.gpio_out_en;
    method  gpio_DRV0             =mygpioA.gpio_DRV0;
    method  gpio_DRV1             =mygpioA.gpio_DRV1;
    method  gpio_DRV2             =mygpioA.gpio_DRV2;
    method  gpio_PD               =mygpioA.gpio_PD;
    method  gpio_PPEN             =mygpioA.gpio_PPEN;
    method  gpio_PRG_SLEW         =mygpioA.gpio_PRG_SLEW;
    method  gpio_PUQ              =mygpioA.gpio_PUQ;
    method  gpio_PWRUPZHL         =mygpioA.gpio_PWRUPZHL;
    method  gpio_PWRUP_PULL_EN    =mygpioA.gpio_PWRUP_PULL_EN;
		method Action gpio_in (Vector#(32,Bit#(1)) inp);
      mygpioA.gpio_in(inp);
    endmethod
    interface axi_slave=mygpioA.axi_slave;
  endmodule
endpackage

