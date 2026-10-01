"""Recovery-specific tumbling art on Proto19; never apply Proto20's global shift.

Reuse the complete native bent-knee get-up drawing as a tucked roll, rotated in
90-degree steps without resampling. Counter the original animation's deliberate
half-cycle X reversal, and centre these four drawings on Alpha's roll pivot.
All other descriptor pointers, body anchors, gameplay and timing are preserved.
"""
import json
from PIL import Image,ImageDraw
from inspect_engine import ROOT,sha
from terry_native_art import catalog,record,BODY_PALETTE
from build_terry import Allocator,pack_body
from build_terry_16 import encode,pixelmap
from sfa_sprite_codec import fileoff,decode,descriptor
from expansion_probe import checksums
from package_probe import SOURCE

OUT=ROOT/'terry_prototype';DEST=OUT/'evidence_21';DEST.mkdir(exist_ok=True)
BASE=OUT/'SFA_Terry_Prototype_19.gbc'
BASE_SHA='a3e97581585c56288721d6b2772e91de3e072f1c52db1495c99fead9706c119b'
ROM=DEST/'SFA_Terry_Prototype_21_candidate.gbc'
TABLES=((130,0x5000),(134,0x4000))

def main():
    old=BASE.read_bytes();assert sha(old)==BASE_SHA;b=bytearray(old)
    for bank in (146,225):assert set(b[bank*16384:(bank+1)*16384])=={255}
    tiles=Allocator(b,146,146);meta=Allocator(b,225,225)
    pid=catalog()['cases']['hit_reactions_full']['unique'][14]
    native=record(pid)['_image'];native_count=sum(v!=0 for v in native.tobytes())
    tiles_used=[];changes=[];panels=[];clean=SOURCE.read_bytes()
    transforms=(Image.Transpose.ROTATE_270,Image.Transpose.ROTATE_180,Image.Transpose.ROTATE_90,None)
    for pose,rotation in zip(range(42,46),transforms):
        # Desired on-screen right-facing orientation. Alpha flips only the
        # first half of each roll, so normalize those two descriptor drawings.
        desired=native.transpose(rotation) if rotation is not None else native.copy()
        im=desired.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if pose<44 else desired.copy()
        coords=[(x,y) for y in range(im.height) for x in range(im.width) if im.getpixel((x,y))]
        assert len(coords)==native_count
        # Alpha renders at worldX-10 (flipped) or worldX+18 (unflipped).
        # mean local X=-10.5 keeps both presentations at worldX-0.5.
        x=round(-10.5-sum(xx for xx,yy in coords)/len(coords))
        y=round(-33-(im.height-1)/2)
        pieces=[(tx+x,ty+y,raw) for tx,ty,raw in pack_body(im.size,im.tobytes(),False)]
        original=descriptor(clean,0,pose)
        bank,ptr=encode(b,pieces,tiles,meta,original);d=decode(b,bank,ptr)
        wanted={(xx+x,yy+y):im.getpixel((xx,yy)) for xx,yy in coords}
        assert pixelmap(d)==wanted
        peak=max(sum(o['y']<=sy<o['y']+16 for o in d['objects']) for sy in range(-100,80))
        assert peak<=5 and len(d['objects'])<=16
        for tb,addr in TABLES:
            at=fileoff(tb,addr)+pose*3
            before=bytes(b[at:at+3]);b[at:at+3]=bytes([bank])+ptr.to_bytes(2,'little')
            changes.append({'offset':at,'old':before.hex(),'new':b[at:at+3].hex(),'pose':pose,'table':[tb,addr]})
        # Store exact indexed descriptor and upright-facing preview sources.
        im.putpalette(BODY_PALETTE);im.save(DEST/f'roll_{pose}_descriptor.png',transparency=0)
        desired.putpalette(BODY_PALETTE);desired.save(DEST/f'roll_{pose}_display.png',transparency=0)
        info={'pose':pose,'source_id':pid,'source_size':list(native.size),'size':list(im.size),
              'source_pixels':native_count,'all_source_pixels_preserved':True,'scaling':False,
              'x':x,'y':y,'objects':len(d['objects']),'max_per_row':peak,
              'mean_local_x':sum(px for px,py in wanted)/len(wanted),'descriptor':[bank,ptr]}
        tiles_used.append(info)
        rgba=desired.convert('RGBA');rgba.putalpha(Image.frombytes('L',desired.size,bytes(255 if v else 0 for v in desired.tobytes())))
        panels.append(rgba)
    checksums(b)
    allowed={0x14e,0x14f}|{p['offset']+n for p in changes for n in range(3)}
    allowed.update(range(146*16384,147*16384));allowed.update(range(225*16384,226*16384))
    delta={i for i,(a,z) in enumerate(zip(old,b)) if a!=z}
    assert delta<=allowed
    ROM.write_bytes(b)
    report={'rom_sha256':sha(b),'base_sha256':BASE_SHA,'changed_bytes':len(delta),'pointers':changes,'frames':tiles_used,
            'scope':'Four Terry rolling recovery descriptors (42-45), their new artwork and checksums only. Proto19 gameplay code, timing, damage and all other artwork are untouched.',
            'code_unchanged':True,'physical_hardware_tested':False}
    (OUT/'build_21.json').write_text(json.dumps(report,indent=2)+'\n')
    sheet=Image.new('RGB',(640,180),(55,70,85));dr=ImageDraw.Draw(sheet)
    for n,im in enumerate(panels):
        dr.text((n*160+8,4),f'Roll {42+n}',fill='white');im=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST)
        sheet.paste(im,(n*160+(160-im.width)//2,28),im)
    sheet.save(DEST/'roll_source_sheet.png')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
