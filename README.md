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

| Folder | Contents |
|---|---|
| [`hardware_r2/`](hardware_r2/README.md) | the **original kit board, rev R2** (silk-screened BRD170127/2): Gerbers, schematic, BOM, pad layout, the toolchain/programming guide, the kit assembly guide, and build photos |
| [`hardware_v2/`](hardware_v2/README.md) | the low-loop-current redesign (write-up only; built on the V3 board without the coin cell) |
| [`hardware_v3/`](hardware_v3/README.md) | V2 plus a CR1632 backup: the ngspice simulation (`spice/`) and the routed KiCad 9 board (`kicad/`) |
| [`firmware/`](firmware/README.md) | the **original source** by Christoph Tack (LieBtrau), verbatim from the [upstream GitHub repo](https://github.com/LieBtrau/pulse-dtmf-converter) under **GPL v3**, plus our rev-V3 `battery_control.ino` notes. Compiled images are in `firmware/images/`. |
| `third_party/` | **ATTinyCore** (the [Arduino core for the ATtiny85](https://github.com/SpenceKonde/ATTinyCore), by Spence Konde; see its `LICENSE.md`) and **Bounce2** (the [debounce library](https://github.com/thomasfredericks/Bounce2), by Thomas Fredericks, MIT). Bundled so the build is self-contained. |
| `WEB_SAVES/` | local copies of the upstream web pages and the ETSI DTMF spec, in case the sites go offline |
| [`ANALYSIS.md`](ANALYSIS.md) | the engineering analysis of the original board and firmware |

## Rev V3: simulation and PCB

- **[hardware_v3/spice](hardware_v3/spice/README.md)** is an ngspice comparison of
  the original board and rev V3: loop-current budget, part spread, pulse dialing
  on six line types, DTMF level and spectrum, hang-up and ringing.
- **[hardware_v3/kicad](hardware_v3/kicad/README.md)** is the KiCad 9 project for
  rev V3, routed and DRC-clean, in the R2 outline. Gerbers, BOM and
  pick-and-place files are in `hardware_v3/kicad/fab/`.

## Engineering analysis

See **[ANALYSIS.md](ANALYSIS.md)** for a full review of the design: how the board
is powered and why low-loop-current IP/VoIP phone systems starve it, why some
TLV431 regulators fail while others from the same batch work, the ATtiny firmware
behaviour and improvement ideas, and a feature comparison (speed dial, special
tones, redial) with other converters.

## Building

Flash the ATtiny85 with one of the `.hex` images in `firmware/images/` (for
example with an Arduino as ISP), or rebuild from source using the ATtiny85
board definition from the bundled ATTinyCore (`third_party/`) and the Bounce2
library. The steps, including the fuse setting, are in
`hardware_r2/BRD170127_Pulse_To_Tone_Converter.doc`. Then populate the R2 PCB
following its BOM and `hardware_r2/KIT_build.doc`.

## License

The design originates from Christoph Tack's (LieBtrau)
[Hackaday.io project 28557](https://hackaday.io/project/28557-pulse-to-tone-converter)
/ [GitHub repo](https://github.com/LieBtrau/pulse-dtmf-converter).

- **Firmware** in [`firmware/`](firmware) — and any build combined with it,
  including our `battery_control.ino` addition — is **GPL v3** (© 2018 Christoph
  Tack); see [`firmware/LICENSE`](firmware/LICENSE).
- **Bundled libraries** (ATTinyCore, Bounce2) keep their own original licenses.
- The **hardware-design notes** here (`ANALYSIS.md`, `hardware_v2/`,
  `hardware_v3/`, and the R2 kit documentation in `hardware_r2/`) are this project's own documentation; the board itself derives
  from the upstream design — check the upstream project before redistributing
  hardware.
