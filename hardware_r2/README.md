# BRD170127 rev R2: the original kit board

These are the design and build files for the **original board, rev R2**. The
silkscreen reads "BRD170127/2". It is the board the kit was sold on. The
design is LieBtrau's (Christoph Tack's) open-source
[Pulse to Tone Converter](https://hackaday.io/project/28557-pulse-to-tone-converter).

How it works and where it falls short are in [`../ANALYSIS.md`](../ANALYSIS.md).
The redesign is [`../hardware_v3`](../hardware_v3/README.md). It keeps R2's
49 × 34 mm outline and RJ11 jack positions, so it drops in where an R2 board
went.

**Firmware for this board** is in [`firmware/`](firmware/README.md):
- the 2019 upstream source that built the production image, and the images
  themselves;
- the Arduino IDE settings and fuses used, and both programming routes;
- a detailed look at the unused PB2 mode jumper.

## Files

| File | What it is |
|---|---|
| `Gerber_BRD170127_R2.zip` | fabrication Gerbers and drill files, exported from EasyEDA in July 2019 |
| `Schematic_pluse_to_tone.JPG` | the schematic (EasyEDA, "Drawn By: LieBtrau", rev 2.0) |
| `BOM.JPG`, `BOM_Pulse to DTMF Converter.xlsx` | the bill of materials, as an image and as a spreadsheet |
| `PADS_ONLY.svg/.png/.odg/.bmp`, `PADS_ONLY_BW.png`, `PCB_pads.JPG` | the pad layout, for hand assembly |
| `BRD170127_Pulse_To_Tone_Converter.doc` | **toolchain and programming guide**: the BOM with LCSC and Digi-Key numbers, Arduino-as-ISP setup, ATTinyCore and Bounce2, **burning the bootloader to set the fuses** (external 8 MHz crystal), then flashing the firmware |
| `KIT_build.doc` | **kit assembly guide**: an 18-step order, starting with the low-profile parts and ending with the RJ11 jacks and C1 |
| `photos/` | build photos (December 2020): assembly, the kit, annotated boards, and the off-hook **voltage measurement** quoted in `../ANALYSIS.md` §1 (`20201219_140931-voltages.jpg`) |

The libraries the build guide uses (ATTinyCore, Bounce2) are bundled in
`../third_party/`.

## Building an R2

1. Order the PCB from `Gerber_BRD170127_R2.zip` and the parts from the BOM.
2. Program the ATtiny85 **before** soldering it, as the kit did. Two routes,
   both in `firmware/README.md` §5:
   - an Arduino Uno as ISP with the chip in a SOIC-8 ZIF adapter;
   - an XGecu programmer writing `firmware/images/ATTINY85V@SOIC8.hex` with
     fuses L 0xFF, H 0xD5, E 0xFF.
3. Assemble the board in the order given in `KIT_build.doc`.

## Board facts

- 49 × 34 mm, 2 layers.
- SMD parts on top. The bottom is a GND (circuit-common) pour.
- Three 6P6C (RJ11) side-entry jacks:
  - CN1 (DTMF phone) and CN2 (FXS/line) on the left edge;
  - CN3 (rotary phone) on the right;
  - each with two 2.4 mm locating posts.
- C1 (470 µF) is through-hole, at the top right.
- **Circuit summary:**
  - a BAT46WH bridge feeding two TLV431 shunt regulators (U2 at about 4.6 V,
    U3 also acting as the DTMF modulator);
  - an ATtiny85V at 8 MHz on a crystal;
  - an MCP6022 active filter driving Q1.

  The full netlist was extracted from the upstream EasyEDA PCB export and is
  simulated in [`../hardware_v3/spice`](../hardware_v3/spice/README.md)
  (`conv_orig.sub`).
