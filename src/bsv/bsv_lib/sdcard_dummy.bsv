/* 
Copyright (c) 2013, IIT Madras All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this list of conditions
  and the following disclaimer.  
* Redistributions in binary form must reproduce the above copyright notice, this list of 
  conditions and the following disclaimer in the documentation and/or other materials provided 
 with the distribution.  
* Neither the name of IIT Madras  nor the names of its contributors may be used to endorse or 
  promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT 
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
--------------------------------------------------------------------------------------------------

Author: Neel Gala
Email id: neelgala@gmail.com
Details:

--------------------------------------------------------------------------------------------------
*/
package sdcard_dummy;
  `include "instance_defines.bsv"
  import ClockDiv::*;
  import ConcatReg::*;
	import Semi_FIFOF::*;
	import BUtils ::*;
 	import AXI4_Lite_Types::*;

  interface Ifc_sdcard_dummy;
	  interface AXI4_Lite_Slave_IFC#(`ADDR, `DATA, `USERSPACE) axi_slave;
    method  Bit#(1) cmd; 
    method  Bit#(1) clk;
    method  Bit#(1) d0_out;
    method  Bit#(1) d0_outen;
    method  Action d0_in(Bit#(1) in);
    method  Bit#(1) d1_out;
    method  Bit#(1) d1_outen;
    method  Action d1_in(Bit#(1) in);
    method  Bit#(1) d2_out;
    method  Bit#(1) d2_outen;
    method  Action d2_in(Bit#(1) in);
    method  Bit#(1) d3_out;
    method  Bit#(1) d3_outen;
    method  Action d3_in(Bit#(1) in);
  endinterface
  (*synthesize*)
  module mksdcard_dummy(Ifc_sdcard_dummy);
	  	AXI4_Lite_Slave_Xactor_IFC#(`ADDR,`DATA, `USERSPACE) s_xactor<-mkAXI4_Lite_Slave_Xactor();
      interface axi_slave=s_xactor.axi_side;
      Reg#(Bit#(1)) rg_cmd <- mkReg(0);
      Reg#(Bit#(1)) rg_clk <- mkReg(0);
      Reg#(Bit#(1)) rg_d0_out <- mkReg(0);
      Reg#(Bit#(1)) rg_d0_outen <- mkReg(0);
      Reg#(Bit#(1)) rg_d0_in <- mkReg(0);
      Reg#(Bit#(1)) rg_d1_out <- mkReg(0);
      Reg#(Bit#(1)) rg_d1_outen <- mkReg(0);
      Reg#(Bit#(1)) rg_d1_in <- mkReg(0);
      Reg#(Bit#(1)) rg_d2_out <- mkReg(0);
      Reg#(Bit#(1)) rg_d2_outen <- mkReg(0);
      Reg#(Bit#(1)) rg_d2_in <- mkReg(0);
      Reg#(Bit#(1)) rg_d3_out <- mkReg(0);
      Reg#(Bit#(1)) rg_d3_outen <- mkReg(0);
      Reg#(Bit#(1)) rg_d3_in <- mkReg(0);
    method  cmd = rg_cmd; 
    method  clk = rg_clk;
    method  d0_out=rg_d0_out;
    method  d0_outen=rg_d0_outen;
    method  Action d0_in(Bit#(1) in);
      rg_d0_in<= in;
    endmethod
    method  d1_out=rg_d1_out;
    method  d1_outen=rg_d1_outen;
    method  Action d1_in(Bit#(1) in);
      rg_d1_in<= in;
    endmethod
    method  d2_out=rg_d2_out;
    method  d2_outen=rg_d2_outen;
    method  Action d2_in(Bit#(1) in);
      rg_d2_in<= in;
    endmethod
    method  d3_out=rg_d3_out;
    method  d3_outen=rg_d3_outen;
    method  Action d3_in(Bit#(1) in);
      rg_d3_in<= in;
    endmethod
  endmodule
endpackage
