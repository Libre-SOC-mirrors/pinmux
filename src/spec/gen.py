import os
import os.path
from spec.interfaces import Pinouts


def specgen(of, pth, pinouts, bankspec, muxwidths, pinbanks, fixedpins,
            fastbus):
    """ generates a specification of pinouts (tsv files)
        for reading in by pinmux.

        files generated:
        * interfaces.txt - contains name and number of interfaces
        * {interfacename}.txt - contains name of pin, type, and bus

        type may be in, out or inout.
        if type is "inout" then a THIRD optional parameter of type
        "bus" indicates whether the bus is ganged together.  in
        future this may be "bus1", "bus2" and so on if an interface
        contains more than one ganged group.

        basically if the function needs to control whether a group
        of pins shall be switched from input to output (as opposed
        to the *pinmux* via user control deciding that), bus is
        the way to indicate it.
    """
    pth = pth or ''
    #print bankspec.keys()
    #print fixedpins.keys()
    #print pinouts.ganged.items()
    if not os.path.exists(pth):
        os.makedirs(pth)
    with open(os.path.join(pth, 'interfaces.txt'), 'w') as f:
        for k in pinouts.fnspec.keys():
            s = pinouts.fnspec[k]
            line = [k.lower(), str(len(s))]
            for b in fastbus:
                if b.startswith(k.lower()):
                    line.append(b)
            line = '\t'.join(line)
            f.write("%s\n" % line)
            s0 = s[list(s.keys())[0]]  # hack, take first
            gangedgroup = pinouts.ganged[k]
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
                        g.write("%s\t%s" % (pn, fntype))
                        if fntype == 'inout' and pinname in gangedgroup:
                            g.write("\tbus")
                        g.write("\n")

    # work out range of bankspecs
    bankpins = []
    for k, v in bankspec.items():
        bankpins.append((v, k))
    bankpins.sort()
    bankpins.reverse()
    muxentries = {}
    cellbank = {}

    pks = sorted(pinouts.keys())

    # truly dreadful way to work out the max mux size...
    for k in pks:
        for (sz, bname) in bankpins:
            print "keys", k, sz, bname
            if k >= sz:
                print "found", bname
                muxentries[k] = muxwidths[bname]
                cellbank[k] = bname
                break

    print muxentries
    # write out the mux...
    with open(os.path.join(pth, 'pinmap.txt'), 'w') as g:
        for k in pks:
            muxsz = muxentries[k]
            bank = cellbank[k]
            res = [str(k), bank, str(muxsz)]
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
        keys = sorted(bankspec.keys())
        for bank in keys:
            pinstart = bankspec[bank]
            wid = muxwidths[bank]
            of.write("* %s %d %d %d\n" % (bank, pinstart, pinbanks[bank], wid))
            g.write("%s\t%d\t%d\t%d\n" % (bank, pinstart, pinbanks[bank], wid))
