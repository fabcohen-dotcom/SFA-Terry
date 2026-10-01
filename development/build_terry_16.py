"""Lossless sprite repacking, informed by consecutive-frame overlap captures.

No scaling, erased pixels or palette approximation. Rebuild from preserved 15.
"""
import json,collections
from pathlib import Path
import numpy as np
from PIL import Image
from sfa_sprite_codec import decode,descriptor,fileoff,pixels,pack,TABLES
from build_terry import Allocator
from inspect_engine import ROOT,sha
from expansion_probe import checksums

OUT=ROOT/'terry_prototype';BASE=OUT/'SFA_Terry_Prototype_15.gbc';ROM=OUT/'SFA_Terry_Prototype_16.gbc'
BASE_SHA='8ed30e457882b8299f03678808626348b8feca704b02cabca92204719c465a97'
LOW=-112;HIGH=80;YS=np.arange(LOW,HIGH)

def key(mem,terry=False):
    pose=mem[21]
    if not terry:return 4,TABLES[mem[0x51]],pose
    custom=mem[0x2a:0x2d]==[1,0,7] and 8<=mem[0xb3]<12 if len(mem)>0xb3 else False
    # Captures store 128 body bytes, so the four newly added moves are not
    # optimization targets; their frame IDs >=235 distinguish that path.
    if pose>=235:return None
    return (130,0x5000,pose) if mem[19]&4 else (134,0x4000,pose)

def lookup(b,k):
    bank,table,pose=k;at=fileoff(bank,table)+pose*3
    return decode(b,b[at],int.from_bytes(b[at+1:at+3],'little'))

def pixelmap(d):
    out={}
    for j,o in reversed(list(enumerate(d['objects']))):
        t=pixels(d['tilebytes'][j*32:(j+1)*32])
        for y in range(16):
            for x in range(8):
                v=t.getpixel((x,y))
                if v:out[o['x']+x,o['y']+y]=v+4*o['palette_add']
    return out

def counts(d,delta=0):
    return np.array([sum(o['y']+delta<=y<o['y']+delta+16 for o in d['objects']) for y in YS],dtype=np.int16)

def contexts(b,receiving=False):
    scenarios=set()
    paths=list((OUT/'clipping_15').glob('*.json'))
    if receiving:paths+=list((OUT/'clipping_received_15').glob('*.json'))
    for p in sorted(paths):
        if p.name=='results.json':continue
        report=json.loads(p.read_text());players=report.get('terry_players',[1,2] if report['opponent']=='Terry' else [1])
        p1terry=1 in players;p2terry=2 in players
        for row in report['rows']:
            actors=[]
            for name,mem,terry in [('p1',row['p1'],p1terry),('p2',row['p2'],p2terry)]:
                k=key(mem,terry)
                if not k or not mem[0x29] or mem[0x17]&2:break
                actors.append((k,mem[15]-16))
            else:
                for mem in row['fx']:
                    if not mem[0] or not mem[0x29]:continue
                    own_terry=mem[0x52]==0xc4 and p1terry or mem[0x52]==0xc6 and p2terry
                    bank=130 if own_terry else 4
                    table=mem[18]+(mem[19]<<8)+(0x1000 if own_terry else 0)
                    if 0x4000<=table<0x8000:actors.append(((bank,table,mem[21]),mem[15]-16))
                # Normalize common vertical origin; retain each distinct scene.
                scenarios.add(tuple((k,y-actors[0][1]) for k,y in actors))
    return sorted(scenarios)

def encode(b,pieces,tiles,meta,original):
    pieces=sorted(pieces,key=lambda z:(z[0],z[1]));minx=min(x for x,y,raw in pieces);miny=min(y for x,y,raw in pieces)
    assert 0<=-minx<256 and 0<=-miny<256
    assert max(y for x,y,r in pieces)-miny<64
    raw=b''.join(r for x,y,r in pieces);bank,ptr=tiles.put(raw,16);cmd=bytearray([((bank-37)<<1)|1]);n=len(raw)//16
    while n:
        size=min(n,8);cmd+=bytes([(ptr&0xf0)|((size-1)<<1),ptr>>8]);ptr+=size*16;n-=size
    assert len(cmd)<=45
    # Alpha's vertical flip axis depends on anchor_y alone. Retain it.
    origin=min(miny,-original['anchor_y']);height=-origin-original['anchor_y']
    assert max(y for x,y,r in pieces)-origin<64
    data=bytearray([len(cmd)])+cmd+bytes([-minx,original['anchor_y'],height]);prev=minx
    for x,y,r in pieces:
        assert x-prev in (0,8)
        data.append(((y-origin)<<2)|(2 if x!=prev else 0));prev=x
    data.append(3);return meta.put(data)

def repack(d,cost):
    pix=pixelmap(d)
    if not pix or any(v>3 for v in pix.values()):return None
    left=min(x for x,y in pix);right=max(x for x,y in pix);top=min(y for x,y in pix);bottom=max(y for x,y in pix)
    oldcount=counts(d);oldscore=int(cost[np.arange(len(YS)),oldcount].sum())
    if not oldscore:return None
    # Never increase the maximum occupied objects on a row or total tile load.
    maxpeak=int(oldcount.max());maxobjects=len(d['objects']);best=None
    for shift in range(8):
        x0=left-shift;columns=[]
        for x in range(x0,right+1,8):
            choices=[]
            for phase in range(16):
                pieces=[]
                for y in range(top-phase,bottom+1,16):
                    t=Image.new('P',(8,16))
                    for yy in range(16):
                        for xx in range(8):t.putpixel((xx,yy),pix.get((x+xx,y+yy),0))
                    raw=pack(t)
                    if any(raw):pieces.append((x,y,raw))
                if not pieces:pieces=[(x,top,bytes(32))]
                if pieces not in choices:choices.append(pieces)
            columns.append(choices)
        beam=[(np.zeros(len(YS),dtype=np.int16),[],1000,-1000)]
        for choices in columns:
            candidates=[];arrays=[]
            for col in choices:
                ys=[p[1] for p in col];occupancy=sum((YS>=y)&(YS<y+16) for y in ys)
                for cnt,pieces,lo,hi in beam:
                    if len(pieces)+len(col)>maxobjects:continue
                    low=min(lo,min(ys));high=max(hi,max(ys))
                    if high-low>=64:continue
                    nc=cnt+occupancy
                    if nc.max()>maxpeak:continue
                    candidates.append((nc,pieces+col,low,high));arrays.append(nc)
            if not candidates:beam=[];break
            ar=np.array(arrays);scores=cost[np.arange(len(YS))[None,:],ar].sum(axis=1)
            ranks=sorted(range(len(candidates)),key=lambda i:(scores[i],int(ar[i].max()),len(candidates[i][1]),int((ar[i]*ar[i]).sum())))[:24]
            beam=[candidates[i] for i in ranks]
        for cnt,pieces,lo,hi in beam:
            score=int(cost[np.arange(len(YS)),cnt].sum())
            rank=(score,int(cnt.max()),len(pieces),int((cnt*cnt).sum()))
            if score<oldscore and (best is None or rank<best[0]):best=(rank,pieces)
    return best

def main():
    old=BASE.read_bytes();assert sha(old)==BASE_SHA;b=bytearray(old)
    tiles=Allocator(b,144,164);meta=Allocator(b,208,219)
    assert set(b[144*0x4000:165*0x4000])=={255} and set(b[208*0x4000:220*0x4000])=={255}
    scenes=contexts(b);keys={k for scene in scenes for k,y in scene};descs={k:lookup(b,k) for k in keys};changes=[]
    for iteration in range(2):
        # Rebuild pairwise row costs after each pass. Only opaque-preserving
        # layouts are eligible, and the legacy descriptor is always retained
        # unless a candidate lowers this measured overlap cost.
        costs={k:np.zeros((len(YS),41),dtype=np.int64) for k in keys}
        for scene in scenes:
            for index,(k,origin) in enumerate(scene[:2]):
                other=sum((counts(descs[otherk],otherorigin-origin) for j,(otherk,otherorigin) in enumerate(scene) if j!=index),start=np.zeros(len(YS),dtype=np.int16))
                cost=np.maximum(0,np.arange(41)[None,:]+other[:,None]-10)**2
                costs[k]+=cost
        todo=sorted(keys,key=lambda k:int(costs[k][np.arange(len(YS)),counts(descs[k])].sum()),reverse=True)
        for k in todo:
            # The two fighters only. FX sources retain their existing art.
            if k[0]==130 and k[1]!=0x5000 or k[0]==4 and k[1] not in TABLES:continue
            d=descs[k];answer=repack(d,costs[k])
            if answer is None:continue
            rank,pieces=answer;bank,ptr=encode(b,pieces,tiles,meta,d);new=decode(b,bank,ptr)
            assert pixelmap(d)==pixelmap(new)
            at=fileoff(k[0],k[1])+k[2]*3;b[at:at+3]=bytes([bank])+ptr.to_bytes(2,'little')
            before=int(costs[k][np.arange(len(YS)),counts(d)].sum());descs[k]=new
            changes.append({'iteration':iteration,'table':k,'before_cost':before,'after_cost':rank[0],
                'before_objects':len(d['objects']),'after_objects':len(pieces),'pixels_and_anchors_identical':True})
            print('PASS',iteration,k,before,'->',rank[0],'objects',len(d['objects']),'->',len(pieces),flush=True)
    checksums(b);ROM.write_bytes(b)
    report={'rom_sha256':sha(b),'base_sha256':BASE_SHA,'base_preserved':sha(BASE.read_bytes())==BASE_SHA,
        'changes':changes,'unique_layouts':len({tuple(c['table']) for c in changes}),
        'tile_last_bank':tiles.bank,'metadata_last_bank':meta.bank,'reference_scenes':len(scenes),
        'scope':'Lossless tile placement only. All visible indexed pixels, world anchors, sprite palettes and gameplay code are retained.'}
    (OUT/'build_16.json').write_text(json.dumps(report,indent=2)+'\n');print('ROM',report['rom_sha256'],flush=True)

if __name__=='__main__':main()
