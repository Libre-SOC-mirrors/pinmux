/*
Copyright (c) 2013, IIT Madras
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

*  Redistributions of source code must retain the above copyright notice,
    this list of conditions and the following disclaimer.
*  Redistributions in binary form must reproduce the above copyright notice,
    this list of conditions and the following disclaimer in the documentation
    and/or other materials provided with the distribution.
*  Neither the name of IIT Madras  nor the names of its contributors may be
    used to endorse or promote products derived from this software without
    specific prior written permission.

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
-------------------------------------------------------------------------------------------------

Code inpired by the pwm module at: https://github.com/freecores/pwm

*/
package pwm_instance;
  /*=== Project imports ==*/
  import Clocks::*;
  /*======================*/
  /*== Package imports ==*/
  //import defined_types::*;
  `include "instance_defines.bsv"
  import ClockDiv::*;
  import ConcatReg::*;
	import Semi_FIFOF::*;
	import BUtils ::*;
  `ifdef PWM_AXI4Lite
  	import AXI4_Lite_Types::*;
  `endif
    import pwm::*;
  /*======================*/

  `ifdef PWM_AXI4Lite
    // the following interface and module will add the
    // AXI4Lite interface to the PWM module
    interface Ifc_PWM_bus_real;
      interface Ifc_PWM_bus pwmbus;
    endinterface

    //(*synthesize*)
    module mkPWM_real#(Clock ext_clock)(Ifc_PWM_bus);
      Ifc_PWM_bus pwmbus <-mkPWM_bus(ext_clock, 32);
      interface pwm_io = pwmbus.pwm_io.io;
      interface axi4_slave = pwmbus.axi4_slave;
    endmodule
  `endif

endpackage
