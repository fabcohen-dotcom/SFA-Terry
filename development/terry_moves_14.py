"""Four Terry-only additions, using native SFA input/collision resolution.

The per-frame programs run in the cartridge, not in the test emulator. They
set animation records through the original decoder; guard, damage, hitstop,
recoil and interruption still belong to Alpha. Native MOTM captures provide
all body poses. Timing and geometry are explicit adaptations to Alpha/GBC.
"""
from inspect_engine import ROOT,SOURCE
from terry_geyser import Code
from terry_variant import far
from terry_native_art import indexed
from PIL import Image
import json
from collections import Counter

ART=ROOT/'terry_prototype/ngpc_moves_14'
CODE_BANK=130
COLLISION_BANK=132
GRAPHICS_BANK=133
NAMES=('Backspin Kick','Burn Knuckle','Power Dunk','Fire Kick')

def native_anchor(catalog,case,pid):
    # MOTM's OAM reflects the preceding 30 Hz simulation step, while the
    # captured actor coordinates already contain the new step. Undo that
    # two-video-frame displacement before deriving the pose's local origin.
    # Every observation of the chosen poses agrees after this correction.
    timeline=catalog['cases'][case]['timeline'];counts=Counter()
    for i,f in enumerate(timeline):
        if i>=2 and f['pose']==pid and f.get('origin') and timeline[i-2].get('origin'):
            counts[tuple(f['offset'][k]+f['origin'][k]-timeline[i-2]['origin'][k] for k in range(2))]+=1
    assert len(counts)==1,(case,pid,counts)
    return counts.most_common(1)[0][0]

class Asm(Code):
    def __init__(self,base):super().__init__(base);self.absolute=[]
    def jp(self,op,label):
        self.b.extend((op,0,0));self.absolute.append((len(self.b)-2,label));return self
    def finish(self):
        for pos,label in self.absolute:self.b[pos:pos+2]=self.labels[label].to_bytes(2,'little')
        return super().finish()

def active(c,fail):
    c.emit('7c fec4').jr(0x28,'actor_ok')
    c.emit('fec6').jp(0xc2,fail)
    c.label('actor_ok').emit('cd0040').jp(0xca,fail)
    c.emit('2e2a 2a fe01').jp(0xc2,fail)
    c.emit('2a b7').jp(0xc2,fail)
    c.emit('7e fe07').jp(0xc2,fail)
    c.emit('2eb3 7e fe08').jp(0xda,fail)
    c.emit('fe0c').jp(0xd2,fail)

def phases(catalog):
    """Pose index, duration, horizontal delta, height, attack profile.

    The frame numbers refer to contact sheets made by playing the owned NGP
    ROM. A callable height is evaluated within the phase (positive upwards).
    Distinct hit IDs prevent repeat damage during sustained active frames.
    """
    return [
      ('backspin_kick_20',[(6,3,0,0,0),(6,4,2,0,0),(7,3,1,0,0),(8,3,1,0,0),
          (9,7,0,0,0x60),(10,4,0,0,0),(11,4,1,0,0),(12,5,0,0,0)]),
      ('burn_knuckle_20',[(5,3,0,0,0),(6,6,0,0,0),(7,2,0,0,0),(8,3,0,0,0),
          (9,3,2,lambda i:2+i*2,0),(10,16,3,lambda i:max(0,8-(i//2)),0x61),
          (9,4,0,0,0),(8,8,0,0,0),(7,4,0,0,0)]),
      ('power_dunk_20',[(7,4,0,0,0),(8,4,1,lambda i:2+i*3,0),
          (9,7,2,lambda i:14+min(12,i*2),0x62),(10,4,1,26,0),
          (11,3,1,lambda i:26-i*2,0),(12,8,1,lambda i:max(0,20-i*3),0x63),
          (7,8,0,0,0),(6,4,0,0,0)]),
      ('fire_kick_20',[(6,6,1,0,0),(7,12,3,0,0x64),(8,6,0,0,0),
          (9,6,0,0,0),(2,4,0,0,0)]),
    ]

def install(b,source,tiles,metadata,encode,descriptor):
    catalog=json.loads((ART/'catalog.json').read_text());patches=[];regions=[]
    def put(bank,addr,data,blank=True):
        off=bank*0x4000+addr-0x4000
        if blank:assert b[off:off+len(data)]==b'\xff'*len(data),(bank,hex(addr),len(data))
        b[off:off+len(data)]=data;b[(bank+1)*0x4000-1]=bank
        regions.append({'bank':bank,'address':hex(addr),'length':len(data)})
    def patch(off,old,new):
        assert len(old)==len(new),(hex(off),len(old),len(new))
        assert b[off:off+len(old)]==old,(hex(off),b[off:off+len(old)].hex(),old.hex())
        b[off:off+len(new)]=new;patches.append(hex(off))

    # Preserve all Ryu collision data in a private copy. Only the attack
    # pointer is relocated; normal/reaction geometry retains original bytes.
    put(COLLISION_BANK,0x4000,source[22*0x4000:23*0x4000-1])
    orig_attack=source[22*0x4000+0x160:22*0x4000+0x160+0x600]
    put(COLLISION_BANK,0x7000,orig_attack,False)
    profiles={
      # id: native damage/reaction template, x,y,halfwidth,halfheight,hit id
      0x60:(0x10,-16,27,11,7,0x70), # sweep's knockdown, raised to spinning foot
      0x61:(0x25,-15,29,12,7,0x71), # tatsu-class special, one rushing hit
      0x62:(0x01,-8,21,8,10,0x72), # initial knee: light normal-class hit
      0x63:(0x10,-14,20,10,13,0x73),# downward fist knocks down
      0x64:(0x05,-18,9,12,6,0x74), # sliding kick, light normal-class hit
      0x65:(0x10,-11,31,9,18,0x75),# high follow-up knocks down
    }
    profile_report={}
    for ident,(original,x,y,w,h,hit_id) in profiles.items():
        off=22*0x4000+0x160+16*original
        raw=bytearray(source[off:off+16]);raw[:4]=bytes((x&255,y,w,h));raw[14]=hit_id
        # Keep sweep-class damage, but use the native tatsu's knockdown
        # reaction for these body/high attacks instead of its low-sweep tag.
        if ident in (0x60,0x63,0x65):raw[6]=0;raw[9]=7
        put(COLLISION_BANK,0x7000+16*ident,raw,False)
        profile_report[hex(ident)]={'template':hex(original),'bytes':raw.hex()}

    # Frame collision records use an unused, aligned tail of original bank
    # 31, the range accepted by the unmodified animation-record decoder.
    collision_records={};collision_next=0x7c20
    def collision(attack,low=False,air=False):
        nonlocal collision_next
        key=(attack,low,air)
        if key not in collision_records:
            hurt=(4,4,4) if air else (2,2,2) if low else (1,1,1)
            raw=bytes((*hurt,attack,3 if air else 2 if low else 1,0,1,0xbc,0,0,0,0,0,0,0,0 if attack else 255))
            assert collision_next+16<0x7fff
            put(31,collision_next,raw)
            collision_records[key]=bytes(((collision_next&255)|2,collision_next>>8))
            collision_next+=16
        return collision_records[key]

    graphic_base=130*0x4000+0x1000
    base_table=bytes(b[graphic_base:graphic_base+235*3])
    # Valid safe fallback entries also cover the renderer's one-frame handoff
    # from a custom move to an interrupted or ordinary Alpha action.
    fallback=base_table[3:6]*21
    put(130,0x52c1,fallback)
    art_stats=[];program_report=[]
    for move,(case,seq) in enumerate(phases(catalog)):
        tab=bytearray(base_table+fallback);pose_ids={};frames=[]
        def pose(case,index):
            pid=catalog['cases'][case]['unique'][index]
            if pid not in pose_ids:
                ident=235+len(pose_ids);assert ident<256
                rec=dict(catalog['poses'][pid]);im=indexed(Image.open(ART/'poses'/rec['file']))
                width=32 if move==0 and index in (5,6) else 40
                if (move,index)==(3,7):width=48
                anchor=native_anchor(catalog,case,pid)
                rec.update(id=pid,_image=im,native=True,native_offset=anchor,maxwidth=width,flexible_y_grid=True)
                bank,ptr,stat=encode(b,rec,descriptor(source,0,1),tiles,metadata)
                tab[ident*3:ident*3+3]=bytes((bank,))+ptr.to_bytes(2,'little')
                pose_ids[pid]=ident;stat.update(move=NAMES[move],frame_id=ident,native_anchor=anchor,reference_case=case)
                art_stats.append(stat)
            return pose_ids[pid]
        def append(case,seq):
            for index,n,dx,height,attack in seq:
                ident=pose(case,index)
                for tick in range(n):
                    y=height(tick) if callable(height) else height
                    flags=0
                    rec=bytes((dx&255,y,flags,1,0,ident))+collision(attack,low=move==3 and len(frames)<48,air=y>0)
                    assert len(rec)==8;frames.append(rec)
        append(case,seq)
        end=len(frames);frames.append(bytes((0,0,128,1,0,1))+collision(0))
        if move==3:
            while len(frames)<48:frames.append(frames[-1])
            append('fire_kick_hit',[(10,4,1,0,0),(11,4,0,0,0),(12,12,0,0,0x65),(13,6,0,0,0),(6,5,0,0,0)])
            frames.append(bytes((0,0,128,1,0,1))+collision(0))
        assert len(frames)<96
        put(130,0x7000+move*0x300,b''.join(frames))
        put(GRAPHICS_BANK,0x4000+move*0x400,tab)
        if move==0:
            # A travelling wave plus the opponent's wide recoil can use
            # seven scanline objects. Keep the ordinary knee at 32 pixels,
            # but supply a three-column knee while a projectile is active.
            compact=bytearray(tab);pid=catalog['cases'][case]['unique'][6]
            rec=dict(catalog['poses'][pid])
            rec.update(id=pid,_image=indexed(Image.open(ART/'poses'/rec['file'])),native=True,
                native_offset=native_anchor(catalog,case,pid),maxwidth=24,flexible_y_grid=True)
            bank,ptr,stat=encode(b,rec,descriptor(source,0,1),tiles,metadata)
            ident=pose_ids[pid];compact[ident*3:ident*3+3]=bytes((bank,))+ptr.to_bytes(2,'little')
            put(GRAPHICS_BANK,0x5000,compact)
            stat.update(move=NAMES[move],frame_id=ident,condition='projectile active',native_anchor=rec['native_offset'],reference_case=case)
            art_stats.append(stat)
        program_report.append({'name':NAMES[move],'normal_duration':end,'total_program_rows':len(frames),'poses':pose_ids})

    # Clone the original directional-history scanner without modifying its
    # global command table. Relative branches remain valid; absolute local
    # calls/jumps are relocated. New patterns: HCF+K and forward+K.
    scanner=bytearray(source[0x57de:0x5876]);delta=0x5b00-0x57de
    for at in range(len(scanner)-2):
        if scanner[at] in (0xc2,0xcd):
            address=int.from_bytes(scanner[at+1:at+3],'little')
            if address in (0x5867,0x586f):scanner[at+1:at+3]=(address+delta).to_bytes(2,'little')
    put(130,0x5b00,scanner);put(130,0x5bc0,bytes.fromhex('0120a0809010ff 0120ff'))
    put(130,0x5bd0,bytes((2,5,7,5))) # normal / tatsu / DP / tatsu meter gain

    # Input entry replaces nine whole bytes before the original super tests.
    # A clear Z flag consumes a custom command; Z means the original routine
    # continues. Original DP / fireball / tatsu / supers are otherwise intact.
    c=Asm(0x5400).emit('f0ec 67 cd0040').jp(0xca,'no')
    c.emit('2e2e 7e b7').jp(0xc2,'no')
    c.emit('3e02 cdad39').jr(0x30,'dunk')
    c.emit('3e09').jp(0xc3,'start')
    c.label('dunk').emit('3e05 cdad39').jr(0x30,'fire')
    c.emit('3e0a').jp(0xc3,'start')
    c.label('fire').emit('21c05b cd005b').jr(0x30,'backspin')
    c.emit('3e0b').jp(0xc3,'start')
    c.label('backspin').emit('f0d9 e603 fe01').jp(0xc2,'no')
    c.emit('f0ec 67 2e2b 7e b7').jp(0xc2,'no')
    c.emit('2c 7e fe03').jp(0xd2,'no')
    c.emit('21c75b cd005b').jp(0xd2,'no')
    c.emit('3e08')
    c.label('start').emit('f5 cd5529 c1').jp(0xca,'no')
    c.emit('2eb3 70 cd a830 cd d219')
    c.emit('cde71f 01000700 2e91 3601 2e5c 3600 2e16 36ff')
    c.emit('2eb3 7e fe08').jr(0x20,'graphics_ready')
    c.emit('fa00d2 47 fa00d3 b0 47 fa00d4 b0').jr(0x28,'graphics_ready')
    c.emit('2e5c 3601')
    c.label('graphics_ready')
    c.emit('2ec6 3600 2c 3670 2ed3 3684')
    c.emit('cd b31c cd bd1c 1e07 cdcc07')
    c.emit('e5 2eb3 7e d608 c6d0 6f 265b 5e 1600 e1 cd3b2d')
    c.emit('3e01 b7 c9')
    c.label('no').emit('f0ec 67 af c9')
    put(130,0x5400,c.finish())
    patch(0x30214,source[0x30214:0x3021d],far(0x5400)+bytes.fromhex('c0 3e14 00'))

    # Decoder-driven custom frame step. No change to the actor's animation
    # bank is needed: only our tick calls this frame decoder directly.
    c=Asm(0x5600).emit('f0ec 67');active(c,'original')
    c.emit('fa25cf b7').jp(0xc2,'handled')
    c.emit('2eb3 7e fe0b').jr(0x20,'row')
    c.emit('2e2d 7e fe12').jr(0x30,'row') # low hit confirms directly into follow-up
    c.emit('2e5c 7e b7').jr(0x28,'row')
    c.emit('3600 2e2d 3630') # only an unblocked hit unlocks the rising kick
    c.label('row').emit('2eb3 7e d608 47 87 80 c670 57 1e00')
    c.emit('2e2d 7e 34 6f 2600 29 29 29 19 54 5d')
    # DE = 8-byte row. The data's Y is a height above Alpha's ground +24.
    c.emit('f0ec 67 1a 47 13 1a 4f 13 1a 13 cb7f').jp(0xc2,'finish')
    c.emit('d5 c5 2e26 7e b7 78').jr(0x20,'forward')
    c.emit('2f 3c')
    c.label('forward').emit('cd151c c1')
    c.emit('2e23 af 22 79 c618 22 af 77 2e2e 79 b7 3e00').jr(0x28,'ground')
    c.emit('3e01')
    c.label('ground').emit('77 d1 cddc19 cd011a')
    c.label('handled').emit('3e01 b7 c9')
    c.label('finish').emit('cd7b1b 2e91 3600 2e16 36ff cd b31c cd bd1c cd b621')
    c.emit('3e01 b7 c9')
    c.label('original').emit('f0ec 67 2eb3 af 7e c9')
    put(130,0x5600,c.finish())
    patch(0x303b6,source[0x303b6:0x303bc],far(0x5600)+bytes.fromhex('c0'))

    # Flag a connected, unblocked Fire Kick through the normal collision
    # resolver. All displaced instructions and flags are preserved exactly.
    c=Asm(0x5900).emit('f5 c5 d5 e5')
    active(c,'hit_done')
    c.emit('2eb3 7e fe0b').jp(0xc2,'hit_done')
    c.emit('1eba 1a feff').jr(0x28,'hit_done')
    c.emit('2e5c 3601')
    c.label('hit_done').emit('e1 d1 c1 f1 f0cf e0be f0a7 c9')
    put(130,0x5900,c.finish())
    patch(0x16c55,source[0x16c55:0x16c5b],far(0x5900)+b'\x00')

    # Each custom move has a 256-entry graphics table, so animation IDs never
    # collide with the original 235 entries or other fighters/projectiles.
    c=Asm(0x4100).emit('cd0040').jp(0xca,'ryu')
    active(c,'standard')
    c.emit('2eb3 7e fe08').jr(0x20,'move_table')
    c.emit('2e5c 7e b7').jr(0x28,'move_table')
    c.emit('110050 3e85 c9')
    c.label('move_table').emit('2eb3 7e d608 87 87 c640 57 1e00 3e85 c9')
    c.label('standard').emit('2e12 2a 56 5f 7a c610 57 3e82 c9')
    c.label('ryu').emit('2e12 2a 56 5f 3e04 c9')
    data=c.finish();off=130*0x4000+0x100
    assert b[off:off+3]==bytes.fromhex('cd0040') and len(data)<0x100
    b[off:off+len(data)]=data
    return {'moves':program_report,'art':art_stats,'profiles':profile_report,'patches':patches,'regions':regions,
        'basis':'NGPC input-only native captures; Alpha-adapted timings and geometry; original collision/damage/guard engine',
        'commands':{'Backspin Kick':'forward + A','Burn Knuckle':'QCB + B','Power Dunk':'forward, down, down-forward + A','Fire Kick':'HCF + A'}}
