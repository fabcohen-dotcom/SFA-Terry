"""Scoped LR35902 hooks for Terry's stationary super eruption.

Code lives in a previously unused expansion bank. Fixed-bank trampolines return
to the original dispatcher. No firmware, emulator RAM patches or save edits.
"""
class Code:
    def __init__(self,base):self.base=base;self.b=bytearray();self.labels={};self.fix=[]
    def emit(self,h):self.b.extend(bytes.fromhex(h));return self
    def label(self,n):self.labels[n]=self.base+len(self.b);return self
    def jr(self,opcode,label):
        self.b.extend((opcode,0));self.fix.append((len(self.b)-1,label));return self
    def finish(self):
        for pos,label in self.fix:
            offset=self.labels[label]-(self.base+pos+1)
            assert -128<=offset<128,(label,offset)
            self.b[pos]=offset&255
        return bytes(self.b)

def is_terry_super(c,exit_label,variant=False):
    # HL is a projectile. +46 is the move type, +52 is the owner actor page.
    c.emit('2e46 7e fe03').jr(0x38,exit_label)
    c.emit('fe06').jr(0x30,exit_label)
    c.emit('e5 2e52 66 2e51 7e b7 e1').jr(0x20,exit_label)
    if variant:c.emit('cd0043').jr(0x28,exit_label)

def install(b,variant=False):
    def patch(off,old,new):
        assert b[off:off+len(old)]==old,(hex(off),b[off:off+len(old)].hex())
        assert len(old)==len(new);b[off:off+len(new)]=new
    def put(bank,addr,data):
        off=bank*0x4000+addr-0x4000
        assert b[off:off+len(data)]==b'\xff'*len(data)
        b[off:off+len(data)]=data;b[(bank+1)*0x4000-1]=bank

    # Preserve the original Power Wave adjustment. Only the super gets a
    # stationary velocity, ground-level origin and its own finite duration.
    c=Code(0x4000).emit('c5 d5 e5')
    if variant:
        from terry_variant import actor_test
        put(129,0x4300,actor_test(0x4300))
        c.emit('cd0043 3e15').jr(0x28,'height')
        c.emit('3e08').label('height').emit('cd241c')
    else:
        c.emit('e5 2e52 66 2e51 7e b7 3e15').jr(0x20,'height')
        c.emit('3e08').label('height').emit('e1 cd241c')
    is_terry_super(c,'init_done',variant)
    c.emit('2e18 af 22 77') # X velocity = 0
    c.emit('2e7e 3630') # private timer in the unused projectile +7E field
    c.emit('3ef8 cd241c') # undo Power Wave's +8 Y: erupt from the ground
    c.emit('2e26 7e b7 3e16').jr(0x20,'add_x')
    c.emit('3eea').label('add_x').emit('cd151c') # +22 facing right, -22 left
    c.label('init_done').emit('e1 d1 c1 c9')
    init=c.finish();put(129,0x4000,init)

    c=Code(0x4100).emit('f5 c5 d5 e5 f0ec 67')
    is_terry_super(c,'tick_done',variant)
    c.emit('2e2a 7e fe01').jr(0x20,'tick_done')
    c.emit('fa25cf b7').jr(0x20,'tick_done') # respect global hitstop
    c.emit('2e7e 7e b7').jr(0x28,'expire')
    c.emit('35').jr(0x20,'tick_done')
    c.label('expire').emit('2e2a 3602 2c af 22 77')
    c.label('tick_done').emit('e1 d1 c1 f1 f0ec 67 c9')
    tick=c.finish();put(129,0x4100,tick)

    # Called only from the projectile collision path, after the original
    # attack record was decoded. Change geometry, retaining damage/guard data.
    c=Code(0x4200).emit('f5 c5 d5 e5 f0ec 67')
    is_terry_super(c,'rect_done',variant)
    c.emit('af e0b4 3e1f e0b5 3e0b e0b6 3e1c e0b7')
    c.label('rect_done').emit('e1 d1 c1 f1 c9')
    rect=c.finish();put(129,0x4200,rect)

    init_stub=bytes.fromhex('3e81 ea5021 cd0040 3e07 ea5021 c9')
    tick_stub=bytes.fromhex('3e81 ea5021 cd0041 3e07 ea5021 c3e85d')
    rect_stub=bytes.fromhex('cd5c35 3e81 ea5021 cd0042 3e05 ea5021 c9')
    for off,data in ((0x3fb7,init_stub),(0x3fc5,tick_stub),(0x3fd5,rect_stub)):
        patch(off,b'\xff'*len(data),data)
    patch(0x1de66,bytes.fromhex('3e15cd241c'),bytes.fromhex('cdb73f0000'))
    patch(0x1dde5,bytes.fromhex('f0ec67'),bytes.fromhex('c3c53f'))
    patch(0x16ddb,bytes.fromhex('cd5c35'),bytes.fromhex('cdd53f'))
    return {'code_bank':129,'init_hex':init.hex(),'tick_hex':tick.hex(),
            'collision_hex':rect.hex(),'active_ticks':48,'additional_forward_offset':22,
            'hitbox':{'center_x':0,'center_y':31,'half_width':11,'half_height':28},
            'scope':('Owner character 0 with that player\'s Terry flag set, projectile types 3 through 5 only.' if variant else 'Owner character 0 (Terry), projectile types 3 through 5 only.')}

def art(effects):
    """Adapt the recovered four-colour indexed flames to a tall eruption."""
    from PIL import Image
    # The first frame must already read as a geyser: impact hitstop can hold
    # it for much of the move. Later frames flicker and taper at the tip.
    heights=(56,60,50,58,60,58,54,60,56,52,48)
    result={}
    for i,height in enumerate(heights):
        src=effects[6 if i%2==0 else 7]
        im=src.resize((24,height),Image.Resampling.NEAREST)
        # A diagonal plume can span 24 pixels overall while needing just two
        # sprite columns on each scanline. Keep the outer columns disjoint on
        # a 16-pixel grid, leaving capacity for both fighters underneath.
        for y in range(height):
            for x in range(24):
                if (y<32 and x<8) or (y>=32 and x>=16):im.putpixel((x,y),0)
        result[217+i]={'id':f'geyser_{i}','_image':im,'effect_width':24,'fixed_grid':True}
    return result
