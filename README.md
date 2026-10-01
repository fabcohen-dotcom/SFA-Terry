# SFA Terry v1.0

Play as **Terry Bogard in Street Fighter Alpha for Game Boy Color**.
An unofficial fan ROM hack with NGPC-derived artwork and adapted Terry moves,
while retaining the original Ryu. Runs as a normal 4 MiB GBC game; no custom
firmware is required.

**[Download v1.0](https://github.com/fabcohen-dotcom/SFA-Terry/releases/tag/v1.0)**
— get `SFA_Terry_v1.0_PATCH_ONLY.zip` for the IPS, instructions and checksums,
or the standalone `SFA_Terry_v1.0.ips`. No ROM is included.

It is an Alpha adaptation, not a port of the complete NGPC game.

## Install

Use your clean **Street Fighter Alpha - Warriors' Dreams (USA)** ROM:

- Size: 1,048,576 bytes.
- CRC32: `AA5F14D2`.
- SHA-256: `5393db89f3763c973438d8a6abd4ff83c404fe6cd58a8041adf2cd6d85535835`.

Apply `SFA_Terry_v1.0.ips` once using an IPS-compatible patcher, save the result as a new `.gbc` file, and launch it fresh. The output is 4,194,304 bytes, SHA-256 `48ed0d15c6e4bc324a9ad7496e1c11ca45007af888a06a5337206096084e5dfb`.

## Select Terry

Highlight **Ryu**, press **Select** to toggle Terry, then confirm normally. Select again restores Ryu. The earlier Akuma/Dan/M. Bison selector is included; no separate hidden-character patch is required.

## Controls and move list

**B = punch; A = kick.** Directions below assume Terry faces right; mirror them when facing left. Forward is towards the opponent and back is away. QCF means down, down-forward, forward; QCB means down, down-back, back; DP means forward, down, down-forward; HCF means back, down-back, down, down-forward, forward.

| Action | Input |
|---|---|
| Normal punches/kicks | B / A; use down for crouching, or jump for air attacks. Original Alpha tap/hold strengths apply to normals. |
| Crouching kick | Down or down-forward + A. |
| Forward/back throw | Close to a grounded, throwable opponent: forward or back + B. Short taps work. |
| Backspin Kick | Standing forward + A. |
| Power Wave | QCF + B. |
| Rising Tackle | DP + B; this adaptation does not use the NGPC charge command. |
| Crack Shoot | QCB + A. |
| Burn Knuckle | QCB + B. |
| Power Dunk | DP + A. |
| Fire Kick | HCF + A. An unblocked slide hit enables the rising follow-up. |
| Power Geyser | QCF, QCF + B, with super meter. |
| Inherited spinning kick super | QCB, QCB + A, with super meter. This is an Alpha-derived extra, not High Angle Geyser. |
| Alpha Counter | While blocking with at least one level: back, down-back, down + B. |
| Taunt | Select during a fight. |

## Build the patch from this repository

Python 3.10+ is sufficient; there are no additional packages to install.
Supply your clean base ROM as documented above:

```sh
python build_patch.py --base "/path/to/Street Fighter Alpha USA.gbc"
```

This reconstructs and verifies `dist/SFA_Terry_v1.0.ips` from the versioned
patch data. Add `--write-rom` to generate the patched `.gbc` locally as well.
The base ROM is never modified. Output directories, ROMs, patches and saves are
ignored by Git. Read [source layout](docs/SOURCE.md) before editing the hack.

Run the builder's integrity tests with:

```sh
python -m unittest discover -s tests -v
```


## Credits and feedback

Street Fighter Alpha and its characters belong to Capcom; Terry and the source
Match of the Millennium artwork belong to SNK. Developed with assistance from
OpenAI Codex. Not an official Capcom, SNK or ModRetro release. See [NOTICE](NOTICE.md).

For bug reports, include the release version, emulator/core or hardware,
opponent, facing, input and a short recording if possible. Start from a fresh
boot, not a savestate from another build. Do not attach ROM files to issues.
