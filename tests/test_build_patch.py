import json
from pathlib import Path
import tempfile
import unittest
from build_patch import assemble,make_ips,apply_ips,sha256

class PatchTests(unittest.TestCase):
    def test_literals_runs_and_expansion(self):
        base=bytes(range(128));target=bytearray(base+b'\xff'*65536)
        target[8:12]=b'four';target[40:70]=b'X'*30;target[-16:]=b'z'*16
        self.assertEqual(apply_ips(base,make_ips(base,bytes(target))),bytes(target))

    def test_truncated_and_out_of_bounds_input(self):
        for patch in (b'BAD',b'PATCH',b'PATCH\0\0\0\0\x03a',b'PATCH\0\0\0\0\0',b'PATCH\x40\0\0\0\x01aEOF'):
            with self.assertRaises(ValueError):apply_ips(b'',patch)

    def test_source_reconstruction_and_hash_guards(self):
        base=b'original';target=b'origXnal'+b'\xff'*8
        manifest={'source_bytes':len(base),'source_sha256':sha256(base),'target_bytes':len(target),
                  'expansion_fill':255,'target_sha256':sha256(target),'data_files':['bank.json']}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);path=root/'bank.json'
            path.write_text(json.dumps({'bank':0,'segments':[{'offset':'0x4','hex':['58']}]}))
            self.assertEqual(assemble(base,manifest,root),target)
            with self.assertRaises(ValueError):assemble(b'wrongrom',manifest,root)
            path.write_text(json.dumps({'bank':0,'segments':[{'offset':'0x4','hex':['59']}]}))
            with self.assertRaises(ValueError):assemble(base,manifest,root)

    def test_overlapping_segments_rejected(self):
        base=b'original';manifest={'source_bytes':8,'source_sha256':sha256(base),'target_bytes':8,
            'expansion_fill':255,'target_sha256':sha256(base),'data_files':['bank.json']}
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'bank.json').write_text(json.dumps({'bank':0,'segments':[
                {'offset':'0x4','hex':['58']},{'offset':'0x4','hex':['58']}]}))
            with self.assertRaises(ValueError):assemble(base,manifest,root)

if __name__=='__main__':unittest.main()
