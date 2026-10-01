"""Install the pixel-exact free-X layouts and a bounded OAM coordinate fixup."""
from build_terry_16 import *
from terry_moves_14 import Asm
from terry_variant import far

def main():
    b=bytearray(ROM.read_bytes());plans=json.loads((OUT/'free_layouts_16.json').read_text())
    assert sha(b)==plans['input_rom_sha256']
    tiles=Allocator(b,160,164);meta=Allocator(b,220,223);changes=[]
    assert set(b[160*0x4000:165*0x4000])=={255} and set(b[220*0x4000:224*0x4000])=={255}
    for p in plans['plans']:
        k=tuple(p['key']);old=lookup(b,k)
        pieces=sorted([(x,y,bytes.fromhex(r)) for x,y,r in p['pieces']],key=lambda v:(v[0],v[1]))
        if 'object_order' in p:
            order=p['object_order'];assert sorted(order)==list(range(len(pieces)))
            pieces=[pieces[j] for j in order]
        minx=min(x for x,y,r in pieces);miny=min(y for x,y,r in pieces)
        raw=b''.join(r for x,y,r in pieces);bank,ptr=tiles.put(raw,16);cmd=bytearray([((bank-37)<<1)|1]);n=len(raw)//16
        while n:
            size=min(n,8);cmd+=bytes([(ptr&0xf0)|((size-1)<<1),ptr>>8]);ptr+=size*16;n-=size
        origin=min(miny,-old['anchor_y']);height=-origin-old['anchor_y']
        assert max(y for x,y,r in pieces)-origin<64
        data=bytearray([len(cmd)])+cmd+bytes([-minx,old['anchor_y'],height])
        data+=bytes([(y-origin)<<2 for x,y,r in pieces])+b'\x03\xfd\x16'+bytes([x-minx for x,y,r in pieces])
        bank,ptr=meta.put(data);new=decode(b,bank,ptr);assert pixelmap(old)==pixelmap(new)
        at=fileoff(k[0],k[1])+k[2]*3;b[at:at+3]=bytes([bank])+ptr.to_bytes(2,'little')
        changes.append({'table':k,'pixels_and_anchors_identical':True,'objects':len(pieces),'bank':bank,'pointer':ptr})
    def put(bank,addr,data):
        off=fileoff(bank,addr) if bank else addr
        assert b[off:off+len(data)]==b'\xff'*len(data),(bank,hex(addr),len(data))
        b[off:off+len(data)]=data
    # A byte beside the established variant flags records this draw's start.
    # Original-ROM direct address references to CBFA were checked absent.
    put(130,0x5f00,bytes.fromhex('f5 f0a0 eafacb f1 2e3a 5e f0ae c9'))
    assert b[0x1424:0x1429]==bytes.fromhex('2e3a5ef0ae')
    b[0x1424:0x1429]=far(0x5f00)
    put(0,0x25a8,bytes.fromhex('7de0a0')+far(0x5e00)+b'\xc9')
    # Banked code cannot switch its own instruction bank. This fixed-bank
    # byte reader temporarily selects A, reads (HL), then restores bank130.
    put(0,0x25b1,bytes.fromhex('ea5021 7e f5 3e82 ea5021 f1 c9'))
    for ret in (0x14a7,0x1509,0x156d,0x15cf):
        assert b[ret-3:ret+1]==bytes.fromhex('7de0a0c9')
        b[ret-3:ret+1]=bytes.fromhex('cda825c9')
    c=Asm(0x5e00).emit('f5 c5 d5 e5 f0ec 67 cd0041 47 2e15 6e 2600 7d 29 85 6f').jr(0x30,'table_no_carry')
    c.emit('24').label('table_no_carry').emit('19 78 cdb125 4f 23 78 cdb125 5f 23 78 cdb125 67 6b 79 fedc').jp(0xda,'done')
    c.emit('fee0').jp(0xd2,'done')
    c.emit('79 cdb125 23 85 6f').jr(0x30,'no_carry').emit('24')
    c.label('no_carry').emit('23 23 23')
    c.label('scan').emit('79 cdb125 23 fe03').jr(0x20,'scan')
    c.emit('79 cdb125 23 fefd').jp(0xc2,'done').emit('79 cdb125 23 fe16').jp(0xc2,'done')
    c.emit('fafacb 5f f0a0 93 cb3f cb3f 47 b7').jr(0x28,'done')
    c.emit('16c0 13 f0ae e601').jr(0x20,'mirror')
    c.label('normal').emit('79 cdb125 23 e5 6f 1a 85 12 e1 13 13 13 13 05').jr(0x20,'normal').jr(0x18,'done')
    c.label('mirror').emit('79 cdb125 23 e5 6f 1a 95 12 e1 13 13 13 13 05').jr(0x20,'mirror')
    c.label('done').emit('e1 d1 c1 f1 c9');put(130,0x5e00,c.finish())
    checksums(b);ROM.write_bytes(b)
    report=json.loads((OUT/'build_16.json').read_text());report.update(rom_sha256=sha(b),free_layouts=changes,
        free_layout_input_sha256=plans['input_rom_sha256'],renderer_hooks=['1424','14A4','1506','156A','15CC','25A8','25B1','130:5E00','130:5F00'],scratch='CBFA: current draw start; rewritten per draw',
        scope='Lossless tile placement and an OAM horizontal-coordinate extension. No art scaling, palette changes, attack logic or timings changed.')
    (OUT/'build_16.json').write_text(json.dumps(report,indent=2)+'\n');print('ROM',sha(b),'free layouts',len(changes))

if __name__=='__main__':main()
