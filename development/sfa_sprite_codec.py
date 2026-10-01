"""Decode Alpha combat-frame pointers, DMA commands and compact OAM layouts.

Reverse engineered from fixed-bank $18A1, $1424-$15CF, $15D0-$16BF.
Does not execute, change or distribute the input ROM.
"""
from inspect_engine import ROOT, SOURCE
from PIL import Image, ImageDraw
import json

TABLES=[0x4000,0x42c1,0x456d,0x48b8,0x4b2b,0x4dfe,0x50b3,0x52fc,0x55e1,0x57e5,0x5abe,0x5ca7,0x5eff]

def fileoff(bank, ptr):
    assert 0x4000<=ptr<0x8000
    return bank*0x4000+ptr-0x4000

def pixels(raw):
    assert len(raw)==32
    tile=Image.new('P',(8,16),0)
    for y in range(16):
        lo,hi=raw[y*2:y*2+2]
        for x in range(8): tile.putpixel((x,y),((lo>>(7-x))&1)|(((hi>>(7-x))&1)<<1))
    return tile

def pack(tile):
    assert tile.size==(8,16)
    out=bytearray()
    for y in range(16):
        lo=hi=0
        for x in range(8):
            v=tile.getpixel((x,y));assert 0<=v<4
            lo|=(v&1)<<(7-x);hi|=(v>>1)<<(7-x)
        out+=bytes([lo,hi])
    return bytes(out)

def descriptor(b, fid, frame):
    ptr=4*0x4000+TABLES[fid]-0x4000+frame*3
    bank=b[ptr];address=int.from_bytes(b[ptr+1:ptr+3],'little')
    return decode(b,bank,address)

def decode(b,bank,address):
    off=fileoff(bank,address);n=b[off];cmd=b[off+1:off+1+n]
    tilebytes=bytearray();srcbank=None;i=0;transfers=[]
    while i<len(cmd):
        first=cmd[i];i+=1
        if first==255:
            tilebytes+=bytes(16);transfers.append({'zero':16})
        elif first&1:
            srcbank=(first>>1)+0x25
        else:
            assert srcbank is not None
            second=cmd[i];i+=1
            addr=(second<<8)|(first&0xf0);size=(((first&14)>>1)+1)*16
            start=fileoff(srcbank,addr)
            tilebytes+=b[start:start+size]
            transfers.append({'bank':srcbank,'address':addr,'size':size})
    pos=off+1+n;anchorx,anchory,height=b[pos:pos+3];pos+=3
    objs=[];x=0
    for j in range(41):
        v=b[pos];pos+=1
        if v==3:break
        if v&2:x+=8
        objs.append({'x':x-anchorx,'y':(v>>2)-anchory-height,'palette_add':v&1})
    else:raise ValueError('unterminated object list')
    assert len(tilebytes)>=len(objs)*32,(bank,address,len(tilebytes),len(objs))
    # Proto16's explicitly tagged extension stores independent horizontal
    # offsets. Original Alpha resources never occupy these metadata banks.
    free_x=False
    if 220<=bank<=223 and b[pos:pos+2]==bytes([0xfd,0x16]):
        pos+=2
        for j,obj in enumerate(objs):obj['x']+=b[pos+j]
        pos+=len(objs);free_x=True
    return {'bank':bank,'address':address,'offset':off,'size':pos-off,'commands':cmd.hex(),
            'anchor_x':anchorx,'anchor_y':anchory,'height':height,'objects':objs,
            'tilebytes':bytes(tilebytes),'transfers':transfers,'free_x':free_x}

PALETTE=[(0,0,0),(35,29,39),(182,135,72),(255,229,185),
         (0,0,0),(35,29,39),(177,45,50),(255,240,220)]

def render(frame):
    objs=frame['objects']
    if not objs:return Image.new('RGBA',(1,1)),(0,0)
    left=min(o['x'] for o in objs);top=min(o['y'] for o in objs)
    right=max(o['x']+8 for o in objs);bottom=max(o['y']+16 for o in objs)
    im=Image.new('RGBA',(right-left,bottom-top))
    for j,o in reversed(list(enumerate(objs))):
        tile=pixels(frame['tilebytes'][j*32:(j+1)*32])
        for y in range(16):
            for x in range(8):
                v=tile.getpixel((x,y))
                if v:im.putpixel((o['x']-left+x,o['y']-top+y),PALETTE[v+4*o['palette_add']]+(255,))
    return im,(left,top)

def atlas(items,path,cols=12,cell=(88,86)):
    w,h=cell;im=Image.new('RGB',(cols*w,((len(items)+cols-1)//cols)*h),(48,56,66));d=ImageDraw.Draw(im)
    for n,(label,pic) in enumerate(items):
        x=(n%cols)*w;y=(n//cols)*h
        d.text((x+2,y+2),str(label),fill='white')
        im.paste(pic,(x+(w-pic.width)//2,y+18),pic if pic.mode=='RGBA' else None)
    im.save(path)

def main():
    b=SOURCE.read_bytes();out=ROOT/'reverse/ryu_frames';out.mkdir(parents=True,exist_ok=True)
    items=[];records=[]
    for i in range((TABLES[1]-TABLES[0])//3):
        f=descriptor(b,0,i);im,xy=render(f)
        im.save(out/f'frame_{i:03d}.png')
        items.append((i,im));records.append({k:v for k,v in f.items() if k!='tilebytes'})
        assert all(pack(pixels(f['tilebytes'][j:j+32]))==f['tilebytes'][j:j+32] for j in range(0,len(f['objects'])*32,32))
    atlas(items,ROOT/'reverse/ryu_atlas.png')
    (ROOT/'reverse/ryu_frame_records.json').write_text(json.dumps(records,indent=2)+'\n')
    print('Decoded and tile-roundtripped',len(records),'frames')

if __name__=='__main__':main()
