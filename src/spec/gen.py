import os
import os.path
from spec.interfaces import Pinouts


def specgen(of, pth, pinouts, bankspec, pinbanks, fixedpins):
    """ generates a specification of pinouts (tsv files)
        for reading in by pinmux
    """
    pth = pth or ''
    #print bankspec.keys()
    #print fixedpins.keys()
    if not os.path.exists(pth):
        os.makedirs(pth)
    with open(os.path.join(pth, 'interfaces.txt'), 'w') as f:
        for k in pinouts.fnspec.keys():
            s = pinouts.fnspec[k]
            f.write("%s\t%d\n" % (k.lower(), len(s)))
            s0 = s[s.keys()[0]]  # hack, take first
            with open(os.path.join(pth, '%s.txt' % k.lower()), 'w') as g:
                if len(s0.pingroup) == 1:  # only one function, grouped higher
                    for ks in s.keys():  # grouped by interface
                        assert False, "TODO, single-function"
                        fntype = 'inout'  # XXX TODO
                        k = s[ks].suffix
                        k_ = k.lower()
                        g.write("%s\t%s\n" % (k_, fntype))
                else:
                    for pinname in s0.pingroup:
                        fntype = s0.fntype.get(pinname, 'inout')
                        pn = pinname.lower()
                        g.write("%s\t%s\n" % (pn, fntype))

    pks = sorted(pinouts.keys())

    # truly dreadful way to work out the max mux size...
    muxsz = 0
    for k in pks:
        for m in pinouts[k].keys():
            muxsz = max(muxsz, m + 1)

    # write out the mux...
    with open(os.path.join(pth, 'pinmap.txt'), 'w') as g:
        for k in pks:
            res = [str(k)]
            # append pin mux
            for midx in range(muxsz):
                if midx in pinouts[k]:
                    fname = pinouts[k][midx][0]
                else:
                    fname = ''
                res.append(fname.lower())
            g.write('\t'.join(res) + '\n')

    # ... and the dedicated pins
    with open(os.path.join(pth, 'fixedpins.txt'), 'w') as g:
        for p in fixedpins:
            p = map(str, p)
            p = map(str.lower, p)
            g.write('\t'.join(p) + '\n')

    # lists bankspec, shows where the pin-numbers *start*
        of.write("# Pin Bank starting points and lengths\n\n")
    with open(os.path.join(pth, 'pinspec.txt'), 'w') as g:
        for bank, pinstart in bankspec.items():
            of.write("* %s %d %d\n" % (bank, pinstart, pinbanks[bank]))
            g.write("%s\t%d\t%d\n" % (bank, pinstart, pinbanks[bank]))
