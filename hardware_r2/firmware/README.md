# Rev R2 firmware: what is on the shipped boards

This folder holds the firmware for the **original R2 kit board**: the source
that built it, the images actually programmed, the toolchain and fuse settings
used, and a detailed look at the PB2 "mode" jumper.

| Path | What it is |
|---|---|
| `pulse-dtmf-converter/` | the sketch, **verbatim from upstream commit [`31ae4ba`](https://github.com/LieBtrau/pulse-dtmf-converter/tree/31ae4bae4a58e38fca52afa2c1105259ea064210/Firmware/pulse-dtmf-converter) (2019-07-06)**: the last version before upstream moved to PlatformIO. It is an Arduino sketch folder; open `pulse-dtmf-converter.ino`. |
| `images/ATTINY85V@SOIC8.hex`, `.BIN` | **the production image** (2,418 bytes of code), saved by the XGecu programmer: the 8 KB flash plus the 512 B EEPROM, which is blank. A copy of the same flash image is on the share as `pulse-dtmf-converter.ino.hex`. |
| `images/pulse-dtmf-converter.ino_R0.hex` | an **earlier test build** (2,482 bytes, 2020-12-18), built from an older, single-mode version. Not for production. |
| `LICENSE` | GPL v3, the upstream license (© 2018 Christoph Tack) |

---

## 1. Which source built these images

**The boards were not built from the 2023 source that the repo used to carry
in `firmware/src`.** That was cloned from upstream GitHub for the analysis on
2026-11-18. Upstream's code had changed after these boards were built (§4), and
the share folder `PULSE-TO-TONE` holds only compiled images, no source. The
evidence for the source actually used:

| Evidence | Production image (`ATTINY85V@SOIC8`) | `R0` test image |
|---|---|---|
| "Send the number" delay compiled in | `millis() + 3000` (the `subi 0x48 / sbci 0xF4 …` sequence): **3 s**, as in the 2018–2019 sources. The 2023 source uses 1,200 ms. | not present |
| RAM cleared at start-up (`.bss` size) | **256 bytes**, which includes the 2018–2019 sketch's **200-byte** `pulsesBuffer` (2023: 15 bytes) | **41 bytes**: no digit buffer at all |
| Toolchain screenshot in `../BRD170127_Pulse_To_Tone_Converter.doc` (29 Dec 2020) | the open sketch is the 2019 file: `#include` lines first, then `const int modePin`, `int mode`, `const bool REVERSE_DIAL_MODE` | — |

**Rebuild test (2026-11-18).** Each upstream 2018–2019 revision was built with
arduino-cli, using the R2 menu settings (§5), Arduino's avr-gcc
7.3.0-atmel3.6.1, and Bounce2 2.55:

| Source | ATTinyCore | Code size | Bytes matching production |
|---|---|---|---|
| `bdddf8e` / `2704130` (2018–2019) | 1.4.2-dev | 2,532 | 13 % |
| `392846b` (2019-07-05, no gap between gathered digits) | 1.4.2-dev | 2,396 | 26 % |
| `31ae4ba` (2019-07-06) | 1.4.2-dev (the zip in `third_party/`) | 2,412 | 50 % |
| **`31ae4ba`** | **1.4.1** (the Boards Manager release) | **2,418: exactly production's size** | **85 %** |

**Conclusion:**
- The production image was built from **`31ae4ba`**, the source in this
  folder, with the **ATTinyCore 1.4.1** release. Bounce2 2.55 to 2.60 all give
  the same result.
- It therefore **includes** `31ae4ba`'s fix: an 80 ms gap between gathered
  digits.
- The remaining 15 % of bytes are scattered register and ordering differences,
  not missing code. That is consistent with building in Arduino IDE 1.8.13 on
  Windows instead of arduino-cli on Linux.
- Rebuilding this folder with ATTinyCore 1.4.1 gives the same firmware.
- The `R0` image is from an **older single-mode version**, upstream's
  early-2018 code. That version sends each digit as soon as it is dialed and
  has no mode pin.

## 2. How R2 units behave (2019 source, production image)

- **Pins:**
  - PB0 (pin 5): loop/pulse sense;
  - PB1 (pin 6): DTMF PWM;
  - PB3/PB4: 8 MHz crystal;
  - PB5: RESET;
  - PB2 (pin 7): **mode pin**, read once at power-up (§3).
- **Pulse decoding:** 10 ms debounce; a digit ends 150 ms after the start of
  its last pulse.
- **Mode 1, the default and in practice the only mode** (§3): digits go into a
  200-byte buffer with no bounds check (harmless on the ATtiny85, which has
  512 B of RAM). **3 s after the last digit**, the whole number is sent as
  80 ms tones with 80 ms gaps.
- Everything else (tone generation, idle sleep, timing) is as described in
  `../../ANALYSIS.md` §4. That analysis was written from the 2023 source; the
  only differences that affect R2 units are the 3 s delay and the buffer.

## 3. The PB2 "mode jumper", in depth

### Where it came from

The R2 board (2017–2018) was designed for a firmware that **sent each digit as
soon as it was dialed**. LieBtrau's Hackaday log describes a DECT base that
would not accept that: "you form the number first, then pick up", so the base
wants the whole number at once.

On **2018-05-19**, Felix Mueller contributed upstream pull request #1, "Dual
mode: tone after each digit (original) – gather all digits then send tones".
It read **ATtiny pin 7 (PB2)** with the internal pull-up:

| Pin 7 at power-up | Mode | Behaviour |
|---|---|---|
| open (pull-up → HIGH) | **1: gather** (default) | collect digits, send the whole number 3 s after the last one |
| tied to GND | 0: per digit | send each digit's tone about 150 ms after its last pulse, like a tone phone |

Upstream kept this through 2019. The 2023 refactor moved it to `pins.h`
(`PIN_MODE_SELECT = 2`).

### Why it was hardly ever used

- **The board has no jumper.** In the upstream netlist, U1 pin 7 is **not
  connected**: no pad, no trace, no via. The feature was added in firmware
  after the PCB already existed.
- **Using it takes a bodge wire** from pin 7 to GND (pin 4, at the opposite
  corner of the SOIC). That has to be done inside the phone.
- **The wire would also block reprogramming.** Pin 7 is the ISP **SCK** line,
  so the wire would have to come off before reflashing.
- **It is read only at power-up.** Each off-hook powers the board, so a switch
  would take effect on the next call. That is fine, but it adds nothing.
- **Mode 1 suits everything this kit was used with:**
  - exchanges, ATAs and PBXs accept a burst of digits;
  - DECT and cordless bases need it.

  Mode 0 is only better for **interactive menus**: "press 1 for…" needs a 3 s
  wait per choice in mode 1. Even there, mode 1 still works.

**So every R2 unit runs mode 1, and the feature went unused**, as you
suspected. Its real legacy is that it kept PB2 reserved in software while the
hardware never used it.

### How the pin was repurposed in V3

Every other ATtiny85 pin is taken: PB0 sense, PB1 PWM, PB3/PB4 crystal,
PB5 reset. So PB2 is the **only free pin**, and rev V3 uses it as **BATT_EN**,
the coin-cell switch. The V3 firmware stops reading PB2 and fixes the mode in
code. Mode 0 is still available as a compile-time constant. See
`../../hardware_v3/firmware/README.md`.

## 4. How upstream changed after these boards were built

| Date | Commit | Change | Affects R2 units? |
|---|---|---|---|
| 2018-01 to 03 | `1fdbe62`…`12459f4` | DDS generator, rotary decoder, ATtiny85 port, "tested on the FXS port", BRD170127 R1 | the `R0` test image is from this era |
| 2018-05-19 | `bdddf8e` / PR #1 | dual mode + **PB2 mode pin**, 3 s gather delay, 200-entry buffer | yes: production |
| 2019-06-30 | `2704130` | `REVERSE_DIAL_MODE` (for New Zealand) compile option | yes (off) |
| 2019-07-05 | `392846b` | the rotary decoder returns a pulse count; the sketch maps it to a digit | yes |
| 2019-07-06 | `31ae4ba` | fix: tones "stringed together" (an 80 ms gap between gathered digits) | **yes: the source in this folder** |
| 2023-02-20 | `590decb`, `9a72751`, `593e746` | **move to PlatformIO**; buffer cut to 15 with a bounds check ("it overflowed the amount of RAM" on an ATtiny45); gather delay turned into a constant and **shortened to 1,200 ms**; pins moved to `pins.h`; GPL headers added | **no.** R2 units never received this. V3's firmware starts from it. |

**The toolchain change is the biggest one:**

| | 2018–2019 (and these R2 boards) | 2023 upstream |
|---|---|---|
| Build system | **Arduino IDE 1.8.x** with **ATTinyCore** by Spence Konde. Upstream also kept a QtCreator project. | **PlatformIO** (`platform = atmelavr`, `framework = arduino`) |
| Board | ATTinyCore "ATtiny25/45/85 (No bootloader)", chip ATtiny85, **8 MHz external** | `board = attiny45`. PlatformIO's default for that board is **not** the 8 MHz crystal setting. |
| Libraries | Bounce2 installed by hand (here: 2.55, bundled in `../../third_party/`) | `lib_deps = Bounce2 @ ^2.71` |
| Fuses | written by the IDE's **Burn Bootloader** from the menu choices (§5) | not covered. PlatformIO needs `board_fuses.*` set and `pio run -t fuses`, which upstream doesn't configure. |
| Status | tested on hardware | upstream's own note: "build succeeds, but not tested onto the target" |
| Upstream's recorded menu choice | `clock=8external, bod=disable` (QtCreator build file) | — |

Upstream's own build file records **BOD disabled**. The R2 boards were
programmed with **BOD 2.7 V**. That matches the fix LieBtrau describes in the
Hackaday log for unreliable start-up on VoIP lines.

## 5. Toolchain and fuses actually used for R2

This is from the screenshots in `../BRD170127_Pulse_To_Tone_Converter.doc`
(Windows, 29 Dec 2020).

**Software:**
- Arduino IDE **1.8.13**;
- ATTinyCore **1.4.1**, from the Boards Manager. The rebuild test in §1 points
  to this release; the `ATTinyCore-master` zip in `../../third_party/` is a
  later 1.4.2-dev snapshot that produces slightly different code;
- Bounce2 **2.55** (bundled).

**Tools menu:**

| Setting | Value |
|---|---|
| Board | ATtiny25/45/85 (No bootloader) |
| Chip | ATtiny85 |
| Clock | **8 MHz (external)** |
| B.O.D. Level | **B.O.D. Enabled (2.7 V)** |
| Save EEPROM | EEPROM retained |
| Timer 1 Clock | CPU (CPU frequency) |
| LTO | Enabled |
| millis()/micros() | Enabled |
| Programmer | Arduino as ISP (ATTinyCore) |

**Resulting fuses.** These are identical to the XGecu programmer's
configuration screenshot.

| Fuse | Value | Meaning |
|---|---|---|
| Low | **0xFF** | external crystal, 8 MHz or more (CKSEL = 1111); slowly-rising-supply start-up (SUT = 11: 16K clocks + 64 ms, which suits the slow ramp through the 470 µF); no ÷8; no clock output |
| High | **0xD5** | BODLEVEL = 101 (**2.7 V brown-out**), EESAVE on, SPI programming on, RESET pin kept, debugWIRE off, watchdog not forced |
| Extended | **0xFF** | self-programming off |
| Lock | 0xFF | no lock |

**Programming routes used:**
1. **Arduino Uno as ISP**, with the chip in a SOIC-8 ZIF adapter on a
   breadboard and a 10 µF capacitor from the Uno's RESET to GND. The wiring is
   the same as for V3: see `../../hardware_v3/firmware/README.md` §5, which
   has a diagram. Run "Burn Bootloader" first; it only writes the fuses. Then
   use **Sketch → Upload Using Programmer**.
2. **XGecu programmer** with the chip in its ZIF socket, writing
   `images/ATTINY85V@SOIC8.hex` with fuses L 0xFF, H 0xD5, E 0xFF, Lock 0xFF.
   This is the quickest way to make more R2 parts.

**After the fuses are set, the chip needs a crystal to run or to be programmed
again.** On the R2 board that is X1, but a bare chip in a socket has none. The
guide therefore warns that an 8 MHz crystal must be on pins 2–3.
