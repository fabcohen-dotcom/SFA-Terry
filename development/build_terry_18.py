"""Allow a quick close-range horizontal+punch throw for Terry only."""
import json
from build_terry_17 import ROOT,OUT
from inspect_engine import sha
from terry_moves_14 import Asm
from terry_variant import far
from sfa_sprite_codec import fileoff
from expansion_probe import checksums

BASE=OUT/'SFA_Terry_Prototype_17.gbc';ROM=OUT/'SFA_Terry_Prototype_18.gbc'
BASE_SHA='fe1cf21cd3f919e67d66385082822db99d379733530f405616056c3eb94ed550'

def main():
    old=BASE.read_bytes();assert sha(old)==BASE_SHA;b=bytearray(old)
    # This entry is reached only after command motions have had priority,
    # and only for a standing normal punch. Reuse Alpha's original throw
    # eligibility and range routine; do not upgrade the strength of a miss.
    c=Asm(0x6500).emit('f0ec 67 cd0040').jr(0x28,'normal')
    c.emit('f0db e6f0 fe10').jr(0x28,'attempt')
    c.emit('fe20').jr(0x20,'normal')
    c.label('attempt').emit('1ef8 1608 cdca27').jr(0x28,'normal')
    c.emit('cde71f 01020000 3e01 b7 c9')
    c.label('normal').emit('f0ec 67 2e2d 34 af c9')
    code=c.finish();off=fileoff(130,0x6500);assert b[off:off+len(code)]==b'\xff'*len(code)
    b[off:off+len(code)]=code
    off=fileoff(12,0x40c6);assert b[off:off+6]==bytes.fromhex('f0ec672e2d34')
    b[off:off+6]=far(0x6500)+b'\xc0'
    # Read the direction saved with the accepted punch, rather than a live
    # direction that may already have been released on a short tap.
    start=fileoff(130,0x6400);needle=bytes.fromhex('f0d5e6203e01')
    at=b.index(needle,start,start+0x100);b[at:at+2]=bytes.fromhex('f0db')
    checksums(b);ROM.write_bytes(b)
    report={'rom_sha256':sha(b),'base_sha256':BASE_SHA,'base_preserved':sha(BASE.read_bytes())==BASE_SHA,
        'input_hook':{'bank':130,'address':'0x6500','length':len(code)},'direction_patch':hex(at),
        'scope':'Terry close-range horizontal+punch accepts light/short press; original throw eligibility, range, animation, damage, cast and motion priority preserved.'}
    (OUT/'build_18.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
