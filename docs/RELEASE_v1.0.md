# SFA Terry v1.0

First named release of the Terry Bogard ROM hack for Street Fighter Alpha GBC.
Byte-identical to the tested Prototype 21, including the corrected rolling recovery.

Highlight Ryu and press **Select** to choose Terry. Original Ryu remains available.
Includes NGPC-derived combat/UI artwork, adapted Terry specials and Power Geyser,
directional throws, Alpha Counter, and the earlier hidden-character selector.

## Download and apply

Use **SFA_Terry_v1.0_PATCH_ONLY.zip** for the IPS, README and checksums, or download
**SFA_Terry_v1.0.ips** directly. Apply it once to your clean USA base ROM:

- Base size: 1,048,576 bytes.
- Base CRC32: `AA5F14D2`.
- Base SHA256: `5393db89f3763c973438d8a6abd4ff83c404fe6cd58a8041adf2cd6d85535835`.
- Patched output: 4,194,304 bytes; SHA256 `48ed0d15c6e4bc324a9ad7496e1c11ca45007af888a06a5337206096084e5dfb`.
- IPS SHA256: `237bfe9b78569f917222f2a2ff104b6d42687ba81bcdcd5554647124b879a21f`.

Do not apply this cumulative IPS on top of another hack or earlier prototype.
Launch fresh; do not load savestates made with another build.

The repository README contains the complete move list, credits, known limitations
and validation details. Both facings and SameBoy were checked for the recovery
fix; the final correction still needs physical-device confirmation.

Only a patch and its source/tooling are published. No complete ROM is included.
