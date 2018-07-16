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
package mux;
	/*==== Package imports ==== */
	import TriState          ::*;
	import Vector				 ::*;
	import BUtils::*;
	import ConfigReg			::*;
	/*============================ */
	/*===== Project Imports ===== */
	import Semi_FIFOF        :: *;
	import AXI4_Lite_Types   :: *;
	/*============================ */
  `define ADDR 32
  `define DATA 64
  `define USER 0
  `define IONum 32
  `define GPIO_MUX

	interface MUX#(numeric type ionum);
		(*always_ready,always_enabled*)
		method Vector#(ionum,Bit#(2))   mux;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USER) axi_slave;
	endinterface

//	(*synthesize*)
	module mkmux(MUX#(ionum_));
	  Vector#(ionum_,ConfigReg#(Bit#(2))) muxer_reg 				<-replicateM(mkConfigReg(0));
		
		AXI4_Lite_Slave_Xactor_IFC #(`ADDR, `DATA, `USER)  s_xactor <- mkAXI4_Lite_Slave_Xactor;
    let ionum=valueOf(ionum_);
		rule rl_wr_respond;
			// Get the wr request
      let aw <- pop_o (s_xactor.o_wr_addr);
      let w  <- pop_o (s_xactor.o_wr_data);
	   	let b = AXI4_Lite_Wr_Resp {bresp: AXI4_LITE_OKAY, buser: aw.awuser};
		  if(aw.awaddr[5:0]=='h2c)
		    for(Integer i=0;i<min(ionum, 16);i=i+1) begin
          muxer_reg[i]<= w.wdata[i*2+1:i*2];
		  	end
		  else if(aw.awaddr[5:0]=='h30 && ionum>=16)
		  	for(Integer i=0;i<ionum-16;i=i+1) begin
          muxer_reg[i+16]<= w.wdata[i*2+1:i*2];
		  	end
			else
				b.bresp=AXI4_LITE_SLVERR;
      	s_xactor.i_wr_resp.enq (b);
		endrule

		rule rl_rd_respond;
			let ar<- pop_o(s_xactor.o_rd_addr);
			Bit#(32) temp=0;
			AXI4_Lite_Rd_Data#(`DATA,`USER) r = AXI4_Lite_Rd_Data {rresp: AXI4_LITE_OKAY, rdata: ?, ruser: 0};
		  if(ar.araddr[5:0]=='h2c)begin
		  	for(Integer i=0;i<min(ionum, 16);i=i+1) begin
          temp[i*2+ 1:i*2]=muxer_reg[i];
		  	end
        r.rdata=duplicate(temp);
      end
		  else if(ar.araddr[5:0]=='h30 && ionum>=16)begin
		  	for(Integer i=0;i<ionum-16;i=i+1) begin
          temp[i*2+ 1:i*2]=muxer_reg[i+ 16];
		  	end
        r.rdata=duplicate(temp);
      end
			else
				r.rresp=AXI4_LITE_SLVERR;
			s_xactor.i_rd_data.enq(r);
		endrule

		interface axi_slave= s_xactor.axi_side;
		method Vector#(ionum,Bit#(2))   mux;
			Vector#(ionum,Bit#(2)) temp;
			for(Integer i=0;i<ionum;i=i+1)
				temp[i]=pack(muxer_reg[i]);
			return temp;
		endmethod
	endmodule


  // instantiation template
	interface MUX_real;
		(*always_ready,always_enabled*)
		method Vector#(32,Bit#(2))   mux;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USER) axi_slave;
	endinterface
  (*synthesize*)
  module mkmux_real(MUX_real);
    MUX#(32) mymux <-mkmux();
    method mux=mymux.mux;
    interface axi_slave=mymux.axi_slave;
  endmodule
endpackage

