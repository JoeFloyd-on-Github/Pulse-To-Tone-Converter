# Pulse-to-Tone Converter, rev V3: V2 plus a CR1632 coin-cell backup

Rev V3 is the [rev-V2 low-loop-current circuit](../hardware_v2/README.md) with
an added **CR1632 coin cell** that can hold the ATtiny's supply (VDD) up while
the loop is open. It is the version that has been laid out.

| Folder | What it holds |
|---|---|
| [`kicad/`](kicad/README.md) | the KiCad 9 project: routed and DRC-clean, in the rev-R2 outline. Gerbers, BOM, pick-and-place and the **schematic PDF** are in `kicad/fab/`. |
| [`spice/`](spice/README.md) | the ngspice comparison of the original board, V2 and V3. Every number on this page comes from it. |

> **Rewritten 2026-11-18.** The earlier version of this page relied on a
> first-order Python model (`sim/`) and a hand-drawn `schematic.svg`. Both are
> removed: the SPICE simulation and the KiCad schematic replace them. The SPICE
> work changed four things the old page claimed:
> - the cell rarely carries anything;
> - a reservoir belongs on VDD, not the loop rail;
> - BATT_EN goes on PB2, not PB1;
> - both shunts need PNP helpers.

---

## 1. What the cell adds, and how much it is needed

SPICE dialed a "0" on six line types: POTS, a 25 mA ATA, a 15 mA weak ATA, and
10, 7 and 3 mA lines. In every case, V2's 470 µF reservoir keeps VDD at
**4.4 V or more**, which is above the cell's voltage. So the **cell never
supplies current during dialing**. It only takes over when VDD falls below
about 3 V. That happens when:
- the loop delivers less than about 1.5 mA, which is the V2 circuit's floor; or
- the loop opens for much longer than a dial break, with the MCU still meant to
  stay up.

The owner chose to **keep and populate the cell** (2026-11-18). A V2 is the
same board with the cell parts left off.

## 2. The cell circuit

The schematic is in `kicad/fab/BRD170127_V3_schematic.pdf`; the reference
designators below are from it.

```
  VCC ─ D5 BAT46WH ──────────────┬──► VDD ─ C1 470 µF ─ ATtiny85 (+ C4/C7)
                                 │
  BT1 CR1632 (+) ─ Q3 DMG2301L ─ D6 BAT46WH
         │           │ gate
         └─ R18 1M ──┴─── BATT_EN = PB2 (ATtiny pin 7)
```

- **Q3 (P-MOS, DMG2301L)** is the cell switch.
  - The MCU **arms** it by driving PB2 LOW.
  - R18 (1 MΩ, gate to BATT+) holds it **off** whenever the MCU is not driving
    the pin: at reset, at brown-out, and with no power.
- **D6** blocks reverse current, so the loop supply can never charge the
  primary cell. D5 and D6 form an OR: whichever source is higher feeds VDD.
- **BATT_EN has to be PB2.**
  - PB0 is the loop/pulse sense and PB1 is the DTMF PWM output (OC1A).
  - PB3/PB4 are the crystal and PB5 is RESET.
  - On the original board PB2 is the unconnected mode-select input, so V3
    firmware must stop reading it (see "Firmware").
- **Holder:** an off-board CR1632 holder with flying leads, soldered to BT1's
  two through-hole pads (+ is the square pad). The board has no room for a
  PCB-mount holder.

## 3. Firmware

[`../firmware/src/battery_control.ino`](../firmware/src/battery_control.ino)
holds the integration notes. **They have not been merged into the sketch yet.**
The changes needed:

- `pins.h`: add `PIN_BATT_EN = 2`. In `setup()`, remove the `PIN_MODE_SELECT`
  read and fix `mode = 1`. That was the original board's mode anyway, because
  PB2 was never connected.
- **Arm** the cell (PB2 LOW) once the MCU is up after off-hook.
- **Disarm on hang-up.** Once armed, the cell keeps the MCU alive through a
  hang-up, so the firmware has to detect it. Use the existing debounced loop
  sense (`rd.lineIsOpen()`, a one-line accessor added to `rotarydialer.h`):
  if the loop stays open for more than about 250 ms, set PB2 HIGH. A dial
  break is about 60 ms.
- Pick the threshold with the original firmware's behaviour in mind
  (`../ANALYSIS.md` §4). A hook-flash (about 100 ms) is already decoded as the
  digit "1", and the 150 ms digit timeout splits slow dials.

## 4. Simulated behaviour (SPICE)

Results from [`spice/`](spice/README.md):

| Case | Result |
|---|---|
| Dialing "0" on every line, fresh / mid-life / end-of-life cell | lowest VDD 4.39–4.48 V. **The cell supplies no current.** |
| Hang-up, firmware disarms 250 ms after the loop opens | VDD collapses; cell current 0.02 µA |
| Hang-up, firmware **never** disarms (fault) | MCU keeps running from the cell at **0.93 mA**: a 125 mAh CR1632 is flat in about 5 days |
| On-hook drain with Q3 off | 0.03 µA typical; about 1 µA if Q3 is at its worst-case leakage (about 11 years for 100 mAh) |
| Incoming ring while on-hook | the ring current powers the MCU (VDD about 4.7 V), so the firmware arms the cell and disarms it once ringing stops. The cell stays idle, because VDD is above its voltage. |

**The disarm logic is the only real risk the cell adds.** If it fails, the cell
goes flat in days.

## 5. Test points and bench checks

| TP | Net | On-hook | Off-hook, idle | While dialing |
|---|---|---|---|---|
| TP1 | VCC (upper shunt) | 0 V | about 5.0 V | collapses at each break |
| TP2 | VDD (MCU) | 0 V | about 4.67 V | stays at 4.4 V or more on any line of 3 mA or more |
| TP3 | BATT+ | cell voltage (about 3.0–3.2 V) | cell voltage | cell voltage |
| TP4 | BATT_EN (Q3 gate) | about BATT+ (off) | about 0 V (armed) | about 0 V (armed) |
| TP5 | CELL (Q3 drain / D6 anode) | about 0 V | about BATT+ | about BATT+ |
| TP6 | GND (circuit common) | — | — | — |

On the first board:
1. Scope **TP1** at 10, 25 and 40 mA. It should sit at about 5.0 V with no
   oscillation.
2. **Hang up and watch TP4.** It must return to BATT+ within about 250 ms,
   with TP5 falling to about 0 V. If TP4 stays at 0 V on-hook, the cell will
   drain in days: fix the firmware before fitting a cell.
3. Pull the cell and redial on the weakest line available. Dialing should be
   unaffected, which confirms what the simulation predicts.
4. The V2 checks also apply: DTMF level and twist, pulse detection on slow
   dials, Q2 temperature (`../hardware_v2/README.md` §6).

## 6. Bill of materials for the cell circuit

This is on top of V2. The full BOM is `kicad/fab/BRD170127_V3_bom.csv`.

| Ref | Part | Note |
|---|---|---|
| BT1 | CR1632 + off-board holder with wire leads | two through-hole pads |
| Q3 | DMG2301L-7 (P-MOS, SOT-23) | cell switch |
| D6 | BAT46WH (SOD-123) | reverse-charge block; the same part as D1–D5 |
| R18 | 1 MΩ, 0805 | Q3 gate pull-up to BATT+ |
| TP3–TP5 | test pads | BATT+, BATT_EN, CELL |

To build a V2, leave all of these off.
