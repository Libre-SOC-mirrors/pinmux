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
	`ifdef UART0
		import Uart16550		 :: *;
	`endif
	`ifdef UART1
		import Uart_bs::*;
		import RS232_modified::*;
	`endif
	`ifdef CLINT
		import clint::*;
	`endif
	`ifdef PLIC
		import plic				::*;
	`endif
	`ifdef I2C0
		import I2C_top			 :: *;
	`endif
	`ifdef QSPI0 
		import qspi				 :: *; 
	`endif
	`ifdef AXIEXP
		import axiexpansion	::*;
	`endif
  `ifdef PWM_AXI4Lite 
    import pwm::*;
  `endif
  // NEEL EDIT
  import pinmux::*;
  import mux::*;
  import gpio::*;
	/*=====================================*/
	
	/*===== interface declaration =====*/
	interface SP_ios;
		`ifdef UART0
			interface RS232_PHY_Ifc uart0_coe;
		`endif
		`ifdef UART1
			interface RS232 uart1_coe;
		`endif
		`ifdef PLIC
			(*always_ready,always_enabled*)
			method Action gpio_in (Vector#(`IONum,Bit#(1)) inp);
			(*always_ready,always_enabled*)
			method Vector#(`IONum,Bit#(1))   gpio_out;
			(*always_ready,always_enabled*)
			method Vector#(`IONum,Bit#(1))   gpio_out_en;
		`endif
		`ifdef I2C0
			interface I2C_out i2c0_out;
		`endif
		`ifdef I2C1
			interface I2C_out i2c1_out;
		`endif
		`ifdef QSPI0 
			interface QSPI_out qspi0_out; 
		`endif
      `ifdef QSPI1 
			interface QSPI_out qspi1_out; 
		`endif
		`ifdef AXIEXP
			interface Get#(Bit#(67)) axiexp1_out;
			interface Put#(Bit#(67)) axiexp1_in;
		`endif
    `ifdef PWM_AXI4Lite
      interface PWMIO pwm_o;
    `endif
	endinterface
	interface Ifc_slow_peripherals;
		interface AXI4_Slave_IFC#(`PADDR,`Reg_width,`USERSPACE) axi_slave;
		interface SP_ios slow_ios;
		`ifdef CLINT
			method Bit#(1) msip_int;
			method Bit#(1) mtip_int;
			method Bit#(`Reg_width) mtime;
		`endif
		`ifdef PLIC method ActionValue#(Tuple2#(Bool,Bool)) intrpt_note; `endif
		`ifdef I2C0	method Bit#(1) i2c0_isint; `endif
		`ifdef I2C1	method Bit#(1) i2c1_isint; `endif
		`ifdef QSPI0 method Bit#(1) qspi0_isint; `endif
		`ifdef QSPI1 method Bit#(1) qspi1_isint; `endif
		`ifdef UART0 method Bit#(1) uart0_intr; `endif
    // NEEL EDIT
    interface IOCellSide iocell_side; // mandatory interface
    interface GPIO_config#(3) pad_configa; // depends on the number of banks
    // NEEL EDIT OVER
	endinterface
	/*================================*/

	function Tuple2#(Bool, Bit#(TLog#(Num_Slow_Slaves))) fn_address_mapping (Bit#(`PADDR) addr);
		`ifdef UART0
			if(addr>=`UART0Base && addr<=`UART0End)
				return tuple2(True,fromInteger(valueOf(Uart0_slave_num)));
			else
		`endif
		`ifdef UART1
			if(addr>=`UART1Base && addr<=`UART1End)
				return tuple2(True,fromInteger(valueOf(Uart1_slave_num)));
			else
		`endif
		`ifdef CLINT
			if(addr>=`ClintBase && addr<=`ClintEnd)
				return tuple2(True,fromInteger(valueOf(CLINT_slave_num)));
			else
		`endif
		`ifdef PLIC
			if(addr>=`PLICBase && addr<=`PLICEnd)
				return tuple2(True,fromInteger(valueOf(Plic_slave_num)));
			else if(addr>=`GPIOBase && addr<=`GPIOEnd)
				return tuple2(True,fromInteger(valueOf(GPIO_slave_num)));
			else
		`endif
		`ifdef I2C0
			if(addr>=`I2C0Base && addr<=`I2C0End)	
				return tuple2(True,fromInteger(valueOf(I2c0_slave_num)));
			else
		`endif
		`ifdef I2C1
			if(addr>=`I2C1Base && addr<=`I2C1End)
				return tuple2(True,fromInteger(valueOf(I2c1_slave_num)));
			else
		`endif
		`ifdef QSPI0
			if(addr>=`QSPI0CfgBase && addr<=`QSPI0CfgEnd)
				return tuple2(True,fromInteger(valueOf(Qspi0_slave_num)));
			else if(addr>=`QSPI0MemBase && addr<=`QSPI0MemEnd)
				return tuple2(True,fromInteger(valueOf(Qspi0_slave_num)));
			else
		`endif
		`ifdef QSPI1
			if(addr>=`QSPI1CfgBase && addr<=`QSPI1CfgEnd)
				return tuple2(True,fromInteger(valueOf(Qspi1_slave_num)));
			else if(addr>=`QSPI1MemBase && addr<=`QSPI1MemEnd)
				return tuple2(True,fromInteger(valueOf(Qspi1_slave_num)));
			else
		`endif
		`ifdef AXIEXP
			if(addr>=`AxiExp1Base && addr<=`AxiExp1End)
				return tuple2(True,fromInteger(valueOf(AxiExp1_slave_num)));
			else
		`endif
    `ifdef PWM_AXI4Lite
      if(addr>=`PWMBase && addr<=`PWMEnd)
        return tuple2(True,fromInteger(valueOf(Pwm_slave_num)));
      else
    `endif

    // NEEL EDIT 
      // give slave number and adress map to whatever peripherals you instantiate on the AXI4_Lite
      // slave.
    // NEEL EDIT OVER
		return tuple2(False,?);
	endfunction

	(*synthesize*)
	module mkslow_peripherals#(Clock fast_clock, Reset fast_reset, Clock uart_clock, Reset uart_reset
  `ifdef PWM_AXI4Lite ,Clock ext_pwm_clock `endif )(Ifc_slow_peripherals);
		Clock sp_clock <-exposeCurrentClock; // slow peripheral clock
		Reset sp_reset <-exposeCurrentReset; // slow peripheral reset

		/*======= Module declarations for each peripheral =======*/
		`ifdef UART0
			Uart16550_AXI4_Lite_Ifc uart0 <- mkUart16550(clocked_by uart_clock, reset_by uart_reset, sp_clock, sp_reset);
		`endif
		`ifdef UART1
			Ifc_Uart_bs uart1 <- mkUart_bs(clocked_by uart_clock, reset_by uart_reset,sp_clock, sp_reset);
		`endif
		`ifdef CLINT
			Ifc_clint				clint				<- mkclint();
		`endif
		`ifdef PLIC
			Ifc_PLIC_AXI	plic <- mkplicperipheral();
         Wire#(Bit#(TLog#(`INTERRUPT_PINS))) interrupt_id <- mkWire();
			Vector#(`INTERRUPT_PINS, FIFO#(bit)) ff_gateway_queue <- replicateM(mkFIFO);
			GPIO						gpio				<- mkgpio;
		`endif
		`ifdef I2C0 
			I2C_IFC					i2c0				<- mkI2CController();
		`endif
		`ifdef I2C1
			I2C_IFC					i2c1				<- mkI2CController();
		`endif
		`ifdef QSPI0 
			Ifc_qspi			qspi0				<-	mkqspi(); 
		`endif
		`ifdef QSPI1 
			Ifc_qspi			qspi1				<-	mkqspi(); 
		`endif
		`ifdef AXIEXP
			Ifc_AxiExpansion		axiexp1			<- mkAxiExpansion();	
		`endif
    `ifdef PWM_AXI4Lite
      Ifc_PWM_bus pwm_bus <- mkPWM_bus(ext_pwm_clock);
    `endif
    // NEEL EDIT
    Ifc_pinmux pinmux <- mkpinmux; // mandatory
    MUX#(3) mymux <- mkmux(); // mandatory. number depends on the number of instances required.
    GPIO#(3) mygpioa <- mkgpio(); // optional. depends the number of IO pins declared before.
    // NEEL EDIT OVER
		/*=======================================================*/

   	AXI4_Lite_Fabric_IFC #(1, Num_Slow_Slaves, `PADDR, `Reg_width,`USERSPACE)	slow_fabric <- 
                                                            mkAXI4_Lite_Fabric(fn_address_mapping);
		Ifc_AXI4Lite_AXI4_Bridge bridge	<-mkAXI4Lite_AXI4_Bridge(fast_clock,fast_reset);
   	
		mkConnection (bridge.axi4_lite_master,	slow_fabric.v_from_masters [0]);
		/*======= Slave connections to AXI4Lite fabric =========*/
		`ifdef UART0
			mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(Uart0_slave_num))],	
                    uart0.slave_axi_uart);  
		`endif
		`ifdef UART1
	   	mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(Uart1_slave_num))],	
                    uart1.slave_axi_uart); 
		`endif
		`ifdef CLINT
			mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(CLINT_slave_num))],
                    clint.axi4_slave);
		`endif
		`ifdef PLIC
			mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(Plic_slave_num))],	
                    plic.axi4_slave_plic); //
			mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(GPIO_slave_num))],	
                    gpio.axi_slave); //
		`endif
		`ifdef I2C0
   		mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(I2c0_slave_num))],	
                    i2c0.slave_i2c_axi); 
		`endif
		`ifdef I2C1
   		mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(I2c1_slave_num))],		
                    i2c1.slave_i2c_axi); // 
		`endif
  		`ifdef QSPI0 
			mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(Qspi0_slave_num))],	
                    qspi0.slave); 
		`endif
  		`ifdef QSPI1 
			mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(Qspi1_slave_num))],	
                    qspi1.slave); 
		`endif
		`ifdef AXIEXP
   		mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(AxiExp1_slave_num))],	
                    axiexp1.axi_slave); //
		`endif
    `ifdef PWM_AXI4Lite
      mkConnection (slow_fabric.v_to_slaves [fromInteger(valueOf(Pwm_slave_num))],
                    pwm_bus.axi4_slave);
    `endif

    // NEEL EDIT
    mkConnection (slow_fabric.v_from_masters[fromInteger(valueOf(Muxa_slave_num))], mymux.axi_slave);
    mkConnection (slow_fabric.v_from_masters[fromInteger(valueOf(Gpioa_slave_num))], gpioa.axi_slave);
    rule connect_select_lines_pinmux;// mandatory
      pinmux.cell0_mux(mymux.mux_config[0]);  
      pinmux.cell1_mux(mymux.mux_config[1]);  
      pinmux.cell2_mux(mymux.mux_config[2]);  
    endrule
    rule connect_uart1tx;
      pinmux.peripheral_side.uart_tx(uart1.coe_rs232.rs232.sout);
    endrule
    rule connect_uart1rx;
      uart1.coe_rs232.rs232.sin(pinmux.peripheral_side.uart_rx);
    endrule
    rule connect_gpioa;
      pinmux.peripheral_side.gpioa_a0_out(gpio.func.gpio_out[0]);
      pinmux.peripheral_side.gpioa_a0_outen(gpio.func.gpio_out_en[0]);
	  	Vector#(3,Bit#(1)) temp;
	  	temp[0]=pinmux.peripheral_side.gpioa_a0_in;
	  	temp[1]=pinmux.peripheral_side.gpioa_a1_in;
	  	temp[2]=pinmux.peripheral_side.gpioa_a2_in;
      gpio.pad_config.gpio_in(temp);
    endrule
    // NEEL EDIT OVER
		/*=======================================================*/
		/*=================== PLIC Connections ==================== */
		`ifdef PLIC
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
         rule rl_connect_i2c0_to_plic;
				`ifdef I2C0
					if(i2c0.isint()==1'b1) begin
						ff_gateway_queue[8].enq(1);
						plic.ifc_external_irq[8].irq_frm_gateway(True);
					end
				`else
					ff_gateway_queue[8].enq(0);
            `endif
         endrule

			rule rl_connect_i2c1_to_plic;
				`ifdef I2C1
					if(i2c1.isint()==1'b1) begin
						ff_gateway_queue[9].enq(1);
						plic.ifc_external_irq[9].irq_frm_gateway(True);
					end
            `else
					ff_gateway_queue[9].enq(0);
            `endif
			endrule

         rule rl_connect_i2c0_timerint_to_plic;
				`ifdef I2C0
					if(i2c0.timerint()==1'b1) begin
						ff_gateway_queue[10].enq(1);
						plic.ifc_external_irq[10].irq_frm_gateway(True);
					end
            `else
					ff_gateway_queue[10].enq(0);
            `endif
			endrule

         rule rl_connect_i2c1_timerint_to_plic;
				`ifdef I2C1
					if(i2c1.timerint()==1'b1) begin
						ff_gateway_queue[11].enq(1);
						plic.ifc_external_irq[11].irq_frm_gateway(True);
					end
            `else
					ff_gateway_queue[11].enq(0);
            `endif
         endrule

         rule rl_connect_i2c0_isber_to_plic;
				`ifdef I2C0
					if(i2c0.isber()==1'b1) begin
						ff_gateway_queue[12].enq(1);
						plic.ifc_external_irq[12].irq_frm_gateway(True);
					end
            `else
					ff_gateway_queue[12].enq(0);
            `endif
         endrule

         rule rl_connect_i2c1_isber_to_plic;
				`ifdef I2C1
					if(i2c1.isber()==1'b1) begin
						ff_gateway_queue[13].enq(1);
						plic.ifc_external_irq[13].irq_frm_gateway(True);
               end
            `else
					ff_gateway_queue[13].enq(0);
            `endif
         endrule

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
				SyncBitIfc#(Bit#(1)) uart0_interrupt <-mkSyncBitToCC(uart_clock,uart_reset); 
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
		interface SP_ios slow_ios;
			`ifdef UART0
				interface uart0_coe=uart0.coe_rs232;
			`endif
			`ifdef UART1
				interface uart1_coe=uart1.coe_rs232;
			`endif
			`ifdef PLIC
				method Action gpio_in (Vector#(`IONum,Bit#(1)) inp)=gpio.gpio_in(inp);
				method Vector#(`IONum,Bit#(1))   gpio_out=gpio.gpio_out;
				method Vector#(`IONum,Bit#(1))   gpio_out_en=gpio.gpio_out_en;
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
		endinterface
    // NEEL EDIT
    interface iocell_side=pinmux.iocell_side;
    interface pad_configa= gpioa.pad_config;
    // NEEL EDIT OVER
		/*===================================*/
	endmodule
endpackage
