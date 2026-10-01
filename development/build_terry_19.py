"""Keep down-forward kick as a crouching normal; scope to Backspin only."""
import json
from build_terry_18 import ROOT,OUT
from inspect_engine import sha
from sfa_sprite_codec import fileoff
from terry_moves_14 import Asm
from expansion_probe import checksums

BASE=OUT/'SFA_Terry_Prototype_18.gbc'
ROM=OUT/'SFA_Terry_Prototype_19.gbc'
BASE_SHA='598c6cec7b708ef7fc88708ae39d6d836f20cf3c7d94c2e4cd5bb3b046cd0143'
DEST=OUT/'evidence_19'

def main():
    old=BASE.read_bytes();assert sha(old)==BASE_SHA;b=bytearray(old)
    # This call is reached only for Terry's simple Backspin command, after
    # Burn Knuckle, DP+K and HCF+K checks. FFDB is the accepted relative input;
    # bit 7 is down in either facing. Direction/punch throw logic is untouched.
    # Retain HL (the existing forward+K pattern) and original AF at scanner
    # entry. A rejected crouching command returns carry clear, just like the
    # original direction scanner's failed match.
    c=Asm(0x6580).emit('f5 f0db cb7f').jr(0x20,'crouch')
    c.emit('f1 c3005b')
    c.label('crouch').emit('f1 b7 c9')
    code=c.finish();off=fileoff(130,0x6580)
    assert b[off:off+len(code)]==b'\xff'*len(code)
    b[off:off+len(code)]=code
    call=fileoff(130,0x544f)
    assert b[call:call+9]==bytes.fromhex('21c75bcd005bd2c454')
    b[call+4:call+6]=bytes.fromhex('8065')
    checksums(b)
    if ROM.exists():assert ROM.read_bytes()==b,'Existing Proto19 differs; preserve it.'
    ROM.write_bytes(b);DEST.mkdir(exist_ok=True)
    changed=[i for i,(x,y) in enumerate(zip(old,b)) if x!=y]
    report={'rom_sha256':sha(b),'base_sha256':BASE_SHA,'base_preserved':sha(BASE.read_bytes())==BASE_SHA,
            'changed_bytes':len(changed),'changed_offsets':[hex(i) for i in changed],
            'gate_bank':130,'gate_address':'0x6580','gate_bytes':code.hex(),
            'scope':'Exclude down-held accepted inputs from Terry Backspin only; preserve prior motion priority and all graphics/timing/damage.'}
    (OUT/'build_19.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
