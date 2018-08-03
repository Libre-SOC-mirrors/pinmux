from bsv.peripheral_gen.base import PBase


class sdram(PBase):

    def slowimport(self):
        return "import sdr_top::*;"

    def num_axi_regs32(self):
        return [0x400000,  # defines an entire memory range (hack...)
                12]        # defines the number of configuration regs

    def extfastifinstance(self, name, count):
        return "// TODO" + self._extifinstance(name, count, "_out", "", True,
                                               ".if_sdram_out")

    def fastifdecl(self, name, count):
        return "// (*always_ready*) interface " + \
            "Ifc_sdram_out sdr{0}_out;".format(count)

    def get_clk_spc(self, typ):
        return "clk0, rst0"

    def get_clock_reset(self, name, count):
        return "slow_clock, slow_reset"

    def mkfast_peripheral(self):
        return "Ifc_sdr_slave sdr{0} <- mksdr_axi4_slave(clk0, rst0);"

    def _mk_connection(self, name=None, count=0):
        return ["sdr{0}.axi4_slave_sdram",
                "sdr{0}.axi4_slave_cntrl_reg"]

    def pinname_out(self, pname):
        return {'sdrwen': 'ifc_sdram_out.osdr_we_n',
                'sdrcsn0': 'ifc_sdram_out.osdr_cs_n',
                'sdrcke': 'ifc_sdram_out.osdr_cke',
                'sdrclk': 'ifc_sdram_out.osdr_clock',
                'sdrrasn': 'ifc_sdram_out.osdr_ras_n',
                'sdrcasn': 'ifc_sdram_out.osdr_cas_n',
                }.get(pname, '')

    def _mk_clk_con(self, name, count, ctype):
        ret = [PBase._mk_clk_con(self, name, count, ctype)]
        for pname, sz, ptype in [
            ('dqm', 8, 'out'),
            ('ba', 2, 'out'),
            ('ad', 13, 'out'),
            ('d_out', 64, 'out'),
            ('d_in', 64, 'in'),
            ('d_out_en', 64, 'out'),
        ]:
            bitspec = "Bit#(%d)" % sz
            txt = self._mk_clk_vcon(name, count, ctype, ptype, pname, bitspec)
            ret.append(txt)
        return '\n'.join(ret)

    def _mk_pincon(self, name, count, typ):
        ret = [PBase._mk_pincon(self, name, count, typ)]
        assert typ == 'fast'  # TODO slow?
        for pname, stype, ptype in [
            ('dqm', 'osdr_dqm', 'out'),
            ('ba', 'osdr_ba', 'out'),
            ('ad', 'osdr_addr', 'out'),
            ('d_out', 'osdr_dout', 'out'),
            ('d_in', 'ipad_sdr_din', 'in'),
            ('d_out_en', 'osdr_den_n', 'out'),
        ]:
            ret.append(self._mk_vpincon(name, count, typ, ptype, pname,
                                        "ifc_sdram_out.{0}".format(stype)))

        return '\n'.join(ret)
