"""Terry-only native MOTM throw art and choreography, based on preserved Proto16."""
import json
from PIL import Image
from inspect_engine import ROOT,sha
from expansion_probe import checksums
from build_terry import Allocator,encode,prepare
from terry_moves_14 import Asm,native_anchor
from terry_variant import far
from terry_native_art import indexed
from sfa_sprite_codec import fileoff,decode
from build_terry_16 import pixelmap

OUT=ROOT/'terry_prototype'; BASE=OUT/'SFA_Terry_Prototype_16.gbc';ROM=OUT/'SFA_Terry_Prototype_17.gbc'
BASE_SHA='339f153543157f5b681a7caff407aa2544bf6253112f7cac97ee72058a31ec9b'
ART=OUT/'throw_review_16/ngpc'

def main():
    old=BASE.read_bytes();assert sha(old)==BASE_SHA;b=bytearray(old);regions=[];patches=[]
    def put(bank,addr,data):
        off=fileoff(bank,addr);assert b[off:off+len(data)]==b'\xff'*len(data),(bank,hex(addr),len(data))
        b[off:off+len(data)]=data;b[(bank+1)*0x4000-1]=bank
        regions.append({'bank':bank,'address':hex(addr),'length':len(data)})
    def patch(off,expected,data):
        assert len(expected)==len(data) and b[off:off+len(expected)]==expected,hex(off)
        b[off:off+len(data)]=data;patches.append({'offset':hex(off),'old':expected.hex(),'new':data.hex()})

    assert set(b[145*16384:146*16384])=={255} and set(b[224*16384:225*16384])=={255}
    tiles=Allocator(b,145,145);meta=Allocator(b,224,224);catalog=json.loads((ART/'catalog.json').read_text());stats=[]
    for slot,pid in enumerate(catalog['cases']['right_p_20']['unique'][1:6],108):
        im=indexed(Image.open(ART/'poses'/catalog['poses'][pid]['file']));ox,oy=native_anchor(catalog,'right_p_20',pid)
        choices=[]
        for pad in range(8):
            padded=Image.new('P',(im.width+pad,im.height));padded.putpalette(im.getpalette());padded.paste(im,(0,0))
            rec={'id':pid,'_image':padded,'native_offset':(ox,oy),'maxwidth':padded.width,'size':list(im.size)}
            _,x,y,pieces=prepare(rec,None)
            count=[sum(yy<=s<yy+16 for xx,yy,raw in pieces) for s in range(-16,im.height+16)]
            choices.append(((max(count),len(pieces),sum(v*v for v in count),pad),rec))
        rank,rec=min(choices,key=lambda t:t[0]);bank,ptr,stat=encode(b,rec,None,tiles,meta)
        assert stat['objects']<=16 and stat['max_per_line']<=5
        wanted={(-(ox+x)-1,oy+y-12):im.getpixel((x,y)) for x in range(im.width) for y in range(im.height) if im.getpixel((x,y))}
        assert pixelmap(decode(b,bank,ptr))==wanted
        for tb,addr in [(130,0x5000),(134,0x4000)]:
            off=fileoff(tb,addr)+slot*3;patch(off,bytes(b[off:off+3]),bytes([bank])+ptr.to_bytes(2,'little'))
        stat.update(slot=slot,native_offset=[ox,oy],all_source_pixels_preserved=True);stats.append(stat)

    # Pose timings are the measured MOTM video-frame timings: grab 12,
    # preparation 4, lift 4, raised-arm release 12, turn 6, recovery 6.
    # All frames retain Alpha's original no-attack throw collision records.
    program=bytearray()
    for duration,flag,pose,collision in [(12,0,108,0x74e0),(4,0,109,0x7760),(4,0,110,0x7770),
                                         (12,1,111,0x7780),(6,1,110,0x7790),(6,1,112,0x77a0)]:
        program+=bytes([duration,flag,pose])+collision.to_bytes(2,'little')
    program+=bytes([0xff,1,0x80,112,0xe0,0x74])
    put(135,0x4000,program)

    c=Asm(0x6400).emit('f0ec 67 cd0040').jp(0xca,'original')
    c.emit('2e2d 7e b7').jp(0xca,'init')
    c.emit('fe01').jp(0xca,'hold')
    c.emit('2e05 cb7e').jr(0x20,'finish')
    c.emit('cdaf1a').jp(0xc3,'done')
    c.label('finish').emit('2e14 3612 2e63 7e b7').jr(0x20,'cpu_finish')
    c.emit('cdb621').jp(0xc3,'done')
    c.label('cpu_finish').emit('cddd2e').jp(0xc3,'done')
    c.label('hold').emit('cdaf1a 2e04 7e b7').jp(0xca,'done')
    c.emit('2e2d 3602 110066 cd8127').jp(0xc3,'done')
    c.label('init').emit('2e2d 3601 0e02 cd6c28 1e14 cdcc07')
    c.emit('2e63 7e b7').jr(0x20,'cpu_dir')
    c.emit('f0d5 e620 3e01').jr(0x28,'direction')
    c.emit('af').jr(0x18,'direction')
    c.label('cpu_dir').emit('cd3b24 ee01')
    c.label('direction').emit('2e26 77 2e14 3687 110040 cde819')
    c.label('done').emit('3e01 b7 c9')
    c.label('original').emit('f0ec 67 11e648 af c9')
    put(130,0x6400,c.finish())
    patch(fileoff(12,0x48d5),bytes.fromhex('f0ec6711e648'),far(0x6400)+b'\xc0')
    # Original damage class and launch type. Facing is now Terry's toss
    # direction, so release no longer inverts the thrower's facing.
    put(130,0x6600,bytes.fromhex('0005130004000000'))

    # The receiving fighter's original four-byte pose record is fetched
    # first. Adjust only a victim currently held by our Terry handler.
    c=Asm(0x6680).emit('cd9d1b e5 c5 d5 f0ec 67 2e3c 66 cd0040').jp(0xca,'victim_done')
    c.emit('2e14 7e fe87').jp(0xc2,'victim_done')
    c.emit('2e2a 2a fe01').jp(0xc2,'victim_done')
    c.emit('2a fe02').jp(0xc2,'victim_done')
    c.emit('2e06 7e d66c fe05').jp(0xd2,'victim_done')
    c.emit('87 87 5f 1600 214067 19 119cff 0604')
    c.label('copy').emit('2a 12 13 05').jr(0x20,'copy')
    c.label('victim_done').emit('d1 c1 e1 f09c 4f c9')
    put(130,0x6680,c.finish())
    patch(fileoff(8,0x4ea4),bytes.fromhex('cd9d1bf09c4f'),far(0x6680)+b'\x00')
    # dx (opposite facing), height, victim flip/layer, native Alpha reaction
    # index. These coordinate existing cast reactions with Terry's hands.
    put(130,0x6740,bytes([240,0,0x81,0, 244,4,0x81,4, 240,18,0x81,4,
                         236,26,0x81,4, 225,6,0x81,8]))
    checksums(b);ROM.write_bytes(b)
    report={'rom_sha256':sha(b),'base_sha256':BASE_SHA,'base_preserved':sha(BASE.read_bytes())==BASE_SHA,
        'native_rom_sha256':catalog['rom_sha256'],'frames':stats,'regions':regions,'patches':patches,
        'scope':'Terry throw animation and opponent choreography; original cast, throw damage data and all other moves preserved.'}
    (OUT/'build_17.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
