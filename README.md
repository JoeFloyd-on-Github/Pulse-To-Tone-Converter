# Pulse-to-Tone Converter (ATtiny85)

An internal **pulse-to-tone converter** — it sits inside a classic rotary
telephone and converts the pulse (loop-disconnect) dialing of the rotary dial
into **DTMF tones**, so the phone can be used on a modern tone-only line. Built
around an **ATtiny85** on a small PCB (board **BRD170127**, rev R2).

> **Origin / credit.** This design originates from the open-source
> **[Pulse to Tone Converter](https://hackaday.io/project/28557-pulse-to-tone-converter)**
> project by **LieBtrau** on Hackaday.io (the schematic is marked "Drawn By:
> LieBtrau"). This repository is a build/working copy of that project, with an
> added engineering analysis; the original hardware and firmware are the
> original author's work and remain under their terms — see the upstream project
> for its license.

## What's in this repo

### Hardware
- `Gerber_BRD170127_R2.zip` — fabrication Gerbers for the PCB (rev R2).
- `Schematic_pluse_to_tone.JPG` — schematic.
- `PADS_ONLY.*` (`.svg`, `.png`, `.odg`, `.bmp`) — the solder/pad layout.
- `PCB_pads.JPG`, `BOM.JPG` — board and bill-of-materials images.
- `BOM_Pulse to DTMF Converter.xlsx` (and a later revision) — bill of materials.

### Firmware (ATtiny85)
- `pulse-dtmf-converter.ino_R0.hex` — compiled Arduino sketch (rev 0).
- `ATTINY85V@SOIC8.hex` / `.BIN` — flashable firmware image for the SOIC-8 part.

### Build documentation & photos
- `BRD170127_Pulse_To_Tone_Converter.doc` — build / design writeup.
- `KIT_build.doc` — kit assembly instructions.
- `20201219_*.jpg`, `20201229_*.jpg` — assembly, voltage-check and annotated
  build photos.

### Bundled third-party libraries (open source)
- `ATTinyCore-master/` (+ `.zip`) — the [ATTinyCore](https://github.com/SpenceKonde/ATTinyCore)
  Arduino core for the ATtiny85, by Spence Konde. See its own `LICENSE.md`.
- `Bounce2-master.zip` — the [Bounce2](https://github.com/thomasfredericks/Bounce2)
  switch-debounce library, by Thomas Fredericks (MIT).

These are included so the build is self-contained; they are the property of their
respective authors and carry their own licenses.

## Engineering analysis

See **[ANALYSIS.md](ANALYSIS.md)** for a full review of the design: how the board
is powered and why low-loop-current IP/VoIP phone systems starve it, why some
TLV431 regulators fail while others from the same batch work, the ATtiny firmware
behaviour and improvement ideas, and a feature comparison (speed dial, special
tones, redial) with other converters.

## Building

Flash the ATtiny85 with one of the provided `.hex` images (e.g. with an Arduino
as ISP), or rebuild from source using the ATtiny85 board definition from the
bundled ATTinyCore and the Bounce2 library. Then populate the PCB per the BOM and
`KIT_build.doc`.

## License

The design is derived from LieBtrau's
[Hackaday.io project 28557](https://hackaday.io/project/28557-pulse-to-tone-converter);
use is governed by that upstream project's license — check it before
redistributing the hardware or firmware. The bundled libraries (ATTinyCore,
Bounce2) keep their own original licenses.
