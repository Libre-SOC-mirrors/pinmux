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
package gpio;
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
	`include "instance_defines.bsv"

	interface GPIO_config#(numeric type ionum);
		(*always_ready,always_enabled*)
		method Action gpio_in (Vector#(ionum,Bit#(1)) inp);
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_out;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_out_en;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_DRV0;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_DRV1;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_DRV2;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_PD;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_PPEN;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_PRG_SLEW;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_PUQ;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_PWRUPZHL;
		(*always_ready*)
		method Vector#(ionum,Bit#(1))   gpio_PWRUP_PULL_EN;
  endinterface
  interface GPIO#(numeric type ionum);
    interface GPIO_config#(ionum) pad_config;
		interface AXI4_Lite_Slave_IFC#(`ADDR,`DATA,`USERSPACE) axi_slave;
	endinterface

	module mkgpio(GPIO#(ionum_));
    let ionum = valueOf(ionum_);
		Vector#(ionum_,ConfigReg#(Bool)) direction_reg			<-replicateM(mkConfigReg(False));
		Vector#(ionum_,ConfigReg#(Bit#(1))) dataout_register	<-replicateM(mkConfigReg(0));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) datain_register	<-replicateM(mkConfigReg(0));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) drv0_reg	<-replicateM(mkConfigReg(1'b1));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) drv1_reg	<-replicateM(mkConfigReg(1'b1));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) drv2_reg	<-replicateM(mkConfigReg(0));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) pd_reg	<-replicateM(mkConfigReg(0));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) ppen_reg	<-replicateM(mkConfigReg(0));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) prg_slew_reg	<-replicateM(mkConfigReg(1'b1));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) puq_reg	<-replicateM(mkConfigReg(0));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) pwrupzhl_reg	<-replicateM(mkConfigReg(0));	
		Vector#(ionum_,ConfigReg#(Bit#(1))) pwrup_pull_en_reg	<-replicateM(mkConfigReg(0));	
		
		AXI4_Lite_Slave_Xactor_IFC #(`ADDR, `DATA, `USERSPACE)  s_xactor <- mkAXI4_Lite_Slave_Xactor;
		rule rl_wr_respond;
			// Get the wr request
      	let aw <- pop_o (s_xactor.o_wr_addr);
      	let w  <- pop_o (s_xactor.o_wr_data);
	   	let b = AXI4_Lite_Wr_Resp {bresp: AXI4_LITE_OKAY, buser: aw.awuser};
			if(aw.awaddr[5:0]=='h0)
				for(Integer i=0;i<ionum;i=i+1)
					direction_reg[i]<=unpack(w.wdata[i]);
			else if(aw.awaddr[5:0]=='h4)
				for(Integer i=0;i<ionum;i=i+1)
					dataout_register[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h8)
				for(Integer i=0;i<ionum;i=i+1)
					drv0_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='hC)
				for(Integer i=0;i<ionum;i=i+1)
					drv1_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h10)
				for(Integer i=0;i<ionum;i=i+1)
					drv2_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h14)
				for(Integer i=0;i<ionum;i=i+1)
					pd_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h18)
				for(Integer i=0;i<ionum;i=i+1)
					ppen_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h1C)
				for(Integer i=0;i<ionum;i=i+1)
					prg_slew_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h20)
				for(Integer i=0;i<ionum;i=i+1)
					puq_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h24)
				for(Integer i=0;i<ionum;i=i+1)
					pwrupzhl_reg[i]<=w.wdata[i];
			else if(aw.awaddr[5:0]=='h28)
				for(Integer i=0;i<ionum;i=i+1)
					pwrup_pull_en_reg[i]<=w.wdata[i];
			else
				b.bresp=AXI4_LITE_SLVERR;
				
      	s_xactor.i_wr_resp.enq (b);
		endrule

		rule rl_rd_respond;
			let ar<- pop_o(s_xactor.o_rd_addr);
			Bit#(32) temp=0;
			AXI4_Lite_Rd_Data#(`DATA,`USERSPACE) r = AXI4_Lite_Rd_Data {rresp: AXI4_LITE_OKAY, rdata: ?, ruser: 0};
			if(ar.araddr[5:0]=='h0)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=pack(direction_reg[i]);
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h4)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=datain_register[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h8)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=drv0_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='hC)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=drv1_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h10)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=drv2_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h14)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=pd_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h18)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=ppen_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h1C)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=prg_slew_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h20)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=puq_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h24)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=pwrupzhl_reg[i];
				r.rdata=duplicate(temp);
			end
			else if(ar.araddr[5:0]=='h28)begin
				for(Integer i=0;i<ionum;i=i+1)
					temp[i]=pwrup_pull_en_reg[i];
				r.rdata=duplicate(temp);
      end
			else
				r.rresp=AXI4_LITE_SLVERR;
				
			s_xactor.i_rd_data.enq(r);
		endrule

		interface axi_slave= s_xactor.axi_side;
    interface pad_config=interface GPIO_config
    	method Action gpio_in (Vector#(ionum,Bit#(1)) inp);
	  		for(Integer i=0;i<ionum;i=i+1)
	  			datain_register[i]<=inp[i];
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_out;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=dataout_register[i];
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_out_en;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(direction_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_DRV0;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(drv0_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_DRV1;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(drv1_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_DRV2;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(drv2_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_PD;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(pd_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_PPEN;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(ppen_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_PRG_SLEW;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(prg_slew_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_PUQ;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(puq_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_PWRUPZHL;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(pwrupzhl_reg[i]);
	  		return temp;
	  	endmethod
	  	method Vector#(ionum,Bit#(1))   gpio_PWRUP_PULL_EN;
	  		Vector#(ionum,Bit#(1)) temp;
	  		for(Integer i=0;i<ionum;i=i+1)
	  			temp[i]=pack(pwrup_pull_en_reg[i]);
	  		return temp;
	  	endmethod
    endinterface;
	endmodule

endpackage

