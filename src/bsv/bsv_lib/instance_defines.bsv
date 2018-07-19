`define ADDR 32
`define DATA 64
`define USERSPACE 0
`define PADDR 32
`define Reg_width 64
`define PRFDEPTH 6
`define VADDR 39
`define DCACHE_BLOCK_SIZE 4
`define DCACHE_WORD_SIZE 8
`define PERFMONITORS                            64
`define DCACHE_WAYS 4
`define DCACHE_TAG_BITS 20      // tag_bits = 52
`define PLIC
	`define PLICBase		'h0c000000
	`define PLICEnd		'h10000000
`define INTERRUPT_PINS 64

`define UART1 enable
    `define UART1Base       'h00011300
    `define UART1End        'h000113FF // 2 32-bit registers

`define BAUD_RATE 130
`ifdef simulate
  `define BAUD_RATE 5 //130 //
`endif

`define I2C0 enable
    `define I2C0Base        'h00011400
    `define I2C0End     'h000114FF // 8 32-bit registers


`define QSPI0 enable
    `define QSPI0CfgBase    'h00011800
    `define QSPI0CfgEnd  'h000118FF // 13 32-bit registers
    `define QSPI0MemBase    'h90000000
    `define QSPI0MemEnd  'h9FFFFFFF // 256 MB

  `define PWMBase      'h00011A00
  `define PWMEnd       'h00011A0C // 4 32-bit registers

//`define PWM_AXI4Lite enable

