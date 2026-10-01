"""Fuller Terry drawings, using the owned NGPC captures as exact pixel sources.

Proto 14 remains the crowded-scene fallback. No generative artwork, smoothing,
palette changes or vertical scaling is used. Named long-limb poses shorten
their reach by joining native pixel sections rather than shrinking the fist.
"""
from pathlib import Path
import json
from PIL import Image
from terry_native_art import ART, catalog, mapping, record, indexed, compress_extension

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'terry_prototype/art_15'


def full_mapping():
    m = mapping()
    idle = catalog()['cases']['idle']['unique']
    # Alpha plays 3,4,3,1,2,1. Retain that timing and restore the native
    # opening/closing-hand phases instead of alternating two narrow poses.
    for target, index in {1:1, 2:2, 3:0, 4:4, 6:0, 7:0, 118:0}.items():
        m[target] = idle[index]
    return m


def corrected_record(pid):
    rec = record(pid)
    findings = json.loads((ROOT/'terry_prototype/art_review_14/animation_audit.json').read_text())['alignment_findings']
    match = next((a for a in findings if a['source'] == pid.split(':')[0] and a['fresh_agrees']), None)
    if match:
        ox, oy = match['corrected']
        im = rec['_image']
        if rec['transform'] == 'flip': ox = -ox-im.width
        elif rec['transform']:
            ox, oy = -ox-im.width, -oy-im.height-40
        rec['native_offset'] = (ox,oy)
        rec['anchor_correction'] = match
    return rec


def join_rows(im, width, bands):
    """Join exact source column spans in selected bands; never resample pixels.

    Each band supplies (y0,y1,source x spans). Unmentioned rows retain their
    original coordinates. Only empty pixels may fall outside the output.
    """
    out = Image.new('P',(width,im.height));out.putpalette(im.getpalette())
    for y in range(im.height):
        spans = next((spans for a,b,spans in bands if a<=y<b),[(0,im.width)])
        x = 0
        for a,b in spans:
            for sx in range(a,b):
                v=im.getpixel((sx,y))
                if x<width:out.putpixel((x,y),v)
                else:assert not v, ('unintended crop',im.size,y,sx)
                x+=1
    return out


def fuller_image(rec, width=40):
    im = rec['_image'].copy();ox,oy = rec['native_offset']
    case = rec.get('first_case','')
    method = 'native pixels and proportions'
    if im.width>width:
        if im.size==(52,40) and case=='standing_p_2' and width in (40,44):
            cut=52-width
            im=join_rows(im,width,[(14,25,[(0,28),(28+cut,52)])])
            method=f'native head, torso, legs and fist; forearm shortened by {cut} pixels'
        elif im.size==(51,35) and case=='crouching_p_2' and width in (40,44):
            cut=51-width
            im=join_rows(im,width,[(13,24,[(0,28),(28+cut,51)])])
            method=f'native head, crouched body and fist; forearm shortened by {cut} pixels'
        else:
            im,ox,method=compress_extension(im,ox,width,case)
    rec['adaptation']=method
    rec['fuller_image']=im.copy()
    # The common encoder calls body_image once more. Supplying an already
    # prepared indexed source and its updated origin leaves these pixels exact.
    rec['_image']=im;rec['native_offset']=(ox,oy);rec['maxwidth']=im.width
    rec['optimize_x_grid']=im.width<=40
    return rec
