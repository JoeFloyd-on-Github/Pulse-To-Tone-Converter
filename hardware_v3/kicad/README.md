# BRD170127 rev V3: KiCad design and manufacturing files

This is a routed, DRC-clean, 2-layer board in the rev-R2 outline (49 × 34 mm).
The three RJ11 jacks are in the same places as on R2, so V3 is a drop-in
replacement. The circuit is the one simulated in [`../spice`](../spice).

**Open in KiCad 9:** `BRD170127_V3.kicad_pro`. The project-local libraries are
`BRD170127.pretty` (the RJ11 footprint copied from the R2 board, and the
cell-lead pads) and `BRD170127.kicad_sym` (TLV431 with the onsemi SOT-23 pinout).

## Status

| Check | Result |
|---|---|
| DRC (`kicad-cli pcb drc --severity-all`) | **0 violations, 0 unconnected** |
| Schematic parity | **0 issues** |
| ERC | no electrical errors. The only warnings are that kicad-cli has no global symbol-library table on this machine; the symbols are embedded in the schematic. |
| R2 hole compatibility | all 18 jack pins and 6 locating posts match the R2 drill file to within 0.02 mm. C1 sits 0.3 mm higher, to clear the rotary jack's body. |

## Ordering (`fab/`)

| File | Use |
|---|---|
| `BRD170127_V3_gerbers.zip` | upload to the PCB fab: 2 layers, 1.6 mm, HASL or ENIG, any colour |
| `BRD170127_V3_bom_jlc.csv`, `BRD170127_V3_cpl_jlc.csv` | JLCPCB-style assembly files for the 41 top-side SMD parts |
| `BRD170127_V3_bom.csv` | the full BOM, including the hand-soldered parts |
| `BRD170127_V3_schematic.pdf` | the schematic |
| `BRD170127_V3_assembly.pdf` | every reference designator. 14 labels did not fit on the silkscreen of this dense board and appear only here. |
| `render_top.png`, `render_bottom.png` | 3-D renders |

Design rules: tracks at least 0.2 mm (0.5 mm on the line, VCC, VEE and GND
nets), clearance 0.2 mm, vias 0.6/0.3 mm (0.8/0.4 mm on line nets), GND pour
on both layers. Any standard 2-layer service can make it.

**Before you order:**
- **Fill in the LCSC numbers.** They are known for the parts reused from R2:
  BAT46WH C127989, TLV431A C56765, BC856B C181144, ATtiny85V C152192 and the
  8 MHz crystal C108703. The 0805 passives, BCX53-16 (Q2/Q4) and DMG2301L (Q3)
  have only an MPN or value. Pick stock parts at order time.
- In the fab's assembly preview, check the rotation of the SOT-23/SOT-89/SOIC
  parts. KiCad and JLCPCB sometimes disagree on the zero orientation.
- **Hand-soldered parts:** the three RJ11 jacks (mounted as on R2), the
  470 µF / 6.3 V radial C1 (8 mm diameter, 3.5 mm pitch), and the CR1632 holder
  on flying leads to the BT1 pads (+ is the square pad).

## Circuit changes from the original (rev R2)

| Area | Original | V3 | Why |
|---|---|---|---|
| Upper shunt | TLV431 alone, 4.59 V, plus a 1k bleeder | TLV431 U2 + BCX53 Q2 (R15 470, R16 220, C12 1n), 5.0 V (R1 100k / R6 33k), 22k bleeder R17 | each TLV431 only biases its PNP; R17 still pulls VCC down quickly so pulse breaks are detected |
| Lower shunt / line modulator | TLV431 U3 carries the whole loop current | U3 + BCX53 Q4 (R19 470, R20 220), R5 47k | the original runs U3 at 25–40 mA against a 15 mA rating |
| DTMF filter | MCP6022: 4th-order active filter + V-to-I | passive 2-pole RC (R12/R13/C8, R10/C9) into Q1 (R2 39k emitter resistor) | removes 2 mA of standing current |
| Reservoir | 470 µF behind D5 | same | the simulation shows it rides through dialing down to about 1.5 mA of loop current |
| Coin cell | none | CR1632 → Q3 (DMG2301L) → D6 → VDD; gate pull-up R18 1M; BATT_EN = **PB2 (pin 7)** | kept at the owner's request; the simulation shows it is rarely needed |
| Test points | none | TP1 VCC, TP2 VDD, TP3 BATT+, TP4 BATT_EN, TP5 CELL, TP6 GND | for bench verification (see `../spice/README.md`) |
| Passive parts | 1206 | 0805 | the extra parts have to fit the same area |

**Firmware:** BATT_EN is on **PB2**, the only free pin: PB1 is the DTMF PWM
output (OC1A), and the crystal uses PB3/PB4. The V3 firmware, its tools and
fuses, and the in-circuit programming (Arduino as ISP with a SOIC-8 clip on U1)
are in [`../firmware`](../firmware/README.md).

## Regenerating

Everything is built from `design.py`, which defines the parts, nets and
placement:

```sh
python3 gen_sch.py          # schematic (net-label style; symbols flattened and embedded)
python3 gen_pcb.py          # placed, unrouted board + project/library tables
python3 route.py            # import route/board.ses, widen neck-downs, refill pours, place labels
python3 make_fab.py         # DRC + parity + ERC, then everything in fab/
```

To route from scratch instead of reusing `route/board.ses`:

```sh
FREEROUTING_JAR=/path/to/freerouting-2.5.0.jar python3 route.py --autoroute
```

Freerouting is run headless with analytics disabled and Java's network access
pointed at a dead proxy.

If you edit the board by hand in KiCad, stop using the generators: they
overwrite the `.kicad_pcb` and `.kicad_sch` files.
