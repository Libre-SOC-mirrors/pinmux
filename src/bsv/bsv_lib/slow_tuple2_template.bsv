package slow_memory_map;
	/*===== Project imports =====*/
	import defined_types::*;
	`include "instance_defines.bsv"
    /* ==== define the AXI Addresses ==== */
{0}

    /* ==== define the AXI slave numbering ===== */
{1}

    /* ==== define the number of slow peripheral irqs ==== */

	function Tuple2#(Bool, Bit#(TLog#(Num_Slow_Slaves)))
                     fn_slow_address_mapping (Bit#(`PADDR) addr);
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
{2}
        return tuple2(False,?);
	endfunction

endpackage
