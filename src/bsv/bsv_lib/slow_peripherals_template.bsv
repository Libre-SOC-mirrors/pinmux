package slow_peripherals;
	/*===== Project imports =====*/
	import defined_types::*;
	import AXI4_Lite_Fabric::*;
	import AXI4_Lite_Types::*;
	import AXI4_Fabric::*;
	import AXI4_Types::*;
	import Semi_FIFOF::*;
	import AXI4Lite_AXI4_Bridge::*;
	`include "instance_defines.bsv"
    /* ==== define the AXI Addresses ==== */
{2}
    /* ==== define the number of slow peripheral irqs ==== */
{11}
    /*====== AXI4 Lite slave declarations =======*/

{3}
	/*===========================*/
	/*=== package imports ===*/
	import Clocks::*;
	import GetPut::*;
	import ClientServer::*;
	import Connectable::*;
	import Vector::*;
	import FIFO::*;
	/*=======================*/
	/*===== Import the slow peripherals ====*/
{0}
    `ifdef CLINT
        import clint::*;
    `endif
    `ifdef PLIC
        import plic             ::*;
    `endif
	`ifdef AXIEXP
		import axiexpansion	::*;
	`endif
	`ifdef QSPI 
		import qspi				 :: *; 
	`endif
	/*=====================================*/
	
	/*===== interface declaration =====*/
	interface SP_dedicated_ios;
		`ifdef AXIEXP
			interface Get#(Bit#(67)) axiexp1_out;
			interface Put#(Bit#(67)) axiexp1_in;
		`endif
	endinterface
	interface Ifc_slow_peripherals;
		interface AXI4_Slave_IFC#(`ADDR,`DATA,`USERSPACE) axi_slave;
		interface SP_dedicated_ios slow_ios;
		`ifdef CLINT
			method Bit#(1) msip_int;
			method Bit#(1) mtip_int;
			method Bit#(`DATA) mtime;
		`endif
		`ifdef PLIC method ActionValue#(Tuple2#(Bool,Bool)) intrpt_note; `endif
    interface IOCellSide iocell_side; // mandatory interface
{1}
	endinterface
	/*================================*/

	function Tuple2#(Bool, Bit#(TLog#(Num_Slow_Slaves)))
                     fn_address_mapping (Bit#(`ADDR) addr);
		`ifdef CLINT
			if(addr>=`ClintBase && addr<=`ClintEnd)
				return tuple2(True,fromInteger(valueOf(CLINT_slave_num)));
			else
		`endif
		`ifdef PLIC
			if(addr>=`PLICBase && addr<=`PLICEnd)
				return tuple2(True,fromInteger(valueOf(Plic_slave_num)));
			else
		`endif
		`ifdef AXIEXP
			if(addr>=`AxiExp1Base && addr<=`AxiExp1End)
				return tuple2(True,fromInteger(valueOf(AxiExp1_slave_num)));
			else
		`endif
{4}
			return tuple2(False,?);
	endfunction

	(*synthesize*)
	module mkslow_peripherals#(Clock fast_clock, Reset fast_reset,
                               Clock uart_clock, Reset uart_reset
                              `ifdef PWM_AXI4Lite ,Clock ext_pwm_clock `endif
                              )(Ifc_slow_peripherals);
		Clock sp_clock <-exposeCurrentClock; // slow peripheral clock
		Reset sp_reset <-exposeCurrentReset; // slow peripheral reset

		/*======= Module declarations for each peripheral =======*/
{5}
		`ifdef CLINT
			Ifc_clint				clint				<- mkclint();
		`endif
		`ifdef PLIC
			Ifc_PLIC_AXI	plic <- mkplicperipheral();
         Wire#(Bit#(TLog#(`INTERRUPT_PINS))) interrupt_id <- mkWire();
			  Vector#(`INTERRUPT_PINS, FIFO#(bit)) ff_gateway_queue <- replicateM(mkFIFO);
		`endif
		`ifdef AXIEXP
			Ifc_AxiExpansion		axiexp1			<- mkAxiExpansion();	
		`endif
    Ifc_pinmux pinmux <- mkpinmux; // mandatory
		/*=======================================================*/

   	AXI4_Lite_Fabric_IFC #(1, Num_Slow_Slaves, `ADDR, `DATA,`USERSPACE)
            slow_fabric <- mkAXI4_Lite_Fabric(fn_address_mapping);
		Ifc_AXI4Lite_AXI4_Bridge
            bridge<-mkAXI4Lite_AXI4_Bridge(fast_clock,fast_reset);
   	
		mkConnection (bridge.axi4_lite_master,	slow_fabric.v_from_masters [0]);
		/*======= Slave connections to AXI4Lite fabric =========*/
{6}
		`ifdef CLINT
			mkConnection (slow_fabric.v_to_slaves
                    [fromInteger(valueOf(CLINT_slave_num))],
                    clint.axi4_slave);
		`endif
		`ifdef PLIC
			mkConnection (slow_fabric.v_to_slaves
                    [fromInteger(valueOf(Plic_slave_num))],	
                    plic.axi4_slave_plic); //
		`endif
		`ifdef AXIEXP
   		mkConnection (slow_fabric.v_to_slaves
                    [fromInteger(valueOf(AxiExp1_slave_num))],	
                    axiexp1.axi_slave); //
		`endif

    /*========== pinmux connections ============*/
{7}
{8}
    rule rl_completion_msg_from_plic;
		  let id <- plic.intrpt_completion;
      interrupt_id <= id;
      `ifdef verbose $display("Dequeing the FIFO -- PLIC Interrupt Serviced id: %d",id); `endif
		endrule

    for(Integer i=0; i <`INTERRUPT_PINS; i=i+1) begin
	    rule deq_gateway_queue;
		    if(interrupt_id==fromInteger(i)) begin
			    ff_gateway_queue[i].deq;
          `ifdef $display($time,"Dequeing the Interrupt request for ID: %d",i); `endif
        end
      endrule
    end
    // NEEL EDIT OVER
		/*=======================================================*/
		/*=================== PLIC Connections ==================== */
		`ifdef PLIC_main
			/*TODO DMA interrupt need to be connected to the plic
			for(Integer i=1; i<8; i=i+1) begin
         `ifdef DMA
             rule rl_connect_dma_interrupts_to_plic;
					if(dma.interrupt_to_processor[i-1]==1'b1) begin
						ff_gateway_queue[i].enq(1);
						plic.ifc_external_irq[i].irq_frm_gateway(True);
					end
             endrule
          `else
             rule rl_connect_dma_interrupts_to_plic;
                 ff_gateway_queue[i].enq(0);
             endrule
          `endif
         end
			*/
{10}
         for(Integer i = 14; i < 20; i=i+1) begin
				rule rl_connect_qspi0_to_plic;
					`ifdef QSPI0
						if(qspi0.interrupts()[i-14]==1'b1) begin
							ff_gateway_queue[i].enq(1);
							plic.ifc_external_irq[i].irq_frm_gateway(True);
						end
               `else
						ff_gateway_queue[i].enq(0);
               `endif
            endrule
         end

         for(Integer i = 20; i<26; i=i+1) begin
				rule rl_connect_qspi1_to_plic;
					`ifdef QSPI1
						if(qspi1.interrupts()[i-20]==1'b1) begin
							ff_gateway_queue[i].enq(1);
							plic.ifc_external_irq[i].irq_frm_gateway(True);
						end
               `else
						ff_gateway_queue[i].enq(0);
               `endif
            endrule
			end
        
			`ifdef UART0 
				SyncBitIfc#(Bit#(1)) uart0_interrupt <-
                                  mkSyncBitToCC(sp_clock, uart_reset); 
				rule synchronize_the_uart0_interrupt;
					uart0_interrupt.send(uart0.irq);		
				endrule
			`endif
			rule rl_connect_uart_to_plic;
				`ifdef UART0
					if(uart0_interrupt.read==1'b1) begin
						ff_gateway_queue[27].enq(1);
			  			plic.ifc_external_irq[27].irq_frm_gateway(True);
               end
			  	
            `else
					ff_gateway_queue[27].enq(0);
            `endif
         endrule
             
			for(Integer i = 28; i<`INTERRUPT_PINS; i=i+1) begin
				rule rl_raise_interrupts;
					if((i-28)<`IONum) begin	//Peripheral interrupts
						if(gpio.to_plic[i-28]==1'b1) begin
							plic.ifc_external_irq[i].irq_frm_gateway(True);
								ff_gateway_queue[i].enq(1);	
                  end
					end
				endrule
			end
			
         rule rl_completion_msg_from_plic;
				let id <- plic.intrpt_completion;
            interrupt_id <= id;
            `ifdef verbose $display("Dequeing the FIFO -- PLIC Interrupt Serviced id: %d",id); `endif
			endrule

         for(Integer i=0; i <`INTERRUPT_PINS; i=i+1) begin
				rule deq_gateway_queue;
					if(interrupt_id==fromInteger(i)) begin
						ff_gateway_queue[i].deq;
                  `ifdef $display($time,"Dequeing the Interrupt request for ID: %d",i); `endif
               end
            endrule
         end

				
		`endif
			/*======================================================= */

		/* ===== interface definition =======*/
		interface axi_slave=bridge.axi_slave;
		`ifdef PLIC method intrpt_note = plic.intrpt_note; `endif
		`ifdef CLINT
			method msip_int=clint.msip_int;
			method mtip_int=clint.mtip_int;
			method mtime=clint.mtime;
		`endif
		`ifdef I2C0
			method i2c0_isint=i2c0.isint;
		`endif
		`ifdef I2C1
			method i2c1_isint=i2c1.isint;
		`endif
		`ifdef QSPI0 method	qspi0_isint=qspi0.interrupts[5]; `endif
		`ifdef QSPI1 method	qspi1_isint=qspi1.interrupts[5]; `endif
		`ifdef UART0 method uart0_intr=uart0.irq; `endif
		interface SP_dedicated_ios slow_ios;
/* template for dedicated peripherals
			`ifdef UART0
				interface uart0_coe=uart0.coe_rs232;
			`endif
			`ifdef UART1
				interface uart1_coe=uart1.coe_rs232;
			`endif
			`ifdef I2C0
				interface i2c0_out=i2c0.out;
			`endif
			`ifdef I2C1
				interface i2c1_out=i2c1.out;
			`endif
			`ifdef QSPI0 
				interface qspi0_out = qspi0.out; 
			`endif
			`ifdef QSPI1 
				interface qspi1_out = qspi1.out; 
			`endif
			`ifdef AXIEXP
				interface axiexp1_out=axiexp1.slave_out;
				interface axiexp1_in=axiexp1.slave_in;
			`endif
      `ifdef PWM_AXI4Lite
        interface pwm_o = pwm_bus.pwm_io;
      `endif
*/
		endinterface
    // NEEL EDIT
    interface iocell_side=pinmux.iocell_side;
    interface pad_config0= gpioa.pad_config;
{9}
    // NEEL EDIT OVER
		/*===================================*/
	endmodule
endpackage
