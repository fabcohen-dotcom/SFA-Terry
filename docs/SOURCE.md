# Source layout

`build_patch.py` and `patch/` are the portable, deterministic source for the
released IPS. Python 3.10 or newer and your clean USA base ROM are sufficient.
The build needs no earlier prototype, extracted PNG, emulator state or private
directory. Its output must match the documented ROM and IPS hashes.

The patch data is hexadecimal replacement data grouped by 16 KiB ROM bank.
Offsets are absolute file offsets. Only differing bytes from the original
1 MiB region are stored; expansion to 4 MiB starts with `FF`, followed by the
listed replacement segments. This includes the patch's game-specific graphics
and assembled machine code. It is not a decompilation of either original game.

`development/` preserves the actual Python implementation used to develop the
character: sprite conversion/packing, move handlers, selection and rendering
hooks, and the later throw, command-input and recovery fixes. These files are
engineering references, not the portable build entry point: the historical
pipeline refers to private source-ROM dumps, extraction catalogs and earlier
builds which are deliberately not bundled. The release builder instead uses
the final checked change data, so those historical dependencies are unnecessary.

To alter behavior, use the development code and comments to understand the
affected bank/address, then update the corresponding patch data and manifest
hashes for a new version. Do not treat changing a hash as a substitute for
gameplay testing. The v1.0 hashes identify the exact tested release.

The repository intentionally excludes complete ROMs, saves, emulator binaries,
source-game image dumps, personal filesystem paths, account credentials and
recordings. Generated files belong in ignored `dist/`. Release assets contain
the IPS and instructions; a complete patched ROM is never published here.
