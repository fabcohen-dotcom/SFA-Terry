# Development implementation references

These are the actual Python modules used for the Terry hack, preserved with
their bank addresses, assembly emitters, artwork mappings and comments.

Use `../build_patch.py` for the supported, self-contained v1.0 release build.
This historical pipeline needs intermediate builds and locally extracted art
catalogs which are not distributed. See `../docs/SOURCE.md` for the distinction.

- `terry_variant.py`: Select toggle, per-player variant flags and graphics hooks.
- `terry_moves_14.py`: additional move input handling and assembly.
- `terry_geyser.py`: flame/super behavior and machine-code emitter.
- `terry_native_art.py`, `terry_art_15.py`, `terry_ui_art.py`: artwork mappings.
- `sfa_sprite_codec.py`, `build_terry.py`: sprite decode/packing and base build.
- `build_terry_15.py`, `build_terry_16.py`, `refine_layouts_16.py`: full/compact
  art selection and lossless sprite layouts.
- `build_terry_17.py`, `build_terry_18.py`: native-style directional throws.
- `build_terry_19.py`: crouching diagonal kick input correction.
- `build_terry_21.py`: the final rolling recovery art/alignment correction.

Prototype 20 was rejected and is intentionally not part of the release chain.
