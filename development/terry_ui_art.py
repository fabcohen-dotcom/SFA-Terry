"""Convert the owned NGPC portrait and native pixel lettering into GBC art."""
from PIL import Image, ImageDraw
from inspect_engine import ROOT
from sfa_sprite_codec import pack

OUT=ROOT/'terry_prototype/art_07'
GLYPHS={
 'T':['11111','00100','00100','00100','00100','00100','00100'],
 'E':['11111','10000','10000','11110','10000','10000','11111'],
 'R':['11110','10001','10001','11110','10100','10010','10001'],
 'Y':['10001','10001','01010','00100','00100','00100','00100']}

def tilebytes(im):
    return b''.join(pack(im.crop((x,y,x+8,y+16)))[:16]
                    for y in range(0,im.height,8) for x in range(0,im.width,8))

def rgb15(rgb):
    r,g,b=rgb;return ((r//8)|((g//8)<<5)|((b//8)<<10)).to_bytes(2,'little')

def make():
    OUT.mkdir(exist_ok=True)
    src=Image.open(ROOT/'terry_prototype/ngpc_reference/terry_portrait_07.png').convert('RGB')
    # The game's animated "OK" UI overlaps the empty space beside the head.
    # Remove only that known UI rectangle before adapting the portrait.
    ImageDraw.Draw(src).rectangle((107,42,114,54),fill=(0,170,255))
    src=src.crop((50,25,112,104)).resize((40,51),Image.Resampling.NEAREST)
    bg=(0,168,216);dark=(16,24,40);skin=(248,200,136);red=(224,48,32);white=(248,240,216)
    pals=[[bg,dark,red,skin],[bg,dark,white,skin]]
    im=Image.new('RGB',(40,56),bg)
    for y in range(51):
        for x in range(40):
            r,g,b=src.getpixel((x,y))
            if (r<20 and 150<g<185 and b>235) or (r>240 and 80<g<115 and b>220):color=bg
            elif r>235 and g>235 and b>235:color=white
            elif r>140 and g<70 and b<80:color=red
            elif r>180 and g>95 and b<210:color=skin
            else:color=dark
            im.putpixel((x,y+2),color)
    raw=bytearray();attrs=[];preview=Image.new('RGB',im.size)
    for ty in range(0,56,8):
        for tx in range(0,40,8):
            tile=im.crop((tx,ty,tx+8,ty+8));candidates=[]
            for pal in pals:
                indexed=Image.new('P',(8,8));err=0
                for y in range(8):
                    for x in range(8):
                        rgb=tile.getpixel((x,y));d=[sum((a-b)**2 for a,b in zip(rgb,c)) for c in pal]
                        idx=min(range(4),key=lambda i:d[i]);indexed.putpixel((x,y),idx);err+=d[idx]
                candidates.append((err,indexed))
            p=min(range(2),key=lambda i:candidates[i][0]);t=candidates[p][1]
            raw+=tilebytes(t);attrs.append(p)
            t.putpalette(sum((list(c) for c in pals[p]),[])+[0]*756)
            preview.paste(t.convert('RGB'),(tx,ty))
    preview.save(OUT/'terry_portrait.png')
    preview.resize((240,336),Image.Resampling.NEAREST).save(OUT/'terry_portrait_preview.png')
    # 16x16 face, three colors plus transparency, aligned to the body palette.
    face=Image.open(ROOT/'terry_prototype/ngpc_reference/terry_portrait_07.png').convert('RGB').crop((63,27,100,61)).resize((16,16),Image.Resampling.NEAREST)
    icon=Image.new('P',(16,16),0)
    for y in range(16):
        for x in range(16):
            r,g,b=face.getpixel((x,y))
            idx=0 if ((r<20 and g>150 and b>230) or (r>240 and 80<g<115 and b>220)) else (2 if r>140 and g<80 else (3 if r>175 and g>90 else 1))
            icon.putpixel((x,y),idx)
    icon.putpalette([0,168,216,24,24,40,208,48,40,248,200,128]+[0]*756)
    icon.save(OUT/'terry_hud_face.png')
    # HUD objects are 8x16, stored by column (left top/bottom, right top/bottom).
    iconraw=pack(icon.crop((0,0,8,16)))+pack(icon.crop((8,0,16,16)))
    # The roster selection is an OBJ overlay above the original Ryu BG icon.
    # Unlike the HUD, its transparent pixels expose another character's face.
    # Preserve all face pixels, but make empty space opaque palette-1 black.
    roster=icon.copy()
    for y in range(16):
        for x in range(16):
            if roster.getpixel((x,y))==0:roster.putpixel((x,y),1)
    roster.save(OUT/'terry_roster_face_13.png')
    rosterraw=pack(roster.crop((0,0,8,16)))+pack(roster.crop((8,0,16,16)))
    # Native 64x24 lettering. Large warm letters, dark outline, slight italic.
    name=Image.new('P',(64,24),0);mask=Image.new('1',name.size)
    for n,ch in enumerate('TERRY'):
        for y,row in enumerate(GLYPHS[ch]):
            for x,on in enumerate(row):
                if on=='1':
                    for yy in range(2):
                        for xx in range(2):mask.putpixel((3+n*11+x*2+xx+(6-y)//3,4+y*2+yy),1)
    for y in range(24):
        for x in range(64):
            if mask.getpixel((x,y)):name.putpixel((x,y),1 if y<11 else 2)
            elif any(0<=x+dx<64 and 0<=y+dy<24 and mask.getpixel((x+dx,y+dy)) for dx,dy in ((0,1),(1,0),(-1,0),(0,-1))):name.putpixel((x,y),3)
    name.putpalette([0,168,216,248,216,0,248,80,0,16,16,24]+[0]*756);name.save(OUT/'terry_name.png')
    hud=Image.new('P',(32,8),0)
    for n,ch in enumerate('TERRY'):
        for y,row in enumerate(GLYPHS[ch]):
            for x,on in enumerate(row):
                if on=='1':hud.putpixel((n*6+x+(6-y)//3,y),1 if y<3 else 3)
    hud.putpalette([0,0,0,248,248,0,0,0,248,248,0,0]+[0]*756);hud.save(OUT/'terry_hud_name.png')
    return {'portrait':bytes(raw),'attrs':bytes(attrs),'palettes':b''.join(rgb15(c) for p in pals for c in p),
            'face':iconraw,'roster_face':rosterraw,'name':tilebytes(name),'hud_name':tilebytes(hud)}

if __name__=='__main__':print({k:len(v) for k,v in make().items()})
