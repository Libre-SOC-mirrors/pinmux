/*
Copyright (c) 2013, IIT Madras
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

*  Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.
*  Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
*  Neither the name of IIT Madras  nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
-------------------------------------------------------------------
*/
package Soc;
    /*====== Package imports === */
    import FIFO::*;
    import FIFOF::*;
    import SpecialFIFOs::*;
    import GetPut::*;
    import ClientServer::*;
    import Vector::*;
    import Connectable::*;
    import Clocks::*;
    /*========================== */
    /*=== Project imports === */
    import ConcatReg::*;
    import AXI4_Types::*;
    import AXI4_Fabric::*;
    import defined_types::*;
    import MemoryMap		 :: *;
    import slow_peripherals::*;
`ifdef DEBUG
    `include "defines.bsv"
`endif
    `include "instance_defines.bsv"
{8}
    /*====== AXI4 slave declarations =======*/
{3}
    /*====== AXI4 Master declarations =======*/
{4}


    `ifdef DMA
        import DMA				 :: *;
    `endif
    `ifdef BOOTROM
        import BootRom			::*;
    `endif
    `ifdef SDRAM
        import sdr_top			 :: *;
    `endif
    `ifdef BRAM
        import Memory_AXI4	::*;
    `endif
    `ifdef TCMemory
        import TCM::*;
    `endif
    `ifdef Debug
        import DebugModule::*;
    `else
        import core::*;
    `endif
    `ifdef  VME
        import vme_top ::*;
    `endif

    `ifdef VME
        import vme_master::*;
    `endif
    `ifdef FlexBus
        import FlexBus_Types::*;
    `endif
{0}

    /*========================= */
    interface Ifc_Soc;
        interface SP_ios slow_ios;
        (*always_ready,always_enabled*)
        method Action boot_sequence(Bit#(1) bootseq);
            
        `ifdef SDRAM 
            (*always_ready*) interface Ifc_sdram_out sdram_out; 
        `endif
        ifdef DDR
            (*prefix="M_AXI"*) interface
                   AXI4_Master_IFC#(`PADDR, `Reg_width, `USERSPACE) master;
        `endif
        `ifdef HYPER
             (*always_ready,always_enabled*)	
             interface Ifc_flash ifc_flash;
        `endif
        /*=============================================== */
        `ifdef VME
             interface Vme_out  proc_ifc;
             interface Data_bus_inf proc_dbus;
        `endif
{1}
    endinterface

    (*synthesize*)
    module mkSoc #(Bit#(`VADDR) reset_vector,
                 Clock slow_clock, Reset slow_reset, Clock uart_clock, 
                 Reset uart_reset, Clock clk0, Clock tck, Reset trst
                 `ifdef PWM_AXI4Lite ,Clock ext_pwm_clock `endif )(Ifc_Soc);
        Clock core_clock <-exposeCurrentClock; // slow peripheral clock
        Reset core_reset <-exposeCurrentReset; // slow peripheral reset
{2}
        `ifdef Debug 
            Ifc_DebugModule core<-mkDebugModule(reset_vector);
        `else
            Ifc_core_AXI4 core <-mkcore_AXI4(reset_vector);
        `endif
        `ifdef BOOTROM
            BootRom_IFC bootrom <-mkBootRom;
        `endif
        `ifdef SDRAM
            Ifc_sdr_slave sdram<- mksdr_axi4_slave(clk0);
        `endif
        `ifdef BRAM
            Memory_IFC#(`SDRAMMemBase,`Addr_space)main_memory <- 
                        mkMemory("code.mem.MSB","code.mem.LSB","MainMEM");
        `endif
        `ifdef TCMemory
            Ifc_TCM					tcm				<- mkTCM;	
        `endif
        `ifdef DMA
            DmaC#(7,`NUM_DMACHANNELS) dma	<- mkDMA();
        `endif
            `ifdef VME
            Ifc_vme_top             vme             <-mkvme_top();
            `endif	
        Ifc_slow_peripherals slow_peripherals <-mkslow_peripherals(
                          core_clock, core_reset, uart_clock, 
                          uart_reset, clocked_by slow_clock ,
                          reset_by slow_reset 
                          `ifdef PWM_AXI4Lite , ext_pwm_clock `endif );	

        // Fabric
        AXI4_Fabric_IFC #(Num_Masters, Num_Slaves,
                          `PADDR, `Reg_width,`USERSPACE)
                        fabric <- mkAXI4_Fabric(fn_addr_to_slave_num);

        // Connect traffic generators to fabric
        mkConnection (core.dmem_master,fabric.v_from_masters
                              [fromInteger(valueOf(Dmem_master_num))]);
        mkConnection (core.imem_master,	fabric.v_from_masters 
                              [fromInteger(valueOf(Imem_master_num))]);
        `ifdef Debug
            mkConnection (core.debug_master, fabric.v_from_masters 
                              [fromInteger(valueOf(Debug_master_num))]);
        `endif
        `ifdef DMA
         mkConnection (dma.mmu, fabric.v_from_masters
                              [fromInteger(valueOf(DMA_master_num))]);
        `endif


        // Connect fabric to memory slaves
            `ifdef Debug
                mkConnection (fabric.v_to_slaves 
                              [fromInteger(valueOf(Debug_slave_num))],
                              core.debug_slave);
            `endif
            `ifdef SDRAM	
                mkConnection (fabric.v_to_slaves 
                              [fromInteger(valueOf(Sdram_slave_num))],	
                              sdram.axi4_slave_sdram); // 
            mkConnection (fabric.v_to_slaves 
                              [fromInteger(valueOf(Sdram_cfg_slave_num))],
                              sdram.axi4_slave_cntrl_reg); // 
      `endif
      `ifdef BRAM
                mkConnection(fabric.v_to_slaves
                              [fromInteger(valueOf(Sdram_slave_num))],
                              main_memory.axi_slave);
            `endif
            `ifdef BOOTROM
                mkConnection (fabric.v_to_slaves 
                              [fromInteger(valueOf(BootRom_slave_num))],
                              bootrom.axi_slave);
            `endif
            `ifdef DMA
            mkConnection (fabric.v_to_slaves 
                              [fromInteger(valueOf(Dma_slave_num))],	
                              dma.cfg); //DMA slave
            `endif
            `ifdef TCMemory
                mkConnection (fabric.v_to_slaves 
                              [fromInteger(valueOf(TCM_slave_num))],
                              tcm.axi_slave);
            `endif
            mkConnection(fabric.v_to_slaves 
                              [fromInteger(valueOf(SlowPeripheral_slave_num))],
                              slow_peripherals.axi_slave);
            `ifdef VME
                mkConnection (fabric.v_to_slaves
                              [fromInteger(valueOf(VME_slave_num))],
                              vme.slave_axi_vme);
            `endif

//          pin connections
{9}

            // fabric connections
{5}

            `ifdef DMA
            // rule to connect all interrupt lines to the DMA
            // All the interrupt lines to DMA are active
            // HIGH. For peripherals that are not connected,
            // or those which do not
            // generate an interrupt (like TCM), drive a constant 1 
            // on the corresponding interrupt line.
{7}
            `endif


        /*==== Synchornization between the JTAG and the Debug Module ===== */
        `ifdef Debug
            SyncFIFOIfc#(Bit#(40)) sync_request_to_dm <-
                                        mkSyncFIFOToCC(1,tck,trst);
            SyncFIFOIfc#(Bit#(34)) sync_response_from_dm <-
                                        mkSyncFIFOFromCC(1,tck);
            rule connect_tap_request_to_syncfifo;
                let x<-tap.request_to_dm;
                sync_request_to_dm.enq(x);
            endrule
            rule read_synced_request_to_dm;
                sync_request_to_dm.deq;
                core.request_from_dtm(sync_request_to_dm.first);
            endrule

            rule connect_debug_response_to_syncfifo;
                let x<-core.response_to_dtm;
                sync_response_from_dm.enq(x);
            endrule
            rule read_synced_response_from_dm;
                sync_response_from_dm.deq;
                tap.response_from_dm(sync_response_from_dm.first);
            endrule
        `endif
        /*============================================================ */
    
        `ifdef FlexBus
            //rule drive_flexbus_inputs;
               //flexbus.flexbus_side.m_TAn(1'b1);
               //flexbus.flexbus_side.m_din(32'haaaaaaaa);
            //endrule
         `endif

        `ifdef CLINT
            SyncBitIfc#(Bit#(1)) clint_mtip_int <-
                                        mkSyncBitToCC(slow_clock,slow_reset);
            SyncBitIfc#(Bit#(1)) clint_msip_int <-
                                        mkSyncBitToCC(slow_clock,slow_reset);
            Reg#(Bit#(`Reg_width)) clint_mtime_value <-
                                        mkSyncRegToCC(0,slow_clock,slow_reset);
            rule synchronize_clint_data;
                clint_mtip_int.send(slow_peripherals.mtip_int);
                clint_msip_int.send(slow_peripherals.msip_int);
                clint_mtime_value<=slow_peripherals.mtime;
            endrule
            rule connect_msip_mtip_from_clint;
                core.clint_msip(clint_msip_int.read);
                core.clint_mtip(clint_mtip_int.read);
            core.clint_mtime(clint_mtime_value);
            endrule
        `endif
        `ifdef PLIC
            Reg#(Tuple2#(Bool,Bool)) plic_interrupt_note <-
                                        mkSyncRegToCC(tuple2(False,False),
                                                      slow_clock,slow_reset);
            rule synchronize_interrupts;
                let note <- slow_peripherals.intrpt_note;
                plic_interrupt_note<=note;
            endrule
            rule rl_send_external_interrupt_to_csr;
                core.set_external_interrupt(plic_interrupt_note);
            endrule
        `endif

        `ifdef VME
            interface  proc_ifc = vme.proc_ifc;
            interface   proc_dbus = vme.proc_dbus;
        `endif 
         method Action boot_sequence(Bit#(1) bootseq) = 
                            core.boot_sequence(bootseq);
        `ifdef SDRAM
            interface sdram_out=sdram.ifc_sdram_out;
        `endif
        `ifdef DDR
          interface master=fabric.v_to_slaves
                                [fromInteger(valueOf(Sdram_slave_num))];
        `endif
        interface slow_ios=slow_peripherals.slow_ios;
{6}
    endmodule
endpackage
