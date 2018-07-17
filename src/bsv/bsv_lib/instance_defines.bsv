`define ADDR 32
`define DATA 64
`define USERSPACE 0
`define PADDR 32
`define Reg_width 64
`define PRFDEPTH 6
`define VADDR 39
`define UART1 enable
`define DCACHE_BLOCK_SIZE 4
`define DCACHE_WORD_SIZE 8
`define PERFMONITORS                            64
`define DCACHE_WAYS 4
`define DCACHE_TAG_BITS 20      // tag_bits = 52

    `define UART1Base       'h00011300
    `define UART1End        'h000113FF // 2 32-bit registers

`define BAUD_RATE 130
`ifdef simulate
  `define BAUD_RATE 5 //130 //
`endif


//`define PWM_AXI4Lite enable

