# Firmware — original ATtiny source (GPL v3)

This is the **original pulse-to-DTMF firmware by Christoph Tack (LieBtrau)**,
included verbatim from the upstream project so this repository is self-contained.

- **Source:** <https://github.com/LieBtrau/pulse-dtmf-converter> ·
  project page <https://hackaday.io/project/28557-pulse-to-tone-converter>
- **Copyright © 2018 Christoph Tack**
- **License: GNU GPL v3** — see [`LICENSE`](LICENSE). The GPL permits
  redistribution provided the license and copyright notices are kept intact;
  they have not been modified.

## Contents

| File | What it is |
|---|---|
| `src/pulse-dtmf-converter.ino` | main sketch: reads pulse dialing, emits DTMF; two modes via PIN_MODE_SELECT (tone-per-digit vs whole-number) |
| `src/rotarydialer.cpp/.h` | rotary pulse decoding (Bounce2 + a one-shot timer) |
| `src/dtmfgenerator.cpp/.h` | DTMF by direct digital synthesis (phase accumulator + sine table, PWM) |
| `src/timer.*`, `src/singletimer.*` | timing helpers |
| `src/pins.h` | pin map (PIN_DTMF_OUT = PB0, PIN_MODE_SELECT = PB2) |
| `platformio.ini` | PlatformIO build (also usable from the Arduino IDE) |
| `src/battery_control.ino` | **our addition** — rev V3 coin-cell switch control (see below) |
| `UPSTREAM-README.md` | the upstream project's own README |

The compiled image `images/pulse-dtmf-converter.ino_R0.hex` is a
build of this source.

## Our addition and what it means for the license

`src/battery_control.ino` is **our** rev-V3 coin-cell backup control, written to
drop into this sketch. Because it is combined with GPL-v3 code, that addition —
and any build of the combined firmware — is likewise **GPL v3**. The hardware
design notes elsewhere in this repo (`ANALYSIS.md`, `hardware_v2/`,
`hardware_v3/`) are our own documentation of the board.

## Building

Open `platformio.ini` with PlatformIO, or load `src/` in the Arduino IDE with the
ATTinyCore board package (bundled at `../third_party/ATTinyCore-master`) and the Bounce2
library, target ATtiny85 @ 8 MHz external crystal, 2.7 V BOD enabled (see the
upstream README and `../hardware_v3/` for the rev-V3 wiring).
