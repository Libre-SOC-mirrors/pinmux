#!/usr/bin/env python

from copy import deepcopy
from collections import OrderedDict
from math import pi
import os
import base64

cwd = os.path.split(os.path.abspath(__file__))[0]
lead_drawing = cwd + "/greatek_qfp_128L.png"
pack_drawing = cwd + "/greatek_qfp_128_fp.png"
c4m_drawing = cwd + "/c4mlogo.png"
ls180_drawing = cwd + "/ls180-img.png"

def bond_int_to_ext(pin, bank):
    """ note that internal numbering is 0-31 whereas the DISPLAY internal
        numbering is 1-32.  this uses the INTERNAL numbering.

        side: N S E W

        outer ring numbers: the python list order of the outer pads
        middle numbers: the package number wires (plus side they are on)
        inner numbers:  the IO pad *python internal (0-31)* numbers plus side

       0     1   2      3   N  34     35   36   37
      N102 N101 N100    99  N  68    N67  N66  N65
      W29  W30  W31     N0  N N31    E29  E30  E31

    25  103 W28                       E28  64 25
     W    W  W                         E  E   E
     0  128 W3                        E3  39  0

      W2  W1   W0      S0   S S31    E0   E1   E2
      S1  S2   S3       4   S  35    S36  S37  S38
       0     1   2      3   S  34     35   36   37

    """
    # returns side, order-on-the-side, pin number
    if bank == 'N':
        return 'N', pin+3, 99-pin
    if bank == 'S':
        return 'S', pin+3, 4+pin
    if bank == 'W':
        if pin >= 29: # 29, 30, 31
            return 'N', pin-29, 100+(31-pin)
        if pin <= 2: # 0, 1, 2
            return 'S', 2-pin, 3-pin
        return 'W', 28-pin, 103+(28-pin)
    if bank == 'E':
        if pin >= 29:
            return 'N', 35+(31-pin), 67-(31-pin)
        if pin <= 2:
            return 'S', pin+35, 36+pin
        return 'E', 28-pin, 39+(pin-3)


def create_sv(fname, pins):
    """unsophisticated drawer of an SVG
    """

    try:
        import svgwrite
    except ImportError:
        print ("WARNING, no SVG image, not producing image %s" % fname)
        return

    # create internal to external map
    bondmap = {'N': {}, 'S': {},  'E': {},  'W': {} }
    padside = {'pads.north': 'N', 'pads.east': 'E', 'pads.south': 'S',
               'pads.west': 'W'}
    sidepad = {}
    for pinpad, bank in padside.items():
        sidepad[bank] = pinpad
        for ipin in range(len(pins[pinpad])):
            eside, enum, epinnum = bond_int_to_ext(ipin, bank)
            bondmap[eside][enum] = (epinnum, ipin, bank)
    with open("/tmp/bondmap.txt", "w") as f:
        for k,v in bondmap.items():
            f.write("%s\n" % k)
            for enum, (epinnum, ipin, bank) in v.items():
                f.write("    %d %d  -> %s %d\n" % (enum, epinnum, bank, ipin))

    scale = 15
    outerscale = scale * 2.0

    width = len(pins['pads.north']) * scale
    height = len(pins['pads.east']) * scale
    woffs = scale*40#-width/2
    hoffs = scale*40#-height/2

    nepads = list(bondmap['N'].keys())
    nepads.sort()
    wepads = list(bondmap['W'].keys())
    wepads.sort()
    eepads = list(bondmap['E'].keys())
    eepads.sort()
    sepads = list(bondmap['S'].keys())
    sepads.sort()

    owoffs = woffs + (width/2) - len(nepads)/2 * outerscale
    ohoffs = hoffs + (height/2) - len(wepads)/2 * outerscale

    dwg = svgwrite.Drawing(fname, profile='full',
                           size=(width+scale*85, height+scale*80))

    # outer QFP rect
    dwg.add(dwg.rect((owoffs-scale*2.5, ohoffs-scale*4.5),
                        (len(nepads)*outerscale+scale*9,
                         len(wepads)*outerscale+scale*13),
            fill='white',
            stroke=svgwrite.rgb(0, 128, 0, '%'),
            stroke_width=scale/5.0))

    # inner lead rect
    dwg.add(dwg.rect((woffs-scale*2, hoffs-scale*2),
                        (width+scale*6, height+scale*6),
            stroke=svgwrite.rgb(16, 255, 16, '%'),
            stroke_width=scale/10.0))

    # record the inner line (iopad) position so that the outer one can
    # match with it
    innerpos = {'N': {}, 'S': {},  'E': {},  'W': {} }

    # create the inner diagram
    for i, pin in enumerate(pins['pads.west']):
        ht = hoffs + height - (i * scale) + scale*0.5
        endline = (woffs-scale*4.5, ht-scale*0.5)
        innerpos['W'][i] = endline
        dwg.add(dwg.line((woffs-scale*2, ht-scale*0.5),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        dwg.add(dwg.text(pin.upper(), insert=(woffs-scale*12, ht),
                         fill='black'))
        dwg.add(dwg.text("W%d" % (i+1), insert=(woffs-scale*1.5, ht),
                            fill='white'))

    for i, pin in enumerate(pins['pads.east']):
        ht = hoffs + height - (i * scale) + scale*0.5
        wd = width + woffs + scale*2
        endline = (wd+scale*4.5, ht-scale*0.5)
        innerpos['E'][i] = endline
        dwg.add(dwg.line((wd+scale*2, ht-scale*0.5),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        dwg.add(dwg.text(pin.upper(), insert=(wd+scale*5, ht-scale*0.25),
                         fill='black'))
        dwg.add(dwg.text("E%d" % (i+1), insert=(wd, ht-scale*0.25),
                            fill='white'))

    for i, pin in enumerate(pins['pads.north']):
        wd = woffs + i * scale + scale*1.5
        endline = (wd, hoffs-scale*4.5)
        innerpos['N'][i] = endline
        dwg.add(dwg.line((wd, hoffs-scale*2),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        pos=(wd, hoffs-scale*5.0)
        txt = dwg.text(pin.upper(), insert=pos, fill='black')
        txt.rotate(-90, pos)
        dwg.add(txt)
        pos=(wd+scale*0.25, hoffs-scale*0.25)
        txt = dwg.text("N%d" % (i+1), insert=pos, fill='white')
        txt.rotate(-90, pos)
        dwg.add(txt)

    for i, pin in enumerate(pins['pads.south']):
        wd = woffs + i * scale + scale*1.5
        ht = hoffs + height + scale*2
        endline = (wd, ht+scale*4.5)
        innerpos['S'][i] = endline
        dwg.add(dwg.line((wd, ht+scale*2),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        pos=(wd-scale*0.25, ht+scale*5.0)
        txt = dwg.text(pin.upper(), insert=pos, fill='black')
        txt.rotate(90, pos)
        dwg.add(txt)
        pos=(wd-scale*0.25, ht+scale*0.25)
        txt = dwg.text("S%d" % (i+1), insert=pos, fill='white')
        txt.rotate(90, pos)
        dwg.add(txt)

    # north outer pads
    for i in nepads:
        (epinnum, ipin, bank) = pad = bondmap['N'][i]
        wd = owoffs + i * outerscale + outerscale*1.5
        endline = (wd, ohoffs-outerscale*2)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos=(wd, ohoffs-outerscale*4.0)
        txt = dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                        insert=pos, fill='black')
        txt.rotate(-90, pos)
        dwg.add(txt)
        pos=(wd, ohoffs-outerscale*2.5)
        txt = dwg.text("%d N" % epinnum, insert=pos, fill='blue')
        txt.rotate(-90, pos)
        dwg.add(txt)

    # west outer pads
    for i in wepads:
        (epinnum, ipin, bank) = pad = bondmap['W'][i]
        ht = ohoffs + (i * outerscale) + outerscale*1.5
        endline = (owoffs+outerscale*0.5, ht)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos = (owoffs-outerscale*6.0, ht)
        dwg.add(dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                         pos,
                         fill='black'))
        pos = (owoffs-outerscale*1.0, ht)
        dwg.add(dwg.text("%d W" % epinnum, insert=pos,
                            fill='blue'))

    # south outer pads
    for i in sepads:
        (epinnum, ipin, bank) = pad = bondmap['S'][i]
        wd = owoffs + i * outerscale + outerscale*1.5
        ht = ohoffs + len(wepads)*outerscale + outerscale*4
        endline = (wd, ht)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos=(wd-outerscale*0.25, ht+outerscale*1.5)
        txt = dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                        insert=pos, fill='black')
        txt.rotate(90, pos)
        dwg.add(txt)
        pos=(wd-outerscale*0.25, ht+outerscale*0.5)
        txt = dwg.text("%d S" % epinnum, insert=pos, fill='blue')
        txt.rotate(90, pos)
        dwg.add(txt)

    # east outer pads
    for i in eepads:
        (epinnum, ipin, bank) = pad = bondmap['E'][i]
        ht = ohoffs + (i * outerscale) + outerscale*1.5
        wd = owoffs+len(nepads)*outerscale + outerscale*1
        endline = (wd+outerscale*0.5, ht)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos = (wd+outerscale*2.5, ht)
        dwg.add(dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                         pos,
                         fill='black'))
        pos = (wd+outerscale*1.0, ht)
        dwg.add(dwg.text("%d E" % epinnum, insert=pos,
                            fill='blue'))

    # add ls180 image
    image_data = open(ls180_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(width/2+woffs-225, height/2+hoffs-225)
    leads = svgwrite.image.Image(data, pos,
                                       size=(480,480))
    dwg.add(leads)

    # add QFP pack image in top-right
    image_data = open(pack_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(0, 0)
    leads = svgwrite.image.Image(data, pos,
                                       size=(327,300))
    dwg.add(leads)
    dwg.add(dwg.text("GREATEK QFP128L",
                       insert=(50,150),
                        font_size=20,
                     fill='black'))
    dwg.add(dwg.text("D/W J1-03128-001",
                       insert=(50,180),
                        font_size=20,
                     fill='black'))


    # add QFP lead image in centre
    sz=320
    image_data = open(lead_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(woffs+width+scale*23.5, 0)
    leads = svgwrite.image.Image(data, pos,
                                       size=(sz,sz))
    leads.rotate(-90, (pos[0]+sz/2, pos[1]+sz/2))
    dwg.add(leads)

    dwg.add(dwg.text("GREATEK ELECTRONICS INC.",
                       insert=(woffs+width+scale*29, scale*8),
                     fill='black'))
    dwg.add(dwg.text("INNER LEAD DRAWING",
                       insert=(woffs+width+scale*29, scale*9),
                     fill='black'))
    dwg.add(dwg.text("QFP 128L OPEN STAMPING",
                       insert=(woffs+width+scale*29, scale*10),
                     fill='black'))
    dwg.add(dwg.text("BODY 14x20x2.75mm",
                       insert=(woffs+width+scale*29, scale*11),
                     fill='black'))
    dwg.add(dwg.text("L/F PAD SIZE 236x236mil^2",
                       insert=(woffs+width+scale*29, scale*12),
                     fill='black'))

    # add C4M Logo
    image_data = open(c4m_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(woffs+scale*5.0, hoffs+height-scale*5.0)
    leads = svgwrite.image.Image(data, pos,
                                       size=(50,50))
    dwg.add(leads)

    if False:
        # add SRAMs
        for i in range(4):
            dwg.add(dwg.rect((woffs+scale+75*i, hoffs+scale),
                            (70,50),
                fill='white',
                stroke=svgwrite.rgb(16, 255, 16, '%'),
                stroke_width=scale/10.0))
        # add PLL
        dwg.add(dwg.rect((woffs+width-scale, hoffs+scale),
                            (25,20),
                fill='white',
                stroke=svgwrite.rgb(16, 255, 16, '%'),
                stroke_width=scale/10.0))

    # add attribution
    dwg.add(dwg.text("Libre-SOC ls180 QFP-128",
                       insert=(woffs+width/2-scale*5, scale*4),
                     fill='black'))
    dwg.add(dwg.text("In collaboration with LIP6.fr",
                       insert=(woffs+width/2-scale*5, scale*5),
                     fill='black'))
    dwg.add(dwg.text("Cell Libraries by Chips4Makers",
                       insert=(woffs+width/2-scale*5, scale*6),
                     fill='black'))
    dwg.add(dwg.text("IMEC TSMC 180nm",
                       insert=(woffs+width/2-scale*5, scale*7),
                     fill='black'))
    dwg.add(dwg.text("RED Semiconductor",
                       insert=(woffs+width/2-scale*5, scale*8),
                     fill='black'))

    # add package marking circles
    pos = (owoffs-outerscale*0, ohoffs+len(wepads)*outerscale+outerscale*2.5)
    dwg.add(dwg.circle(pos, scale*2,
                         fill='white',
                         stroke=svgwrite.rgb(16, 16, 16, '%'),
                         stroke_width=scale/5.0))
    dwg.add(dwg.circle(pos, scale*1,
                         fill='black',
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/5.0))
    pos = (owoffs+len(nepads)*outerscale+outerscale*2, ohoffs-outerscale*0.5)
    dwg.add(dwg.circle(pos, scale*2,
                         fill='white',
                         stroke=svgwrite.rgb(16, 16, 16, '%'),
                         stroke_width=scale/5.0))


    dwg.save()

def temp_create_sv(fname, pins):
    """unsophisticated drawer of an SVG
    """

    try:
        import svgwrite
    except ImportError:
        print ("WARNING, no SVG image, not producing image %s" % fname)
        return

    # create internal to external map
    bondmap = {'N': {}, 'S': {},  'E': {},  'W': {} }
    padside = {'pads.north': 'N', 'pads.east': 'E', 'pads.south': 'S',
               'pads.west': 'W'}
    sidepad = {}
    for pinpad, bank in padside.items():
        sidepad[bank] = pinpad
        for ipin in range(len(pins[pinpad])):
            eside, enum, epinnum = bond_int_to_ext(ipin, bank)
            bondmap[eside][enum] = (epinnum, ipin, bank)
    with open("/tmp/bondmap.txt", "w") as f:
        for k,v in bondmap.items():
            f.write("%s\n" % k)
            for enum, (epinnum, ipin, bank) in v.items():
                f.write("    %d %d  -> %s %d\n" % (enum, epinnum, bank, ipin))

    scale = 15
    outerscale = scale * 2.0

    width = len(pins['pads.north']) * scale
    height = len(pins['pads.east']) * scale
    woffs = scale*40#-width/2
    hoffs = scale*40#-height/2

    nepads = list(bondmap['N'].keys())
    nepads.sort()
    wepads = list(bondmap['W'].keys())
    wepads.sort()
    eepads = list(bondmap['E'].keys())
    eepads.sort()
    sepads = list(bondmap['S'].keys())
    sepads.sort()

    owoffs = woffs + (width/2) - len(nepads)/2 * outerscale
    ohoffs = hoffs + (height/2) - len(wepads)/2 * outerscale

    dwg = svgwrite.Drawing(fname, profile='full',
                           size=(width+scale*85, height+scale*80))

    # outer QFP rect
    # dwg.add(dwg.rect((owoffs-scale*2.5, ohoffs-scale*4.5),
    dwg.add(dwg.rect((owoffs-scale*2.5, ohoffs-scale*4.5),
                        (len(nepads)*outerscale+scale*9,
                         len(wepads)*outerscale+scale*13),
            fill='white',
            stroke=svgwrite.rgb(0, 128, 0, '%'),
            stroke_width=scale/5.0))

    # inner lead rect
    dwg.add(dwg.rect((woffs-scale*2, hoffs-scale*2),
                        (width+scale*6, height+scale*6),
            stroke=svgwrite.rgb(16, 255, 16, '%'),
            stroke_width=scale/10.0))

    # record the inner line (iopad) position so that the outer one can
    # match with it
    innerpos = {'N': {}, 'S': {},  'E': {},  'W': {} }

    # create the inner diagram
    for i, pin in enumerate(pins['pads.west']):
        ht = hoffs + height - (i * scale) + scale*0.5
        endline = (woffs-scale*4.5, ht-scale*0.5)
        innerpos['W'][i] = endline
        dwg.add(dwg.line((woffs-scale*2, ht-scale*0.5),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        dwg.add(dwg.text(pin.upper(), insert=(woffs-scale*12, ht),
                         fill='black'))
        dwg.add(dwg.text("W%d" % (i+1), insert=(woffs-scale*1.5, ht),
                            fill='white'))

    for i, pin in enumerate(pins['pads.east']):
        ht = hoffs + height - (i * scale) + scale*0.5
        wd = width + woffs + scale*2
        endline = (wd+scale*4.5, ht-scale*0.5)
        innerpos['E'][i] = endline
        dwg.add(dwg.line((wd+scale*2, ht-scale*0.5),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        dwg.add(dwg.text(pin.upper(), insert=(wd+scale*5, ht-scale*0.25),
                         fill='black'))
        dwg.add(dwg.text("E%d" % (i+1), insert=(wd, ht-scale*0.25),
                            fill='white'))

    for i, pin in enumerate(pins['pads.north']):
        wd = woffs + i * scale + scale*1.5
        endline = (wd, hoffs-scale*4.5)
        innerpos['N'][i] = endline
        dwg.add(dwg.line((wd, hoffs-scale*2),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        pos=(wd, hoffs-scale*5.0)
        txt = dwg.text(pin.upper(), insert=pos, fill='black')
        txt.rotate(-90, pos)
        dwg.add(txt)
        pos=(wd+scale*0.25, hoffs-scale*0.25)
        txt = dwg.text("N%d" % (i+1), insert=pos, fill='white')
        txt.rotate(-90, pos)
        dwg.add(txt)

    for i, pin in enumerate(pins['pads.south']):
        wd = woffs + i * scale + scale*1.5
        ht = hoffs + height + scale*2
        endline = (wd, ht+scale*4.5)
        innerpos['S'][i] = endline
        dwg.add(dwg.line((wd, ht+scale*2),
                         endline,
                         stroke=svgwrite.rgb(16, 255, 16, '%'),
                         stroke_width=scale/10.0))
        pos=(wd-scale*0.25, ht+scale*5.0)
        txt = dwg.text(pin.upper(), insert=pos, fill='black')
        txt.rotate(90, pos)
        dwg.add(txt)
        pos=(wd-scale*0.25, ht+scale*0.25)
        txt = dwg.text("S%d" % (i+1), insert=pos, fill='white')
        txt.rotate(90, pos)
        dwg.add(txt)

    # north outer pads
    for i in nepads:
        (epinnum, ipin, bank) = pad = bondmap['N'][i]
        wd = owoffs + i * outerscale + outerscale*1.5
        endline = (wd, ohoffs-outerscale*2)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos=(wd, ohoffs-outerscale*4.0)
        txt = dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                        insert=pos, fill='black')
        txt.rotate(-90, pos)
        dwg.add(txt)
        pos=(wd, ohoffs-outerscale*2.5)
        txt = dwg.text("%d N" % epinnum, insert=pos, fill='blue')
        txt.rotate(-90, pos)
        dwg.add(txt)

    # west outer pads
    for i in wepads:
        (epinnum, ipin, bank) = pad = bondmap['W'][i]
        ht = ohoffs + (i * outerscale) + outerscale*1.5
        endline = (owoffs+outerscale*0.5, ht)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos = (owoffs-outerscale*6.0, ht)
        dwg.add(dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                         pos,
                         fill='black'))
        pos = (owoffs-outerscale*1.0, ht)
        dwg.add(dwg.text("%d W" % epinnum, insert=pos,
                            fill='blue'))

    # south outer pads
    for i in sepads:
        (epinnum, ipin, bank) = pad = bondmap['S'][i]
        wd = owoffs + i * outerscale + outerscale*1.5
        ht = ohoffs + len(wepads)*outerscale + outerscale*4
        endline = (wd, ht)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos=(wd-outerscale*0.25, ht+outerscale*1.5)
        txt = dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                        insert=pos, fill='black')
        txt.rotate(90, pos)
        dwg.add(txt)
        pos=(wd-outerscale*0.25, ht+outerscale*0.5)
        txt = dwg.text("%d S" % epinnum, insert=pos, fill='blue')
        txt.rotate(90, pos)
        dwg.add(txt)

    # east outer pads
    for i in eepads:
        (epinnum, ipin, bank) = pad = bondmap['E'][i]
        ht = ohoffs + (i * outerscale) + outerscale*1.5
        wd = owoffs+len(nepads)*outerscale + outerscale*1
        endline = (wd+outerscale*0.5, ht)
        startline = innerpos[bank][ipin]
        dwg.add(dwg.line(startline,
                         endline,
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/10.0))
        pin = pins[sidepad[bank]][ipin]
        pos = (wd+outerscale*2.5, ht)
        dwg.add(dwg.text("%s (%s%d)" % (pin.upper(), bank, ipin+1),
                         pos,
                         fill='black'))
        pos = (wd+outerscale*1.0, ht)
        dwg.add(dwg.text("%d E" % epinnum, insert=pos,
                            fill='blue'))

    # add ls180 image
    image_data = open(ls180_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(width/2+woffs-225, height/2+hoffs-225)
    leads = svgwrite.image.Image(data, pos,
                                       size=(480,480))
    dwg.add(leads)

    # add QFP pack image in top-right
    image_data = open(pack_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(0, 0)
    leads = svgwrite.image.Image(data, pos,
                                       size=(327,300))
    dwg.add(leads)
    dwg.add(dwg.text("GREATEK QFP128L",
                       insert=(50,150),
                        font_size=20,
                     fill='black'))
    dwg.add(dwg.text("D/W J1-03128-001",
                       insert=(50,180),
                        font_size=20,
                     fill='black'))


    # add QFP lead image in centre
    sz=320
    image_data = open(lead_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(woffs+width+scale*23.5, 0)
    leads = svgwrite.image.Image(data, pos,
                                       size=(sz,sz))
    leads.rotate(-90, (pos[0]+sz/2, pos[1]+sz/2))
    dwg.add(leads)

    dwg.add(dwg.text("GREATEK ELECTRONICS INC.",
                       insert=(woffs+width+scale*29, scale*8),
                     fill='black'))
    dwg.add(dwg.text("INNER LEAD DRAWING",
                       insert=(woffs+width+scale*29, scale*9),
                     fill='black'))
    dwg.add(dwg.text("QFP 128L OPEN STAMPING",
                       insert=(woffs+width+scale*29, scale*10),
                     fill='black'))
    dwg.add(dwg.text("BODY 14x20x2.75mm",
                       insert=(woffs+width+scale*29, scale*11),
                     fill='black'))
    dwg.add(dwg.text("L/F PAD SIZE 236x236mil^2",
                       insert=(woffs+width+scale*29, scale*12),
                     fill='black'))

    # add C4M Logo
    image_data = open(c4m_drawing, "rb").read()
    encoded = base64.b64encode(image_data).decode()
    data = 'data:image/png;base64,{}'.format(encoded)
    pos=(woffs+scale*5.0, hoffs+height-scale*5.0)
    leads = svgwrite.image.Image(data, pos,
                                       size=(50,50))
    dwg.add(leads)

    if False:
        # add SRAMs
        for i in range(4):
            dwg.add(dwg.rect((woffs+scale+75*i, hoffs+scale),
                            (70,50),
                fill='white',
                stroke=svgwrite.rgb(16, 255, 16, '%'),
                stroke_width=scale/10.0))
        # add PLL
        dwg.add(dwg.rect((woffs+width-scale, hoffs+scale),
                            (25,20),
                fill='white',
                stroke=svgwrite.rgb(16, 255, 16, '%'),
                stroke_width=scale/10.0))

    # add attribution
    dwg.add(dwg.text("Libre-SOC ls180 QFP-128",
                       insert=(woffs+width/2-scale*5, scale*4),
                     fill='black'))
    dwg.add(dwg.text("In collaboration with LIP6.fr",
                       insert=(woffs+width/2-scale*5, scale*5),
                     fill='black'))
    dwg.add(dwg.text("Cell Libraries by Chips4Makers",
                       insert=(woffs+width/2-scale*5, scale*6),
                     fill='black'))
    dwg.add(dwg.text("IMEC TSMC 180nm",
                       insert=(woffs+width/2-scale*5, scale*7),
                     fill='black'))
    dwg.add(dwg.text("RED Semiconductor",
                       insert=(woffs+width/2-scale*5, scale*8),
                     fill='black'))

    # add package marking circles
    pos = (owoffs-outerscale*0, ohoffs+len(wepads)*outerscale+outerscale*2.5)
    dwg.add(dwg.circle(pos, scale*2,
                         fill='white',
                         stroke=svgwrite.rgb(16, 16, 16, '%'),
                         stroke_width=scale/5.0))
    dwg.add(dwg.circle(pos, scale*1,
                         fill='black',
                         stroke=svgwrite.rgb(255, 16, 16, '%'),
                         stroke_width=scale/5.0))
    pos = (owoffs+len(nepads)*outerscale+outerscale*2, ohoffs-outerscale*0.5)
    dwg.add(dwg.circle(pos, scale*2,
                         fill='white',
                         stroke=svgwrite.rgb(16, 16, 16, '%'),
                         stroke_width=scale/5.0))


    dwg.save()


def display(of, pins, banksel=None, muxwidth=4):
    of.write("""\
| Pin | Mux0        | Mux1        | Mux2        | Mux3        |
| --- | ----------- | ----------- | ----------- | ----------- |
""")
    pinidx = sorted(pins.keys())
    for pin in pinidx:
        pdata = pins.get(pin)
        if banksel:
            skip = False
            for mux in range(muxwidth):
                if mux not in pdata:
                    continue
                name, bank = pdata[mux]
                if banksel != bank:
                    skip = True
            if skip:
                continue
        res = '| %3d |' % pin
        for mux in range(muxwidth):
            if mux not in pdata:
                res += "             |"
                continue
            name, bank = pdata[mux]
            res += " %s %-9s |" % (bank, name)
        of.write("%s\n" % res)


def fnsplit(f):
    a = ''
    n = 0
    if not f.startswith('FB_'):
        f2 = f.split('_')
        if len(f2) == 2:
            if f2[1].isdigit():
                return f2[0], int(f2[1])
            return f2[0], f2[1]
    #print f
    while f and not f[0].isdigit():
        a += f[0]
        f = f[1:]
    return a, int(f) if f else None


def fnsort(f1, f2):
    a1, n1 = fnsplit(f1)
    a2, n2 = fnsplit(f2)
    x = cmp(a1, a2)
    if x != 0:
        return x
    return cmp(n1, n2)


def find_fn(fname, names):
    for n in names:
        if fname.startswith(n):
            return n

def map_name(pinmap, fn, fblower, pin, rename):
    if not rename:
        if pin[:-1].isdigit():
            print ("map name digit", pin, fn, fblower)
            if fn in ['PWM', 'EINT', 'VDD', 'VSS']:
                return fn.lower() + pin.lower()
        if fn == 'GPIO':
            return 'gpio' + pin[1:].lower()
        return pin.lower()
    pin = pin.lower()
    if fn == 'GPIO':
        pk = '%s%s_%s' % (fblower, pin[0], pin[:-1])
    elif pin[:-1].isdigit() and fn != 'EINT':
        pk = '%s%s_out' % (fblower, pin[:-1])
    else:
        pk = '%s_%s' % (fblower, pin[:-1])
    print ("map name", pk, fblower, pk in pinmap)
    if not pk in pinmap:
        return pin.lower()
    remapped = pinmap[pk]
    uscore = remapped.find('_')
    if uscore == -1:
        return pin.lower()
    fn, pin = remapped[:uscore], remapped[uscore+1:] + pin[-1]
    return pin.lower()

def python_pindict(of, pinmap, pins, function_names, dname, remap):

    res = OrderedDict()
    of.write("\n%s = OrderedDict()\n" % dname)

    for k, pingroup in pins.byspec.items():
        (a, n) = k.split(":")
        if n.isdigit():
            a = "%s%s" % (a, n)
        fblower = a.lower()
        of.write("%s['%s'] = [ " % (dname, fblower))
        res[fblower] = []
        count = 0
        for i, p in enumerate(pingroup):
            name = map_name(pinmap, k[0], fblower, p, remap)
            res[fblower].append(name)
            of.write("'%s', " % name)
            count += 1
            if count == 4 and i != len(pingroup)-1:
                of.write("\n                ")
                count = 0
        of.write("]\n")
        print ("    dict %s" % dname, a, n, pingroup)
    of.write("\n\n")
    return res

def python_dict_fns(of, pinmap, pins, function_names):
    of.write("# auto-generated by Libre-SOC pinmux program: do not edit\n")
    of.write("# python src/pinmux_generator.py -v -s {spec} -o {output}\n")
    of.write("# use OrderedDict to fix stable order for JTAG Boundary Scan\n")
    of.write("from collections import OrderedDict\n")

    fn_names = function_names.keys()
    fns = {}

    fnidx = list(fns.keys())
    fnidx.sort(key=fnsplit)

    print ("python fnames", function_names)
    print ("python speckeys", pins.byspec.keys())
    print ("python dict fns", dir(pins.gpio))
    print (pins.gpio.pinfn('', ''))
    print (pins.pwm.pinfn('', ''))
    print (pins.sdmmc.pinfn('', ''))
    print ("by spec", pins.byspec)
    print (pinmap)

    pd = python_pindict(of, {}, pins, function_names, 'pindict', False)
    ld = python_pindict(of, pinmap, pins, function_names, 'litexdict', True)

    print ("pd", pd)
    print ("ld", ld)
    # process results and create name map
    litexmap = OrderedDict()
    for k in pd.keys():
        pl = pd[k]
        ll = ld[k]
        for pname, lname in zip(pl, ll):
            pname = "%s_%s" % (k, pname[:-1]) # strip direction +/-/*
            lname = lname[:-1] # strip direction +/-/*
            if k in ['eint', 'pwm', 'gpio', 'vdd', 'vss']: # sigh
                lname = "%s_%s" % (k, lname)
            litexmap[pname] = lname
    print ("litexmap", litexmap)
    of.write("litexmap = {\n")
    for k, v in litexmap.items():
        of.write("\t'%s': '%s',\n" % (k, v))
    of.write("}\n")
    return litexmap


def display_fns(of, bankspec, pins, function_names):
    fn_names = function_names.keys()
    fns = {}
    for (pin, pdata) in pins.items():
        for mux in range(0, 4):  # skip GPIO for now
            if mux not in pdata:
                continue
            name, bank = pdata[mux]
            assert name is not None, str(bank)
            if name not in fns:
                fns[name] = []
            fns[name].append((pin - bankspec[bank], mux, bank))

    fnidx = list(fns.keys())
    fnidx.sort(key=fnsplit)
    current_fn = None
    for fname in fnidx:
        fnbase = find_fn(fname, fn_names)
        #fblower = fnbase.lower()
        assert fnbase in function_names, "fn %s not in descriptions %s" % \
            (fname, str(function_names.keys()))
        #print "name", fname, fnbase
        if fnbase != current_fn:
            if current_fn is not None:
                of.write('\n')
            of.write("## %s\n\n%s\n\n" % (fnbase, function_names[fnbase]))
            current_fn = fnbase
        of.write("* %-9s :" % fname)
        for (pin, mux, bank) in fns[fname]:
            of.write(" %s%d/%d" % (bank, pin, mux))
        of.write('\n')

    return fns


def check_functions(of, title, bankspec, fns, pins, required, eint, pwm,
                    descriptions=None):
    fns = deepcopy(fns)
    pins = deepcopy(pins)
    if descriptions is None:
        descriptions = {}
    fnidx = fns.keys()

    #print dir(fns)
    #print dir(pins)

    of.write("# Pinmap for %s\n\n" % title)

    print ("fn_idx", fnidx)
    print ("fns", fns)
    print ("fnspec", pins.fnspec.keys())
    print ("required", required)
    for name in required:
        of.write("## %s\n\n" % name)
        if descriptions and name in descriptions:
            of.write("%s\n\n" % descriptions[name])

        name = name.split(':')
        if len(name) == 2:
            findbank = name[0][0]
            findmux = int(name[0][1:])
            name = name[1]
        else:
            name = name[0]
            findbank = None
            findmux = None
        name = name.split('/')
        if len(name) == 2:
            count = int(name[1])
        else:
            count = 100000
        name = name[0]
        #print name
        found = set()
        pinfound = {}
        located = set()
        for fname in fnidx:
            if not fname.startswith(name):
                continue
            for k in pins.fnspec.keys():
                if fname.startswith(k):
                    fk = list(pins.fnspec[k].keys())
                    fn = pins.fnspec[k]
                    fn = fn[fk[0]]
                    #print fname, fn, dir(fn)
                    if count == 100000:
                        count = len(fn.pingroup)
            for pin, mux, bank in fns[fname]:
                if findbank is not None:
                    if findbank != bank:
                        continue
                    if findmux != mux:
                        continue
                pin_ = pin + bankspec[bank]
                if pin_ in pins:
                    pinfound[pin_] = (fname, pin_, bank, pin, mux)

        pinidx = sorted(pinfound.keys())

        fname = None
        removedcount = 0
        print ("pinidx", pinidx)
        for pin_ in pinidx:
            fname, pin_, bank, pin, mux = pinfound[pin_]
            if fname in found:
                continue
            found.add(fname)
            if len(found) > count:
                continue
            del pins[pin_]
            removedcount += 1
            of.write("* %s %d %s%d/%d\n" % (fname, pin_, bank, pin, mux))

        print (fns)
        if removedcount != count:
            if fname is None:
                print ("no match between required and available pins")
            else:
                print ("not all found", name, removedcount, count, title, found,
                   fns[fname])
            print ("pins found", pinfound)

        # fnidx.sort(fnsort)
        of.write('\n')

    # gpios
    gpios = []
    for name in descriptions.keys():
        if not name.startswith('GPIO'):
            continue
        if name == 'GPIO':
            continue
        gpios.append(name)
    gpios.sort()

    if gpios:
        of.write("## GPIO\n\n")

        for fname in gpios:
            if fname in found:
                continue
            desc = ''
            if descriptions and fname in descriptions:
                desc = ': %s' % descriptions[fname]
            bank = fname[4]
            pin = int(fname[7:])
            pin_ = pin + bankspec[bank]
            if pin_ not in pins:
                continue
            del pins[pin_]
            found.add(fname)
            of.write("* %-8s %d %s%-2d %s\n" % (fname, pin_, bank, pin, desc))
        of.write('\n')

    if eint:
        display_group(of, bankspec, "EINT", eint, fns, pins, descriptions)
    if pwm:
        display_group(of, bankspec, "PWM", pwm, fns, pins, descriptions)

    of.write("## Unused Pinouts (spare as GPIO) for '%s'\n\n" % title)
    if descriptions and 'GPIO' in descriptions:
        of.write("%s\n\n" % descriptions['GPIO'])
    display(of, pins)
    of.write('\n')

    return pins  # unused


def display_group(of, bankspec, title, todisplay, fns, pins, descriptions):
    of.write("## %s\n\n" % title)

    found = set()
    for fname in todisplay:
        desc = ''
        if descriptions and fname in descriptions:
            desc = ': %s' % descriptions[fname]
        fname = fname.split(':')
        if len(fname) == 2:
            findbank = fname[0][0]
            findmux = int(fname[0][1:])
            fname = fname[1]
        else:
            fname = fname[0]
            findbank = None
            findmux = None
        for (pin, mux, bank) in fns[fname]:
            if findbank is not None:
                if findbank != bank:
                    continue
                if findmux != mux:
                    continue
            if fname in found:
                continue
            pin_ = pin + bankspec[bank]
            if pin_ not in pins:
                continue
            del pins[pin_]
            found.add(fname)
            of.write("* %s %d %s%d/%d %s\n" %
                     (fname, pin_, bank, pin, mux, desc))
    of.write('\n')


def display_fixed(of, fixed, offs):

    fkeys = sorted(fixed.keys())
    pin_ = offs
    res = []
    for pin, k in enumerate(fkeys):
        of.write("## %s\n\n" % k)
        prevname = ''
        linecount = 0
        for name in fixed[k]:
            if linecount == 4:
                linecount = 0
                of.write('\n')
            if prevname[:2] == name[:2] and linecount != 0:
                of.write(" %s" % name)
                linecount += 1
            else:
                if linecount != 0:
                    of.write('\n')
                of.write("* %d: %d %s" % (pin_, pin, name))
                linecount = 1
                res.append((pin_, name))

            prevname = name
            pin_ += 1
        if linecount != 0:
            of.write('\n')
        of.write('\n')

    return res
