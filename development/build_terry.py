"""Convert the user's recovered Terry artwork into Alpha combat sprites.

Terry is a Select-toggle alternate on Ryu, with independent combat and UI art.
Uses Alpha's combat logic with scoped changes to Terry's projectile position.
"""
from sfa_sprite_codec import *
from inspect_engine import EXPECTED, sha
from expansion_probe import checksums
from functools import lru_cache

from terry_native_art import mapping,record,body_image,width_budget,native_neutral,effects as native_effects
OUT=ROOT/'terry_prototype';OUT.mkdir(exist_ok=True)
ROM=OUT/'SFA_Terry_Prototype_14.gbc'

class Allocator:
    def __init__(self,b,first,last):self.b=b;self.bank=first;self.last=last;self.pos=0
    def put(self,data,align=1):
        pos=(self.pos+align-1)//align*align
        if pos+len(data)>0x3fe0:self.bank+=1;pos=0
        assert self.bank<=self.last
        off=self.bank*0x4000+pos
        self.b[off:off+len(data)]=data
        self.b[(self.bank+1)*0x4000-1]=self.bank
        self.pos=pos+len(data)
        return self.bank,0x4000+pos

@lru_cache(maxsize=512)
def pack_body(size,data,fixed):
    im=Image.frombytes('P',size,data)
    columns=[]
    for tx in range(0,im.width,8):
        choices=[]
        for phase in ([0] if fixed else range(16)):
            col=[]
            for ty in range(-phase,im.height,16):
                t=im.crop((tx,ty,tx+8,ty+16));raw=pack(t)
                if any(raw):col.append((tx,ty,raw))
            if not col:col=[(tx,0,bytes(32))]
            if col not in choices:choices.append(col)
        # All choices preserve every pixel. Use the minimum number of tiles,
        # but choose their vertical phases jointly rather than per column.
        count=min(map(len,choices));columns.append([c for c in choices if len(c)==count])
    base=-16;end=im.height+16;beam=[((0,)*(end-base),[],0)]
    for choices in columns:
        candidates=[]
        for col in choices:
            occupancy=tuple(sum(ty<=y<ty+16 for _,ty,_ in col) for y in range(base,end))
            for counts,pieces,penalty in beam:
                ys=[p[1] for p in pieces+col]
                if max(ys)-min(ys)>=64:continue
                combined=tuple(a+b for a,b in zip(counts,occupancy));cost=penalty+sum(abs(ty) for _,ty,_ in col)
                candidates.append((combined,pieces+col,cost))
        assert candidates,('No encodable packing',size)
        candidates.sort(key=lambda z:(max(z[0]),sum(v*v for v in z[0]),z[2]))
        beam=candidates[:32]
    return tuple(beam[0][1])

@lru_cache(maxsize=128)
def pack_sparse_body(size,data,budget=()):
    """Place 8x16 objects independently within each column.

    A uniform vertical grid makes empty padding consume the ten-object
    scanline budget. Allow gaps between the tiles when their pixels permit
    it, while retaining every source pixel and the original object format.
    """
    im=Image.frombytes('P',size,data);columns=[]
    for tx in range(0,im.width,8):
        opaque=tuple(y for y in range(im.height) if any(im.getpixel((x,y)) for x in range(tx,min(tx+8,im.width))))
        if not opaque:columns.append([[(tx,0,bytes(32))]]);continue
        @lru_cache(maxsize=None)
        def covers(left,previous):
            if left==len(opaque):return ((),)
            first=opaque[left];options=[]
            for start in range(max(previous,first-15),first+1):
                nxt=left
                while nxt<len(opaque) and opaque[nxt]<start+16:nxt+=1
                for tail in covers(nxt,start+16):options.append((start,)+tail)
            least=min(map(len,options));return tuple(o for o in options if len(o)==least)
        starts=covers(0,-16)
        columns.append([[(tx,ty,pack(im.crop((tx,ty,tx+8,ty+16)))) for ty in ys] for ys in starts])
    base=-16;end=im.height+16;beam=[((0,)*(end-base),[],0)];limits=dict(budget)
    for choices in columns:
        options=[]
        for col in choices:
            occupancy=tuple(sum(ty<=y<ty+16 for _,ty,_ in col) for y in range(base,end))
            for counts,pieces,penalty in beam:
                ys=[p[1] for p in pieces+col]
                if max(ys)-min(ys)>=64:continue
                combined=tuple(a+b for a,b in zip(counts,occupancy))
                cost=penalty+sum(abs(ty) for _,ty,_ in col)
                options.append((combined,pieces+col,cost))
        assert options,('No sparse packing',size)
        def score(v):
            counts,pieces,cost=v
            excess=sum(max(0,counts[y-base]-limit) for y,limit in limits.items())
            return (excess,max(counts),sum(n*n for n in counts),len(pieces),cost)
        options.sort(key=score);beam=options[:48]
    return tuple(beam[0][1])

def prepare(rec,target,maxwidth=40):
    if rec.get('effect'):
        im=rec['_image'].transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        x=-im.width//2;y=-3-im.height
    else:im,x,y=body_image(rec,rec.get('maxwidth',maxwidth))
    pieces=list(pack_sparse_body(im.size,im.tobytes(),tuple(rec.get('row_budget',()))) if rec.get('flexible_y_grid')
                else pack_body(im.size,im.tobytes(),bool(rec.get('fixed_grid'))))
    if rec.get('optimize_x_grid'):
        # Shift the invisible tile grid, not the artwork. Native idle 1/2
        # need only twelve objects on a grid displaced by two pixels, versus
        # thirteen on the crop boundary; all source pixels keep their world
        # coordinates. Never introduce a sixth horizontal column.
        options=[]
        for shift in range(min(7,40-im.width)+1):
            padded=Image.new('P',(im.width+shift,im.height));padded.putpalette(im.getpalette())
            padded.paste(im,(shift,0))
            packed=list(pack_body(padded.size,padded.tobytes(),False))
            counts=[sum(ty<=line<ty+16 for tx,ty,raw in packed) for line in range(-16,im.height+16)]
            cost=(max(counts),sum(v>=5 for v in counts),len(packed),sum(v*v for v in counts),shift)
            options.append((cost,padded,packed,shift))
        _,im,pieces,shift=min(options,key=lambda v:v[0]);x-=shift
    miny=min(z[1] for z in pieces);pieces=[(tx,ty-miny,raw) for tx,ty,raw in pieces]
    y+=miny
    assert len(pieces)<=20,(rec['id'],len(pieces))
    assert all(0<=ty<64 for tx,ty,raw in pieces),(rec['id'],pieces)
    return im,x,y,pieces

def encode(b,rec,target,tiles,metadata):
    im,x,y,pieces=prepare(rec,target)
    raw=b''.join(r for tx,ty,r in pieces);bank,addr=tiles.put(raw,16)
    commands=bytearray([((bank-0x25)<<1)|1]);remaining=len(raw)//16
    while remaining:
        count=min(8,remaining)
        commands+=bytes([(addr&0xf0)|((count-1)<<1),addr>>8])
        addr+=16*count;remaining-=count
    assert len(commands)<=45
    anchor=-y;height=min(max(anchor,0),im.height//2)
    assert 0<=-x<=255 and 0<=anchor-height<=255
    data=bytearray([len(commands)])+commands+bytes([-x,anchor-height,height])
    lastx=0
    for tx,ty,r in pieces:
        assert tx-lastx in (0,8)
        data.append((ty<<2)|(2 if tx!=lastx else 0));lastx=tx
    data.append(3)
    mb,mp=metadata.put(data)
    decoded=decode(b,mb,mp)
    assert decoded['tilebytes']==raw
    assert len(decoded['objects'])==len(pieces)
    for obj,(tx,ty,r) in zip(decoded['objects'],pieces):
        assert (obj['x'],obj['y'])==(x+tx,y+ty)
    line=max(sum(o['y']<=scan<o['y']+16 for o in decoded['objects']) for scan in range(-100,80))
    return mb,mp,{'source_id':rec['id'],'objects':len(pieces),'max_per_line':line,'size':list(im.size),'x':x,'y':y,'adaptation':rec.get('adaptation'),'native_size':rec.get('size')}

def terry_hud_name(b):
    # Ryu's left and right HUD names occupy four 8x8 tiles each. A compact
    # six-row italic alphabet fits TERRY into those existing 32-pixel slots.
    glyphs={'T':['11111','00100','00100','00100','00100','00100'],
            'E':['11111','10000','11110','10000','10000','11111'],
            'R':['11110','10001','11110','10100','10010','10001'],
            'Y':['10001','10001','01010','00100','00100','00100']}
    im=Image.new('P',(32,8),0)
    for n,ch in enumerate('TERRY'):
        for y,row in enumerate(glyphs[ch]):
            for x,on in enumerate(row):
                if on=='1':im.putpixel((n*6+x+(5-y)//2,y+1),(1,1,1,2,2,3)[y])
    raw=b''.join(pack(im.crop((x,0,x+8,16)))[:16] for x in range(0,32,8))
    assert b[0x2ca30:0x2ca40]==bytes.fromhex('00ff3ec133c066cc7ca8cccdcede0011')
    b[0x2ca30:0x2cab0]=raw+raw

def main():
    source=SOURCE.read_bytes();assert sha(source)==EXPECTED
    b=bytearray(source+b'\xff'*(4*1024*1024-len(source)));b[0x148]=7
    table=130*0x4000+0x1000
    b[table:table+235*3]=source[0x10000:0x10000+235*3]
    tiles=Allocator(b,64,111);metadata=Allocator(b,112,127)
    links={};stats=[]
    for target,origin in mapping().items():
        old=descriptor(source,0,target)
        if not render(old)[0].getbbox():continue
        rec=record(origin)
        # Cast frames share scanlines with a projectile, so reserve two
        # additional columns across the pair of actors.
        rec['maxwidth']=width_budget(target)
        rec['optimize_x_grid']=native_neutral(target)
        bank,ptr,stat=encode(b,rec,old,tiles,metadata)
        links[target]=(bank,ptr);stat['target_id']=target;stats.append(stat)
        off=table+target*3
        b[off:off+3]=bytes([bank])+ptr.to_bytes(2,'little')
    from terry_geyser import install
    effectdir=OUT/('converted_effects_'+ROM.stem[-2:]);effectdir.mkdir(exist_ok=True)
    for target,rec in native_effects().items():
        rec['_image'].save(effectdir/f'effect_{target}.png')
        bank,ptr,stat=encode(b,rec,descriptor(source,0,target),tiles,metadata)
        links[target]=(bank,ptr);stat['target_id']=target;stats.append(stat)
        off=table+target*3;b[off:off+3]=bytes([bank])+ptr.to_bytes(2,'little')
    # Shared normal-projectile initialization: change world Y only when the
    # owner is the replaced Ryu slot. Collision and rendering both use this Y.
    gameplay_hooks=install(b,variant=True)
    # Fighter palette blocks overlap at transparent entries (six-byte stride).
    poff=0x24*0x4000+0x21f9
    def rgb(r,g,bl):return (r|(g<<5)|(bl<<10)).to_bytes(2,'little')
    palette=bytearray(source[poff:poff+24])
    palette[2:8]=rgb(0,0,0)+rgb(31,0,0)+rgb(31,31,31)
    palette[8:14]=rgb(0,0,0)+rgb(0,12,31)+rgb(31,31,31)
    palette[14:20]=rgb(29,10,0)+rgb(31,29,0)+rgb(31,31,31)
    from terry_variant import install as install_variant
    variant_hooks=install_variant(b,source,palette)
    extra_moves=None
    if int(ROM.stem[-2:])>=14:
        from terry_moves_14 import install as install_moves
        extra_moves=install_moves(b,source,tiles,metadata,encode,descriptor)
    checksums(b);ROM.write_bytes(b)
    report={'rom_sha256':sha(b),'source_sha256':sha(source),'art_source':'Owned original NGPC MOTM ROM; native sprite and foreground-layer captures',
            'alternate_slot':'Select on Ryu; Ryu retained','graphics_ids_replaced':len(links),'converted_terry_frames':len(set(mapping().values())),
            'tiles_last_bank':tiles.bank,'metadata_last_bank':metadata.bank,
            'mapping':mapping(),'frames':stats,'art_source_sha256':__import__('terry_native_art').catalog()['rom_sha256'],
            'projectile_hooks':gameplay_hooks,
            'variant_hooks':variant_hooks,
            'extra_moves':extra_moves,
            'gameplay':'Alpha/Ryu base. Terry normal Power Wave retained; super is a finite stationary tall eruption with a matching taller hitbox. Combat artwork uses native NGPC poses; wide extensions adapted to GBC limits.'}
    (OUT/('build_'+ROM.stem[-2:]+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('frames','mapping')},indent=2))

if __name__=='__main__':main()
