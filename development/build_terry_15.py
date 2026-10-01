"""Build Proto 15 from the preserved, tested Proto 14 ROM.

Two graphics sets: fuller art during ordinary fights and the known Proto 14
set while projectiles are active. The cache key changes with the set, so a
held pose cannot accidentally draw newly selected layouts with stale tiles.
Moves, collision records, damage, UI and source ROMs stay unchanged.
"""
from pathlib import Path
import json
from PIL import Image
from build_terry import Allocator, encode,pack_body
from sfa_sprite_codec import decode, descriptor, fileoff
from inspect_engine import ROOT, SOURCE, sha
from expansion_probe import checksums
from terry_variant import far
from terry_moves_14 import Asm, active, ART as MOVE_ART, native_anchor
from terry_native_art import indexed
from terry_art_15 import full_mapping, corrected_record, fuller_image, OUT as ART_OUT

OUT=ROOT/'terry_prototype'
BASE=OUT/'SFA_Terry_Prototype_14.gbc'
ROM=OUT/'SFA_Terry_Prototype_15.gbc'
BASE_SHA='93d979b00251ce7293c964d7649f0dc18f6d419623f476f778690fc79182d399'
FULL_BANK=134


def table(b,bank,addr):
    off=fileoff(bank,addr)
    return bytearray(b[off:off+768])


def wider_record(rec):
    """Allow 44 visible pixels only when exact packing still uses <=5/row.

    An invisible pad relocates the eight-pixel tile grid, not the artwork.
    The descriptor format supports this without an engine or OAM change.
    """
    rec=fuller_image(rec,44);im=rec['_image'];options=[]
    for shift in range(8):
        padded=Image.new('P',(im.width+shift,im.height));padded.putpalette(im.getpalette())
        padded.paste(im,(0,0))
        mirrored=padded.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        pieces=pack_body(mirrored.size,mirrored.tobytes(),False)
        counts=[sum(yy<=y<yy+16 for x,yy,r in pieces) for y in range(-16,im.height+16)]
        score=(max(counts),len(pieces),sum(v*v for v in counts),shift)
        options.append((score,padded))
    score,padded=min(options,key=lambda r:r[0]);assert score[0]<=5 and score[1]<=16,(rec['id'],score)
    rec.update(_image=padded,maxwidth=padded.width,optimize_x_grid=False,flexible_y_grid=False,
        grid_pad_right=score[-1])
    return rec


def main():
    base=BASE.read_bytes();assert sha(base)==BASE_SHA
    b=bytearray(base);source=SOURCE.read_bytes();ART_OUT.mkdir(exist_ok=True)
    tiles=Allocator(b,80,111);metadata=Allocator(b,120,127)
    # All new storage is blank in the released base.
    assert set(b[80*0x4000:112*0x4000])=={255}
    assert set(b[120*0x4000:128*0x4000])=={255}
    regions=[]
    def put(bank,addr,data):
        off=fileoff(bank,addr);assert b[off:off+len(data)]==b'\xff'*len(data),(bank,hex(addr),len(data))
        b[off:off+len(data)]=data;b[(bank+1)*0x4000-1]=bank
        regions.append({'bank':bank,'address':hex(addr),'bytes':len(data)})
    def replace(off,old,new):
        assert b[off:off+len(old)]==old and len(old)==len(new),hex(off)
        b[off:off+len(new)]=new

    full=table(b,130,0x5000);stats=[]
    for target,pid in full_mapping().items():
        rec=corrected_record(pid)
        rec=wider_record(rec) if target in (67,79,110) else fuller_image(rec)
        method=rec['adaptation'];correction=rec.get('anchor_correction')
        bank,ptr,stat=encode(b,rec,descriptor(source,0,target),tiles,metadata)
        stat.update(target_id=target,adaptation=method,anchor_correction=correction,table='standard')
        assert stat['max_per_line']<=5,(target,stat)
        full[target*3:target*3+3]=bytes((bank,))+ptr.to_bytes(2,'little')
        stats.append(stat)
        rec['fuller_image'].save(ART_OUT/f'body_{target:03}.png')
    full[235*3:]=full[3:6]*21
    put(FULL_BANK,0x4000,full)

    # One bit for each original fighter/pose. A non-Terry pose using more
    # than five objects on any row needs the established compact opponent.
    # This also covers the wide knockdowns seen in the comparison replay.
    wide=bytearray(13*32)
    for fid in range(13):
        for pose in range(256):
            try:
                d=descriptor(base,fid,pose)
                peak=max((sum(o['y']<=y<o['y']+16 for o in d['objects']) for y in range(-128,128)),default=0)
                crowded=peak>5
            except (AssertionError,ValueError,IndexError):crowded=True
            if crowded:wide[fid*32+pose//8]|=1<<(pose%8)
    put(130,0x6200,wide)
    old_report=json.loads((OUT/'build_14.json').read_text())
    cat=json.loads((MOVE_ART/'catalog.json').read_text())
    for move,name in enumerate(('Backspin Kick','Burn Knuckle','Power Dunk','Fire Kick')):
        tab=bytearray(full)
        for s in old_report['extra_moves']['art']:
            if s['move']!=name or s.get('condition'):continue
            pid=s['source_id'];rec=dict(cat['poses'][pid])
            rec.update(id=pid,_image=indexed(Image.open(MOVE_ART/'poses'/rec['file'])),
                native_offset=native_anchor(cat,s['reference_case'],pid))
            if name=='Burn Knuckle' and rec['_image'].size==(66,42):
                rec=wider_record(rec)
            else:
                rec=fuller_image(rec,48 if name=='Fire Kick' and s['size'][0]==48 else 40)
                rec['flexible_y_grid']=True
            method=rec['adaptation']
            bank,ptr,stat=encode(b,rec,descriptor(source,0,1),tiles,metadata)
            stat.update(move=name,target_id=s['frame_id'],adaptation=method,table=move,
                reference_case=s['reference_case'])
            assert stat['max_per_line']<=5,(name,stat)
            tab[s['frame_id']*3:s['frame_id']*3+3]=bytes((bank,))+ptr.to_bytes(2,'little')
            stats.append(stat)
        put(FULL_BANK,0x4400+move*0x400,tab)

    # Actor graphics identity high-byte 60/64 distinguishes both sets from
    # original Ryu (40) and the other original body tables (42..5E). Alpha
    # shares cached tiles across actors using this byte and the pose ID.
    # No new WRAM allocation or save data needed.
    # Run before both its cache lookup and its upload/descriptor selection.
    c=Asm(0x5c00).emit('f5 c5 d5 e5 7c fec4').jr(0x28,'body')
    c.emit('fec6').jp(0xc2,'done')
    c.label('body').emit('cd0040').jp(0xca,'done')
    c.emit('fa00d2 47 fa00d3 b0 47 fa00d4 b0').jr(0x20,'compact')
    c.emit('cd005d b7').jr(0x20,'compact')
    c.emit('2e13 3660').jr(0x18,'done')
    c.label('compact').emit('2e13 3664')
    c.label('done').emit('e1 d1 c1 f1 7c e0ec 5e 2e29 c9')
    put(130,0x5c00,c.finish())
    replace(0x3f44,bytes.fromhex('7ce0ec5e2e29'),far(0x5c00)+b'\x00')

    c=Asm(0x5d00).emit('e5 7c ee02 67 cd0040').jr(0x20,'not_wide')
    # The engine updates/draws the two actors in order. Enter the fallback
    # early during an original opponent's hit/guard/throw reaction, rather
    # than being one draw late when its next pose suddenly becomes wider.
    c.emit('2e2b 7e b7').jr(0x20,'is_wide')
    c.emit('2e51 7e fe0d').jr(0x30,'not_wide')
    c.emit('5f 1600')
    for _ in range(5):c.emit('cb23 cb12') # DE = fighter ID *32
    c.emit('2e15 7e 4f cb3f cb3f cb3f 83 5f').jr(0x30,'no_carry')
    c.emit('14')
    c.label('no_carry').emit('210062 19 5e 79 e607 47 b7').jr(0x28,'bit')
    c.label('shift').emit('cb3b 05').jr(0x20,'shift')
    c.label('bit').emit('7b e601 e1 c9')
    c.label('is_wide').emit('3e01 e1 c9')
    c.label('not_wide').emit('af e1 c9')
    put(130,0x5d00,c.finish())

    # The selector receives the same actor state for VRAM upload and OAM.
    # Original fighters/projectiles keep the original lookup paths.
    c=Asm(0x4100).emit('cd0040').jp(0xca,'ryu')
    active(c,'standard')
    c.emit('2e13 7e e604').jr(0x20,'compact_move')
    c.emit('2eb3 7e d608 87 87 c644 57 1e00 3e86 c9')
    c.label('compact_move').emit('2eb3 7e fe08').jr(0x20,'old_move')
    c.emit('2e5c 7e b7').jr(0x28,'old_move')
    c.emit('110050 3e85 c9')
    c.label('old_move').emit('2eb3 7e d608 87 87 c640 57 1e00 3e85 c9')
    c.label('standard').emit('7c fec4').jr(0x28,'standard_body')
    c.emit('fec6').jr(0x20,'projectile')
    c.label('standard_body').emit('2e13 7e e604').jr(0x20,'compact_body')
    c.emit('110040 3e86 c9')
    c.label('compact_body').emit('110050 3e82 c9')
    c.label('projectile').emit('2e12 2a 56 5f 7a c610 57 3e82 c9')
    c.label('ryu').emit('2e12 2a 56 5f 3e04 c9')
    code=c.finish();assert len(code)<256
    off=fileoff(130,0x4100);b[off:off+256]=code+b'\xff'*(256-len(code))
    checksums(b);ROM.write_bytes(b)
    report={'rom_sha256':sha(b),'base_sha256':BASE_SHA,'base_unchanged':sha(BASE.read_bytes())==BASE_SHA,
        'graphics_bank':FULL_BANK,'tiles_last_bank':tiles.bank,'metadata_last_bank':metadata.bank,
        'new_regions':regions,'frames':stats,'full_mapping':full_mapping(),
        'mode':'Fuller ordinary art; exact Proto14 graphics during projectiles or original-opponent hit/guard/throw reactions and poses exceeding five objects per row',
        'cache_mode_bit':'actor graphics-table high byte 60/64 (distinct from original fighters; bit2 chooses compact)',
        'gameplay_changes':False,'physical_hardware_tested':False}
    (OUT/'build_15.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('frames','full_mapping','new_regions')},indent=2))


if __name__=='__main__':main()
