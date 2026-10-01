"""A reversible Select-on-Ryu alternate, using independent ROM art and RAM flags.

All hooks are in the ROM. CBF8/CBF9 are fixed-WRAM variant bits, independent
for the two actors. The original fighter IDs and gameplay tables stay intact.
"""
from terry_geyser import Code

FAR=0x2560
BANK=130

def far(addr):return bytes.fromhex('cd6025')+addr.to_bytes(2,'little')

def actor_test(base):
    c=Code(base).emit('e5 7c fed2').jr(0x38,'actor')
    c.emit('fed5').jr(0x30,'no')
    c.emit('2e52 66')
    c.label('actor').emit('2e51 7e b7').jr(0x20,'no')
    c.emit('7c fec4').jr(0x28,'one')
    c.emit('fec6').jr(0x20,'no')
    c.emit('faf9cb').jr(0x18,'done')
    c.label('one').emit('faf8cb').jr(0x18,'done')
    c.label('no').emit('af')
    c.label('done').emit('b7 e1 c9')
    return c.finish()

def install(b,source,palette):
    patches=[]
    def patch(off,old,new):
        assert b[off:off+len(old)]==old,(hex(off),b[off:off+len(old)].hex(),old.hex())
        assert len(old)==len(new),(hex(off),len(old),len(new))
        b[off:off+len(new)]=new;patches.append(hex(off))
    def put(addr,data,bank=BANK):
        off=bank*0x4000+addr-0x4000
        assert b[off:off+len(data)]==b'\xff'*len(data),(hex(off),len(data))
        b[off:off+len(data)]=data;b[(bank+1)*0x4000-1]=bank

    # Relocate the existing select-screen name copier verbatim. Its local
    # branches are relative; VRAM/data addresses are unchanged.
    put(0x6000,source[0x255a:0x25ce])
    patch(0x255a,source[0x255a:0x25ce],far(0x6100)+b'\xc9'+b'\xff'*110)

    # Banked CALL with a two-byte inline address. Save all input registers,
    # amend the caller's return address, then restore them before dispatch.
    # The nested return trampoline also preserves all result registers/flags.
    c=Code(FAR).emit('f5 f5 f5 f5 c5 d5 e5')
    c.emit('f80c 4e 23 46 f806 71 23 70')
    c.emit('f80e 5e 23 56 1a 4f 13 1a 47 13 72 2b 73')
    c.emit('f808 71 23 70 23 36e6 23 363f 23 3600 23')
    c.emit('faff7f 77 3e82 ea5021 e1 d1 c1 f1 c9')
    entry=c.finish();assert len(entry)<=110
    patch(FAR,b'\xff'*len(entry),entry)
    ret=bytes.fromhex('f5 e5 f805 7e ea5021 f802 5e 23 56 23 73 23 72 e1 e802 f1 c9')
    # DE must also survive the return. Use BC-free two-byte copies via A,
    # with saved HL addressing the stack; no output register may be scratch.
    ret=bytes.fromhex('f5 e5 f805 7e ea5021 f802 7e 23 23 77 2b 7e 23 23 77 e1 e802 f1 c9')
    assert len(ret)<=26
    patch(0x3fe6,b'\xff'*len(ret),ret)
    put(0x4000,actor_test(0x4000))

    # Return table bank in A and table base in DE; H remains the actor page.
    c=Code(0x4100).emit('cd0040 f5 2e12 2a 56 5f f1').jr(0x28,'ryu')
    # Projectiles point into the fighter's table after the body entries;
    # translate that pointer, rather than resetting it to the table start.
    c.emit('7a c610 57 3e82 c9')
    c.label('ryu').emit('3e04 c9')
    put(0x4100,c.finish())
    lookup=far(0x4100)+bytes.fromhex('ea5021 2e15 6e 2600 7d 29 85 6f 3001 24 19 2a 5e 23 66 6b c9')
    assert len(lookup)<=29
    patch(0x18a1,source[0x18a1:0x18be],lookup+b'\x00'*(29-len(lookup)))

    # One clean reset on entry to a fresh character selection, not each round.
    c=Code(0x4200).emit('cd404d af eaf4cb eaf8cb eaf9cb 3e01 eaaacb c9')
    put(0x4200,c.finish())
    patch(0x24723,bytes.fromhex('3e01eaaacb'),far(0x4200))
    # Select edge on Ryu's actual grid box. Force the game's normal redraws.
    c=Code(0x4300).emit('fab4db b7').jr(0x20,'done')
    c.emit('fabecb e604').jr(0x28,'done')
    c.emit('fadcdb fec4 21f8cb').jr(0x28,'toggle')
    c.emit('23')
    c.label('toggle').emit('7e ee01 77 3eff eab3db eac9db')
    c.label('done').emit('fab4db 21004f c9')
    put(0x4300,c.finish())
    patch(0x24e99,bytes.fromhex('fab4db21004f'),far(0x4300)+b'\x00')

    # Body palette: keep original Ryu bytes and choose a separate palette
    # block in the same data bank, so both fighters can coexist in a match.
    put(0x6d00,palette,36)
    c=Code(0x4400).emit('e5 f0ec 67 cd0040 e1 11f961').jr(0x28,'done')
    c.emit('11006d').label('done').emit('c9')
    put(0x4400,c.finish())
    # A six-byte fixed wrapper uses the spare end of the lookup routine.
    # The full rewritten lookup uses all 29 bytes, so reuse a bank-9 cave
    # only for bank-9 hooks; this fixed stub lives in the relocated name gap.
    stub=FAR+len(entry)
    assert stub+6<=0x25ce
    patch(stub,b'\xff'*6,far(0x4400)+b'\xc9')
    patch(0x205e,bytes.fromhex('11f961'),b'\xcd'+stub.to_bytes(2,'little'))

    # The selected Manual/Auto label is drawn with objects using palette 1,
    # also used by the character preview. Terry's body palette makes its text
    # unreadable. Give only Terry's highlight an unused menu OBJ palette (6),
    # copied from original Ryu and uploaded in the existing VBlank callback.
    # Other characters, portrait BG palettes, and in-fight palettes are intact.
    put(0x6d00,source[0x921f9:0x92201])
    c=Code(0x4b00).emit('3e01 cd3a03 f5 c5 d5 e5 26c4 cd0040').jr(0x28,'done')
    c.emit('21006d 0606 cd6a02 3e06 cd5203')
    c.label('done').emit('e1 d1 c1 f1 c9')
    put(0x4b00,c.finish())
    patch(0x25001,bytes.fromhex('3e01cd3a03'),far(0x4b00))
    c=Code(0x4b40).emit('2c f5 e5 26c4 cd0040 e1').jr(0x28,'original')
    c.emit('7e e6f8 f606 77').jr(0x18,'done')
    c.label('original').emit('cbc6')
    c.label('done').emit('f1 2c c9')
    put(0x4b40,c.finish())
    menu_stub=stub+6
    assert menu_stub+6<=0x25ce
    patch(menu_stub,b'\xff'*6,far(0x4b40)+b'\xc9')
    patch(0x25073,bytes.fromhex('2ccbc62c'),b'\xcd'+menu_stub.to_bytes(2,'little')+b'\x00')

    # The selected 16x16 roster icon originally shares OBJ palette 2 with
    # the preview fighter's projectile. A delayed Terry preview refresh
    # overwrote it with flame colours. Menu palette 7 is independent of
    # both fighters (1-6) and the Manual/Auto highlight (6).
    # Choose the private palette only for the currently hovered Terry.
    # Leave every other fighter's original icon rendering unchanged.
    c=Code(0x4c00).emit('110040 19 e5 fadcdb 67 cd0040 e1 0602').jr(0x28,'done')
    c.emit('0607').label('done').emit('c9')
    put(0x4c00,c.finish())
    patch(0x24b6d,bytes.fromhex('110040190602'),far(0x4c00)+b'\x00')
    # Finish the second icon object, then give both halves the same palette.
    c=Code(0x4c40).emit('0c 0c 71 2c f5 e5 fadcdb 67 cd0040 e1 3e0a').jr(0x28,'write')
    # Only the selected Terry icon uses the HUD face in private OBJ tiles
    # B8/BA. Original grid resources end at B7 and remain byte-for-byte intact.
    c.emit('2d 36ba 2d 2d 2d 2d 36b8 2c 2c 2c 2c 2c 3e0f')
    c.label('write').emit('77 2d 2d 2d 2d 77 2c 2c 2c 2c f1 c9')
    put(0x4c40,c.finish())
    patch(0x24b50,bytes.fromhex('0c0c712c360ac9'),far(0x4c40)+b'\xc9\x00')
    # The menu queues only its changed icon palette, not all eight palettes.
    # Upload the matching private slot in that existing VBlank callback.
    c=Code(0x4c80).emit('3e02').jr(0x28,'done')
    c.emit('e5 fadcdb 67 cd0040 e1 3e02').jr(0x28,'load')
    # This callback runs in VBlank. Upload the HUD face with an opaque black
    # backdrop: zero/transparent pixels otherwise reveal Ryu's old BG icon.
    c.emit('cd004d 3e07').label('load').emit('cd5203')
    c.label('done').emit('c9')
    put(0x4c80,c.finish())
    patch(0x26cf,bytes.fromhex('3e02c45203'),far(0x4c80))
    put(0x6d20,palette[:8])
    c=Code(0x4d00).emit('c5 d5 e5 21206d 0607 cd6a02 e1 d1 c1 c9')
    put(0x4d00,c.finish())
    # Preload the private tiles while character-select initialization has
    # LCD disabled. Uploading tiles in the late palette callback corrupts
    # VRAM on SameBoy; that callback's timing budget is only for palettes.
    c=Code(0x4d40).emit('f5 c5 d5 e5 f04f f5 3e01 e04f')
    c.emit('21006e 11808b 0640 cddf00')
    c.emit('f1 e04f e1 d1 c1 f1 c9')
    put(0x4d40,c.finish())

    from terry_ui_art import make
    art=make()
    put(0x6e00,art['roster_face'])
    for addr,data in ((0x6800,art['portrait']),(0x6a30,art['attrs']),
                      (0x6a60,art['palettes']),(0x6a80,art['face']),
                      (0x6ac0,art['hud_name']),(0x6b00,art['name'])):put(addr,data)
    mirror=b''.join(art['attrs'][y*5:y*5+5][::-1] for y in range(7))
    put(0x6c80,mirror)

    # UI ownership is encoded in the destination's column, including the
    # pre-fight screen. Fixed WRAM works while the game's portrait WRAM bank
    # is selected. A = destination low byte; result is the Terry predicate.
    c=Code(0x4500).emit('e61f fe0a 26c4').jr(0x38,'test')
    c.emit('26c6').label('test').emit('c30040')
    put(0x4500,c.finish())

    # Replace only the portrait DMA source, leaving Ryu's cached art intact.
    # The original portrait consists of 35 row-major 8x8 tiles (40x56).
    c=Code(0x4600).emit('f3 c5 d5 e5 faefc2 cd0045 e1 d1 c1').jr(0x28,'dma')
    c.emit('110068')
    c.label('dma').emit('7b e052 7a e051 7c e053 7d e054 3e22 e055 c9')
    put(0x4600,c.finish())
    patch(0x25120,source[0x25120:0x25131],far(0x4600)+b'\x00'*12)

    # Matching per-tile palettes; retain the game's mirrored layout.
    c=Code(0x4700).emit('faefc2 cd0045').jr(0x28,'done')
    c.emit('21efc2 2a 56 5f 1a e620 47 21306a').jr(0x28,'map')
    c.emit('21806c')
    c.label('map').emit('0e07')
    c.label('row').emit('c5 0e05')
    c.label('cell').emit('2a f606 b0 12 13 0d').jr(0x20,'cell')
    c.emit('7b c61b 5f').jr(0x30,'nocarry')
    c.emit('14')
    c.label('nocarry').emit('c1 0d').jr(0x20,'row')
    c.emit('21606a 1140c2 0610 cddf00')
    c.label('done').emit('3e01 e070 3e00 c9')
    put(0x4700,c.finish())
    patch(0x2519d,source[0x2519d:0x251a3],far(0x4700)+b'\x00')

    # HUD faces/names get private VRAM copies after the original decompressor.
    # No shared ROM font bytes are touched (Manual/Auto depends on those).
    c=Code(0x4800).emit('26c4 cd0040').jr(0x28,'two')
    c.emit('21806a 11408c 0640 cddf00')
    c.label('two').emit('26c6 cd0040').jr(0x28,'done')
    c.emit('21806a 11008c 0640 cddf00')
    c.label('done').emit('3e00 e04f 3e01 e070 c9')
    put(0x4800,c.finish())
    patch(0xe36,source[0xe36:0xe3e],far(0x4800)+b'\x00'*3)

    # The HUD queues fighter names after loading its background resource.
    # Mark that queue once, then replace the names after the normal DMA flush.
    c=Code(0x4a00).emit('3e01 eaf4cb 0603 fa51c6 c9')
    put(0x4a00,c.finish())
    patch(0x2d700,bytes.fromhex('0603fa51c6'),far(0x4a00))
    c=Code(0x4a40).emit('3e6a e051 3ec0 e052 7a e053 7b e054 3e03 e055 c9')
    put(0x4a40,c.finish())
    c=Code(0x4900).emit('faf4cb b7').jr(0x28,'done')
    c.emit('af eaf4cb 26c4 cd0040').jr(0x28,'two')
    c.emit('11208f cd404a')
    c.label('two').emit('26c6 cd0040').jr(0x28,'done')
    c.emit('11e08e cd404a')
    c.label('done').emit('3e00 e04f 21e0c3 c9')
    put(0x4900,c.finish())
    patch(0x2d2ef,source[0x2d2ef:0x2d2f6],far(0x4900)+b'\x00'*2)

    # Character-select and versus name panels share the original copier.
    # Terry's 24 tiles occupy private bank-1 VRAM; Ryu uses the original path.
    c=Code(0x6100).emit('fab2db b7').jr(0x20,'original')
    c.emit('21d6db 2a 56 5f 7b cd0045').jr(0x28,'original')
    c.emit('3e01 e04f 3e6b e051 af e052 3e8d e053 af e054 3e17 e055')
    c.emit('af e04f 0603 3ed0')
    c.label('row').emit('0e08')
    c.label('cell').emit('12 f5 3e01 e04f 3e0b 12 af e04f f1 3c 13 0d').jr(0x20,'cell')
    c.emit('f5 7b c618 5f').jr(0x30,'nocarry')
    c.emit('14')
    c.label('nocarry').emit('f1 05').jr(0x20,'row')
    c.emit('af e0f9 c9')
    c.label('original').emit('c30060')
    put(0x6100,c.finish())
    return {'flags':['CBF8','CBF9'],'bank':BANK,'farcall':hex(FAR),'patches':patches,'far_entry_bytes':len(entry)}
