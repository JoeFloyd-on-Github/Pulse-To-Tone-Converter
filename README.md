# Pulse-to-Tone Converter (ATtiny85)

An internal **pulse-to-tone converter**. It sits inside a classic rotary
telephone and turns the dial's pulses (loop interruptions) into **DTMF
tones**, so the phone works on a modern tone-only line or VoIP adapter. It is
built around an **ATtiny85** on a small PCB, **BRD170127**.

> **Origin and credit.** The design comes from the open-source
> **[Pulse to Tone Converter](https://hackaday.io/project/28557-pulse-to-tone-converter)**
> by **LieBtrau** (Christoph Tack) on Hackaday.io and
> [GitHub](https://github.com/LieBtrau/pulse-dtmf-converter). This repository
> documents the kit built from it (rev R2), analyses it, and adds a
> redesigned board (rev V3).

## Board revisions

Each revision has its own parts list, firmware and build instructions. Use
the folder for the board you have.

| | **Rev R2**: the original kit board | **Rev V3**: the redesign |
|---|---|---|
| Folder | [`hardware_r2/`](hardware_r2/README.md) | [`hardware_v3/`](hardware_v3/README.md) |
| Board | LieBtrau's BRD170127/2 (EasyEDA): Gerbers, schematic, BOM, photos | KiCad 9, routed and DRC-clean, in the same outline with the jacks in the same places ([`hardware_v3/kicad`](hardware_v3/kicad/README.md)) |
| What's different | — | runs on loop currents down to about 1.5 mA (R2 needs about 6.5 mA); a PNP helper on each shunt regulator; no op-amp; optional CR1632 backup |
| Firmware source | upstream commit **`31ae4ba` (2019-07-06)**, Arduino IDE era ([`hardware_r2/firmware`](hardware_r2/firmware/README.md)) | upstream **`593e746` (2023)** plus V3 battery control ([`hardware_v3/firmware`](hardware_v3/firmware/README.md)) |
| Firmware image | `hardware_r2/firmware/images/ATTINY85V@SOIC8.hex` (production) | `hardware_v3/firmware/images/pulse-dtmf-converter-v3.hex` |
| Send delay after the last digit | 3 s | 1.2 s (configurable) |
| PB2 (ATtiny pin 7) | "mode" input, never wired on the board | coin-cell enable (BATT_EN) |
| Toolchain | Arduino IDE 1.8.13 + ATTinyCore 1.4.1 + Bounce2 2.55 | Arduino IDE 2 or arduino-cli + ATTinyCore 1.5.2 + Bounce2 2.71 |
| Fuses | L 0xFF, H 0xD5 (BOD 2.7 V), E 0xFF | the same |
| Programming | Arduino Uno as ISP, chip in a SOIC-8 ZIF adapter; or an XGecu programmer | the same Uno setup, in circuit with a SOIC-8 clip; or an XGecu programmer |
| Build docs | the toolchain guide + `KIT_build.doc` | [`hardware_v3/firmware/README.md`](hardware_v3/firmware/README.md) §3–5 + the KiCad fab files |
| Status | built and sold as a kit | designed and simulated; **not built yet** |

### About the firmware versions

Upstream's code changed after the R2 kits were made. The repo used to carry
upstream's **2023** source as if it were the kit firmware. It is not: the R2
production image was rebuilt from the **2019** source and matches it in size,
constants and RAM layout. The 2023 update moved the project from the Arduino
IDE to **PlatformIO**, shortened the send delay from 3 s to 1.2 s, and bounded
the digit buffer. The details are in
[`hardware_r2/firmware/README.md`](hardware_r2/firmware/README.md) §1 and §4.

## Also in this repo

| Path | Contents |
|---|---|
| [`ANALYSIS.md`](ANALYSIS.md) | engineering analysis of the original board and firmware: power, regulators, pulse decoding, DTMF generation, features |
| [`hardware_v3/spice`](hardware_v3/spice/README.md) | ngspice comparison of R2 and V3 |
| `third_party/` | **ATTinyCore** ([Spence Konde](https://github.com/SpenceKonde/ATTinyCore); a 1.4.2-dev snapshot; see its `LICENSE.md`) and **Bounce2** 2.55 ([Thomas Fredericks](https://github.com/thomasfredericks/Bounce2), MIT), as bundled with the R2 kit build |
| `WEB_SAVES/` | local copies of the upstream web pages and the ETSI DTMF specification, in case the sites go offline |

## License

- **Firmware:** both `hardware_r2/firmware` (upstream, verbatim) and
  `hardware_v3/firmware` (upstream plus the V3 changes) are **GPL v3**,
  © 2018 Christoph Tack. See the `LICENSE` file in each folder.
- **Bundled libraries** (ATTinyCore, Bounce2) keep their own licenses.
- The **documentation** (`ANALYSIS.md`, the READMEs, the SPICE and KiCad work)
  is this project's own. The boards derive from the upstream design; check the
  upstream project before redistributing hardware.
