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
package fast_memory_map;
    /*====== Package imports === */
    `include "instance_defines.bsv"
    `include "core_parameters.bsv"

    /*====== Fast peripherals Memory Map ======= */
{0}

    /*====== AXI4 slave declarations =======*/
{1}

    /*====== AXI4 Master declarations =======*/
{2}



function Tuple2 #(Bool, Bit#(TLog#(Num_Fast_Slaves)))
                fn_addr_to_fastslave_num  (Bit#(`PADDR) addr);

    if(addr>=`SDRAMMemBase && addr<=`SDRAMMemEnd)
        return tuple2(True,fromInteger(valueOf(Sdram_slave_num)));
    else if(addr>=`DebugBase && addr<=`DebugEnd)
        return tuple2(True,fromInteger(valueOf(Debug_slave_num)));
    `ifdef SDRAM
        else if(addr>=`SDRAMCfgBase && addr<=`SDRAMCfgEnd )
            return tuple2(True,fromInteger(valueOf(Sdram_cfg_slave_num)));
    `endif
    `ifdef BOOTROM
        else if(addr>=`BootRomBase && addr<=`BootRomEnd)
            return tuple2(True,fromInteger(valueOf(BootRom_slave_num)));
    `endif
    `ifdef DMA
        else if(addr>=`DMABase && addr<=`DMAEnd)
            return tuple2(True,fromInteger(valueOf(Dma_slave_num)));
    `endif
    `ifdef VME
        else if(addr>=`VMEBase && addr<=`VMEEnd)
            return tuple2(True,fromInteger(valueOf(VME_slave_num)));
    `endif
    `ifdef TCMemory
        else if(addr>=`TCMBase && addr<=`TCMEnd)
            return tuple2(True,fromInteger(valueOf(TCM_slave_num)));
    `endif
        else 
{3}
            return tuple2(False,?);
endfunction

endpackage
