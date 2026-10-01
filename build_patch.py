"""Deterministically build the v1.0 IPS from the versioned patch change data.

Requires the user's clean USA SFA ROM. No network, emulator or proprietary SDK.
The original game is an external input, not source included in this project.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def assemble(base: bytes, manifest: dict, data_root: Path) -> bytes:
    if len(base) != manifest['source_bytes'] or sha256(base) != manifest['source_sha256']:
        raise ValueError('Wrong base ROM: use the clean Street Fighter Alpha USA version documented in README.md.')
    size = manifest['target_bytes']
    if not len(base) <= size <= 0x400000:
        raise ValueError('Invalid target size.')
    output = bytearray(base + bytes([manifest['expansion_fill']]) * (size-len(base)))
    last_end = 0
    for name in manifest['data_files']:
        path = (data_root / name).resolve()
        if not path.is_relative_to(data_root.resolve()):
            raise ValueError('Patch data path escapes its source directory.')
        bank = json.loads(path.read_text(encoding='utf-8'))
        for segment in bank['segments']:
            offset = int(segment['offset'], 16)
            payload = bytes.fromhex(''.join(segment['hex']))
            end = offset + len(payload)
            if not payload or offset < last_end or end > size:
                raise ValueError('Overlapping, out-of-order or out-of-bounds patch segment.')
            if offset // 0x4000 != bank['bank'] or (end-1) // 0x4000 != bank['bank']:
                raise ValueError('Patch segment does not belong to its stated ROM bank.')
            output[offset:end] = payload
            last_end = end
    if sha256(output) != manifest['target_sha256']:
        raise ValueError('Output hash mismatch: patch source is modified or incomplete.')
    return bytes(output)

def make_ips(base: bytes, target: bytes) -> bytes:
    if len(base) > len(target) or len(target) > 0x400000:
        raise ValueError('This patch builder supports expansion up to 4 MiB only.')
    patch = bytearray(b'PATCH')
    def record(offset: int, payload: bytes) -> None:
        if not 0 < len(payload) <= 65535 or offset == 0x454f46:
            raise ValueError('Invalid IPS record.')
        patch.extend(offset.to_bytes(3, 'big'))
        if len(payload) > 3 and len(set(payload)) == 1:
            patch.extend(b'\0\0' + len(payload).to_bytes(2, 'big') + payload[:1])
        else:
            patch.extend(len(payload).to_bytes(2, 'big') + payload)
    pos = 0
    while pos < len(base):
        if base[pos] == target[pos]:
            pos += 1
            continue
        start = pos
        while pos < len(base) and base[pos] != target[pos] and pos-start < 65535:
            pos += 1
        record(start, target[start:pos])
    for pos in range(len(base), len(target), 0x4000):
        record(pos, target[pos:pos+0x4000])
    patch.extend(b'EOF')
    return bytes(patch)

def apply_ips(base: bytes, patch: bytes) -> bytes:
    if not patch.startswith(b'PATCH'):
        raise ValueError('Invalid IPS header.')
    data = bytearray(base)
    pos = 5
    while True:
        if pos+3 > len(patch):
            raise ValueError('Truncated IPS file.')
        if patch[pos:pos+3] == b'EOF':
            if pos+3 != len(patch):
                raise ValueError('Unexpected trailing IPS data.')
            return bytes(data)
        if pos+5 > len(patch):
            raise ValueError('Truncated IPS record.')
        offset = int.from_bytes(patch[pos:pos+3], 'big')
        size = int.from_bytes(patch[pos+3:pos+5], 'big')
        pos += 5
        if size:
            payload = patch[pos:pos+size]
            if len(payload) != size:
                raise ValueError('Truncated IPS payload.')
            pos += size
        else:
            if pos+3 > len(patch):
                raise ValueError('Truncated IPS run-length record.')
            size = int.from_bytes(patch[pos:pos+2], 'big')
            if not size:
                raise ValueError('Empty IPS run-length record.')
            payload = patch[pos+2:pos+3]*size
            pos += 3
        if offset+size > 0x400000:
            raise ValueError('IPS record exceeds this project\'s 4 MiB limit.')
        if len(data) < offset+size:
            data.extend(b'\0'*(offset+size-len(data)))
        data[offset:offset+size] = payload

def write_new_or_identical(path: Path, data: bytes) -> None:
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'Refusing to overwrite different existing file: {path.name}')
    path.write_bytes(data)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True, help='Your clean SFA USA ROM')
    parser.add_argument('--out-dir', type=Path, default=ROOT/'dist')
    parser.add_argument('--write-rom', action='store_true', help='Also write the patched ROM locally')
    args = parser.parse_args()
    manifest = json.loads((ROOT/'patch/manifest.json').read_text(encoding='utf-8'))
    base = args.base.read_bytes()
    target = assemble(base, manifest, ROOT/'patch')
    patch = make_ips(base, target)
    if sha256(patch) != manifest['ips_sha256'] or apply_ips(base, patch) != target:
        raise ValueError('IPS verification failed.')
    args.out_dir.mkdir(parents=True, exist_ok=True)
    name = manifest['output_name']
    if args.base.resolve() == (args.out_dir/(name+'.gbc')).resolve():
        raise ValueError('Output must not overwrite the input ROM.')
    write_new_or_identical(args.out_dir/(name+'.ips'), patch)
    if args.write_rom:
        write_new_or_identical(args.out_dir/(name+'.gbc'), target)
    sums = f'{sha256(patch)}  {name}.ips\n{sha256(target)}  {name}.gbc (generated locally only)\n'
    write_new_or_identical(args.out_dir/'SHA256SUMS.txt', sums.encode('ascii'))
    print(f'Built and verified {name}.ips ({len(patch):,} bytes)')
    print(f'IPS SHA256: {sha256(patch)}')
    print(f'ROM SHA256: {sha256(target)}')

if __name__ == '__main__':
    main()
