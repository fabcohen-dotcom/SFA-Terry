"""Native MOTM artwork and explicit semantic mapping into Alpha's animation slots.

No Commodore combat artwork is read here. Original RGBA references are retained;
the three opaque colours are losslessly indexed. Wide extensions are adapted to
the GBC actor budget while a selected anatomical strip stays at native scale.
"""
from inspect_engine import ROOT
from PIL import Image
import json,math
from functools import lru_cache

ART=ROOT/'terry_prototype/ngpc_combat_12'

@lru_cache(maxsize=1)
def catalog():return json.loads((ART/'catalog.json').read_text())

def mapping():
    c=catalog();m={}
    def p(case,i):return c['cases'][case]['unique'][i]
    def run(start,case,indices):
        for j,i in enumerate(indices):m[start+j]=p(case,i)
    # Use complete, compact native idle poses instead of squeezing the wide
    # outstretched hand. The original wide poses require a fifth OBJ column
    # and caused measured losses alongside another fighter and projectiles.
    # This deliberately reduces the breathing cycle, not the pixel anatomy.
    run(1,'idle',[2,2,3,3]);run(5,'crouch',[1]);run(6,'idle',[2,2])
    run(8,'walk_forward',[1,2,3,2,1,2,3,2,1,2]);run(18,'crouch',[1])
    run(19,'guard_reactions',[5,6,5,9,10,11])
    run(25,'jump',[1,2,2,2,1,2,1,2,2,2,2])
    run(36,'guard_reactions',[5,6,9,11]);run(40,'jump',[1,2,2,2,2,2])
    # Input-only replay of the original ROM identifies 46-50 as the round
    # introduction and 51-55 as Select's taunt. They are NOT hit reactions.
    # Reuse Terry's complete "come on" gesture for the intro/celebration;
    # the five taunt slots beckon twice, then retract into his stance.
    run(46,'taunt',[1,2,1,2]);run(50,'idle',[2])
    run(51,'taunt',[1,2,1,2]);run(55,'idle',[2])
    run(56,'taunt',[1,2,1,2,1,2,1,2,2])
    run(65,'standing_p_2',[1,1,2]);run(68,'standing_p_20',[3,4])
    run(70,'standing_k_2',[2,2,3]);run(73,'standing_k_20',[2,4,6,7,3])
    run(78,'crouching_p_2',[2,3]);run(80,'crouching_p_20',[3])
    run(81,'geyser_motion',[6,8]);run(83,'crouching_k_2',[2,3])
    run(85,'crouching_k_20',[3,5,4]);run(88,'crouch',[1])
    run(89,'jump',[2]);run(90,'jump_p_2',[3]);run(91,'jump',[2]);run(92,'jump_p_20',[3])
    run(93,'jump',[2]);run(94,'jump_k_2',[3]);run(95,'jump',[2]);run(96,'jump_k_20',[2,2,3])
    run(99,'jump',[2]);run(100,'jump_k_20',[3]);run(101,'jump_k_2',[3]);run(102,'jump',[1,2])
    run(104,'crouch',[1]);run(105,'guard_reactions',[9]);run(106,'crouching_k_20',[3,5])
    run(108,'guard_reactions',[5]);run(109,'standing_p_2',[1,2]);run(111,'crouch',[1])
    run(112,'jump',[2]);run(113,'jump_k_2',[3]);run(114,'hit_reactions',[13,15,16,17]);run(118,'idle',[2])
    run(119,'power_wave',[6,7,8]);run(122,'rising_tackle',[3,4,5,6]);run(126,'jump',[2])
    # 127 is the uppercut's landing, not the spinning kick's startup.
    # 132-135 are spin recovery; 136-139 are its repeating attack cycle.
    run(127,'crack_shoot',[14,6,7,8,9,13,13])
    run(134,'jump',[2,1]);run(136,'crack_shoot',[9,10,11,12])
    run(140,'power_wave',[6,7,8]);run(143,'cpu_geyser',[11,12,13,13,12,13,13,13,13])
    for target in range(143,152):m[target]+=':flip'
    # The double-QCB kick super charges in 147-151 then enters the spin.
    # Geyser art here made Terry kneel to punch the floor before spinning.
    run(147,'standing_k_20',[2,3,4,5,5]);run(152,'crack_shoot',[6])
    run(153,'power_wave',[6,7,8,9]);run(157,'jump',[2,2])
    run(159,'guard_reactions',[5]);run(160,'hit_reactions',[18,19,20,22,23,5,6,7,8,9,10,11,12,13,17])
    # Native knockdown phases replace Alpha's many character-specific thrown
    # poses. Rotation is only used where the receiving throw rotates a body.
    run(175,'hit_reactions',[6,7,8,9,10,11,12,13,14,6,7,8,9,10,13,14,16,17])
    for target in range(175,182):m[target]+=':180'
    run(193,'hit_reactions',[6,7,8,9,13,14,17,15,16,17,13,21,23])
    run(206,'cpu_geyser',[11,12])
    for target in (206,207):m[target]+=':flip'
    # The first knockdown reached the viewport edge. Prefer the complete
    # later frame and re-centered OAM captures, rather than clipped limbs.
    recovery={**{i:7 for i in range(6,13)},13:8,14:8,15:9,16:10,17:11,
              18:12,19:12,20:12,22:5,23:5}
    replacements={p('hit_reactions',i):p('hit_reactions_full',j) for i,j in recovery.items()}
    # Those crouching guard captures were also culled at the NGPC viewport
    # edge before extraction. The complete earlier guard retains the back.
    replacements.update({p('guard_reactions',i):p('guard_reactions',9) for i in (10,11)})
    for target,pid in list(m.items()):
        bits=pid.split(':');bits[0]=replacements.get(bits[0],bits[0]);m[target]=':'.join(bits)
    # New input-only captures keep the action away from either viewport edge.
    # Even the old "full" recoil and lying-down captures were pre-culled by
    # the NGPC game. These replacements include the cap, back and rear hand.
    better={p('hit_reactions_full',12):p('advance_reactions',5),
            p('hit_reactions_full',9):p('advance_reactions',8)}
    for target,pid in list(m.items()):
        bits=pid.split(':');bits[0]=better.get(bits[0],bits[0]);m[target]=':'.join(bits)
    # Preserve the launch -> airborne -> ground impact -> get-up sequence.
    # 166 is the initial recoiling launch, not a fully horizontal body.
    m[166]=p('advance_reactions',5)
    # The two grounded reactions used during repeated projectile hits must
    # leave room for the caster and effect. Use the complete native compact
    # recoil, with the head protected during conversion, for the first one.
    m[160]=p('hit_reactions_full',5)
    run(170,'advance_reactions',[8,8])
    run(172,'hit_reactions_full',[10])
    run(174,'hit_reactions_full',[8])
    # Ryu's counter has its own three preparation slots before sharing the
    # uppercut. A Power Wave cast here was the wrong visual action.
    run(119,'rising_tackle',[1,1,2])
    # Match Alpha's receiving-throw silhouette: inverted upright bodies,
    # then the landing and recovery phases, rather than sideways get-ups.
    run(175,'rising_tackle',[5,5,6,6,7,7,6])
    run(197,'advance_reactions',[5])
    run(198,'guard_reactions',[9,9])
    run(200,'hit_reactions_full',[5])
    run(201,'advance_reactions',[7,7])
    run(203,'rising_tackle',[5])
    run(204,'hit_reactions_full',[14,5])
    assert set(m)==set(range(1,208)),sorted(set(range(1,208))-set(m))
    return m

BODY_PALETTE=[0,0,0, 0,0,0, 255,0,0, 255,255,255]+[0]*756
FIRE_PALETTE=[0,0,0, 255,85,0, 255,255,0, 255,255,255]+[0]*756

def indexed(im,effect=False):
    im=im.convert('RGBA');out=Image.new('P',im.size);out.putpalette(FIRE_PALETTE if effect else BODY_PALETTE)
    colors=((255,85,0),(255,255,0),(255,255,255)) if effect else ((0,0,0),(255,0,0),(255,255,255))
    for y in range(im.height):
        for x in range(im.width):
            v=im.getpixel((x,y))
            if v[3]:
                i=min(range(3),key=lambda i:sum((v[j]-colors[i][j])**2 for j in range(3)))
                out.putpixel((x,y),i+1)
    return out

def record(pid):
    parts=pid.split(':');rec=dict(catalog()['poses'][parts[0]])
    im=indexed(Image.open(ART/'poses'/rec['file']));ox,oy=rec['offset']
    if len(parts)>1 and parts[1]=='flip':
        im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT);ox=-ox-im.width
    elif len(parts)>1:
        im=im.transpose(Image.Transpose.ROTATE_180);ox=-ox-im.width;oy=-oy-im.height-40
    rec.update(id=pid,_image=im,native_offset=(ox,oy),native=True,transform=parts[1] if len(parts)>1 else None)
    return rec

def compress_extension(im,ox,maxwidth,case=''):
    """Keep a central anatomical strip exact; compact only outlying columns.

    Transparent leading/trailing space is never used as a reason to rescale.
    This is an explicit adaptation, recorded per pose, not claimed pixel exact.
    """
    if im.width<=maxwidth:return im,ox,'native pixels'
    # Leave more room for long limbs instead of preserving a 24-column
    # torso at their expense. Follow the cap in upright attack/cast poses:
    # the world-space anchor is behind the head during a lean or kick.
    core=16 if im.width>=48 else 20 if im.width>40 else 24
    core=min(core,maxwidth-8)
    lo=max(0,min(im.width-core,-ox-core//2))
    if case.startswith(('standing_','crouching_','jump_','power_wave','cpu_geyser')) or (im.height>=32 and case.startswith(('hit_reactions','advance_reactions','central_reactions'))):
        cap=sorted(x for y in range(min(8,im.height)) for x in range(im.width) if im.getpixel((x,y))==2)
        if cap:lo=max(0,min(im.width-core,cap[len(cap)//2]-core//2))
    elif case.startswith('crack_shoot'):lo=(im.width-core)//2
    hi=lo+core
    remaining=maxwidth-core;left=lo;right=im.width-hi
    nl=round(remaining*left/(left+right))
    if left and right:nl=max(1,min(remaining-1,nl))
    nr=remaining-nl
    assert not left or nl
    assert not right or nr
    out=Image.new('P',(maxwidth,im.height));out.putpalette(im.getpalette())
    def shrink_strip(src,width,tip_at_right):
        # Every source column contributes to a destination bin. Build 09
        # copied only the terminal eight columns when width <= 8, deleting
        # the intervening arm, leg or back outright. Retain thin silhouettes
        # by choosing the most common OPAQUE index within each bin.
        if src.width<=width:return src
        result=Image.new('P',(width,src.height));result.putpalette(src.getpalette())
        for x in range(width):
            a=x*src.width//width;b=(x+1)*src.width//width
            for y in range(src.height):
                values=[src.getpixel((sx,y)) for sx in range(a,b)]
                opaque=[v for v in values if v]
                if opaque:
                    counts={v:opaque.count(v) for v in set(opaque)}
                    # Prefer the centre sample when equally frequent.
                    centre=values[len(values)//2]
                    result.putpixel((x,y),max(counts,key=lambda v:(counts[v],v==centre,-v)))
        return result
    if nl:out.paste(shrink_strip(im.crop((0,0,lo,im.height)),nl,False),(0,0))
    out.paste(im.crop((lo,0,hi,im.height)),(nl,0))
    if nr:out.paste(shrink_strip(im.crop((hi,0,im.width,im.height)),nr,True),(nl+core,0))
    return out,ox+lo-nl,f'{core}-column anatomical core retained; entire outer strips resampled with opaque coverage'

def width_budget(target):
    # The GBC limit is ten objects per scanline, not 32 pixels per actor.
    # Tight vertical packing and actual opaque-loss tests select the budget.
    # Neutral, intro and taunt retain complete native pixels. A 32-column
    # conversion visibly crushed the outstretched hand even standing alone.
    # Neutral uses the compact native poses; only the brief intro and taunt
    # need five-column rows. Overlap limits are checked separately.
    # Grounded normals can coincide with an earlier wave. A full 40-pixel
    # set preserved P1 but measurably clipped P2, so keep those compact.
    # Retraction/return, airborne attacks and the kick/uppercut specials have
    # a separately tested wider budget.
    if target in (160,164):return 32
    return 40 if native_neutral(target) or target in (76,77) or 89<=target<=107 or 114<=target<=117 or 122<=target<=126 or 128<=target<=152 or 160<=target<=205 else 32


def native_neutral(target):
    return target in (1,2,3,4,6,7,118) or 46<=target<=64

def body_image(rec,maxwidth=32):
    im=rec['_image'].copy();ox,oy=rec['native_offset']
    im,ox,adapt=compress_extension(im,ox,maxwidth,rec.get('first_case',''))
    rec['adaptation']=adapt
    # Ryu's decoded opaque foot baseline is -12 (not the OAM rectangle's
    # bottom). Preserve native relative offsets and share that ground plane.
    return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT),-(ox+im.width),oy-12

def effects():
    c=catalog();ids=c['effects']['power_wave_native']['unique'];result={}
    native=[indexed(Image.open(ART/'poses'/c['poses'][pid]['file']),True) for pid in ids]
    superids=c['effects']['cpu_geyser']['unique']
    for target in range(209,235):
        i=(target-209)%len(native);im=native[i].copy();is_super=217<=target<=227
        if is_super:
            # Genuine Power Geyser phases, recovered from CPU Terry's real
            # super. The source faces left; normalize it to the body inputs.
            j=(9,10,9,10,10,9,10,10,11,11,12)[target-217]
            pid=superids[j]
            im=indexed(Image.open(ART/'poses'/c['poses'][pid]['file']),True).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            height=(56,60,50,58,60,58,54,60,56,52,48)[target-217]
            im=im.resize((24,height),Image.Resampling.NEAREST)
            # Diagonal 24-pixel silhouette, with only two occupied columns
            # on each 16-line band. Both fighters retain their four columns.
            for y in range(height):
                for x in range(24):
                    if (y<32 and x<8) or (y>=32 and x>=16):im.putpixel((x,y),0)
        else:im=im.resize((16,min(24,im.height)),Image.Resampling.NEAREST)
        result[target]={'id':(pid if is_super else ids[i])+(':geyser' if is_super else ':wave'),'_image':im,'effect':True,
                        'native':True,'fixed_grid':True,'adaptation':'native flame adapted to two GBC sprite columns'}
    return result
