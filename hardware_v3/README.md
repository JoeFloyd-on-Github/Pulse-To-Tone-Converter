# BRD170127 rev V3: the low-loop-current redesign, with an optional CR1632 backup

Rev V3 redesigns the R2 kit board ([`../hardware_r2`](../hardware_r2/README.md))
so it works on **IP/VoIP ports (ATAs) with little loop current**. It also adds
an **optional CR1632 coin cell**. It keeps R2's 49 × 34 mm outline and RJ11
positions, so it drops in where an R2 board went.

| Folder | What it holds |
|---|---|
| [`firmware/`](firmware/README.md) | the V3 firmware, including the battery control; tools, fuse settings, Arduino-as-ISP wiring and step-by-step programming |
| [`kicad/`](kicad/README.md) | the KiCad 9 project: routed and DRC-clean. Gerbers, BOM, pick-and-place and the **schematic PDF** are in `kicad/fab/`. |
| [`spice/`](spice/README.md) | the ngspice comparison of R2 and V3. Every performance number on this page comes from it. |

> **History.** The design started as two steps: "V2", the supply/DTMF
> redesign, and "V3", V2 plus the cell. The only difference between them was
> the cell parts, so V2 has been folded into this page (§5). Earlier drafts
> (a Python ride-through model, a hand-drawn schematic, "direct drive" with
> the reservoir on the loop rail, BATT_EN on PB1) were removed in favour of
> the SPICE results and the KiCad design.

---

## 1. What R2 already had (upstream's fixes)

LieBtrau's Hackaday log records the first breadboard failing on an internet
gateway's FXS port ("runs in bursts", digits not dialed). Upstream fixed that
before the R2 kits, and V3 keeps every fix:

| Problem (upstream log) | Upstream fix | In V3 |
|---|---|---|
| unreliable start-up: VCC ramps slowly through the 470 µF, and BOD was off | **2.7 V brown-out detector** | the same fuse, H 0xD5 (`firmware/README.md` §4) |
| VCC sagging to 3.08 V with the MCU always active | **IDLE sleep** between timer ticks (3.57 V afterwards) | `sleepNow()` kept |
| DTMF too weak | R5 raised to 39k | R5 is now 47k (re-centred modulator, §2) |
| a DECT base wants the whole number | "gather" mode | `SEND_MODE = 1` |

## 2. What changed from R2, and why

SPICE of the R2 netlist (`spice/`) shows three remaining problems:
- R2 needs **at least 6.5 mA** of loop current. On a 7 mA line, VDD drops to
  2.25 V while dialing.
- **U3 carries the whole loop current** (25–40 mA) against its 15 mA rating.
- The DTMF waveform **clips**.

| Block | R2 | V3 | Why |
|---|---|---|---|
| Upper shunt | TLV431 U2 alone, 4.59 V | U2 drives a **BCX53 PNP, Q2** (R15 470 Ω, R16 220 Ω, C12 1 nF); R1 100k / R6 33k → **5.0 V** | the PNP carries the excess current. With 470 Ω, a TL431 fitted by mistake still works. |
| Bleeder | R4 **1 kΩ** (4.6 mA) | R17 **22 kΩ** | still pulls VCC down fast at each break, so PB0 sees every pulse |
| Lower shunt / modulator | TLV431 U3 alone | U3 drives a **BCX53 PNP, Q4** (R19 470 Ω, R20 220 Ω), C11 10 nF; **R5 47k** | U3 runs at about 1.6 mA instead of the full loop current |
| DTMF path | MCP6022 4th-order active filter + Q1 (R2 15k) | **passive 2-pole RC** (R12 10k / R13 160k / C8 4.7 nF, then R10 10k / C9 4.7 nF) into **Q1 as an emitter follower**, R2 **39k** | removes the op-amp's 2 mA. Q1's emitter resistor makes the voltage-to-current converter without it. |
| Reservoir | C1 470 µF on VDD, behind D5 | unchanged | a reservoir on VCC would hide the pulse breaks from PB0 |
| Coin cell | — | optional: BT1 → Q3 → D6 → VDD, gate on PB2 (§4) | backup for very weak lines |
| Passive parts | 1206 | 0805 | to fit the extra parts in the same area |
| Test points | — | TP1–TP6 | bench checks (§6) |

**How the tone gets onto the line without an op-amp:** PB1 carries the
DDS PWM (31.25 kHz; duty = high tone + ¾ × low tone). The RC filter turns it
into the tone pair. Q1's emitter follows its base, so its current is
(VDD − V_base − 0.65 V)/R2. That current goes into U3's REF node and moves the
lower shunt's voltage, which is the converter's own voltage drop. The values
centre that current at about 53 µA during a tone, with ±48 µA of swing.

## 3. Simulated performance

| | R2 | V3 |
|---|---|---|
| Lowest loop current keeping VDD above the 2.7 V BOD | 6.5 mA | **1.5 mA** |
| Converter drop at 20 mA, idle | 6.4 V | 8.1 V (the price of the PNP helpers) |
| TLV431 U3 current at 25 / 40 mA loop | 24.9 / 39.9 mA | **1.6 / 1.7 mA** |
| Dialing "0", lowest VDD: POTS / 25 mA ATA / 15 mA weak ATA | 3.80 / 3.78 / 3.77 V | 4.48 V on all three |
| Dialing "0", lowest VDD: 10 / 7 / 3 mA lines | 3.43 / **2.25** / **0.67 V** | 4.48 / 4.48 / 4.39 V |
| Pulses detected (10 sent), every line | 10/10 | 10/10 |
| DTMF into 600 Ω, low / high tone | about −7 / −6 dBm, clipped | about −8.6 to −9.5 dBm, clean in-band |
| Twist (high minus low tone) | +0.8 to +1.8 dB | −0.6 to +0.4 dB. ETSI asks for 1–4 dB: raise the firmware's high-tone weighting, or fit C8/C9 at 3.3 nF |
| PWM carrier at 31.25 kHz | −59 dBm | −40 dBm |

The cell made **no difference** to any of these. On every simulated line, C1
alone keeps VDD above the cell's voltage while dialing.

## 4. The coin-cell circuit

```
  VCC ─ D5 BAT46WH ──────────────┬──► VDD ─ C1 470 µF ─ ATtiny85 (+ C4/C7)
                                 │
  BT1 CR1632 (+) ─ Q3 DMG2301L ─ D6 BAT46WH
         │           │ gate
         └─ R18 1M ──┴─── BATT_EN = PB2 (ATtiny pin 7)
```

- **Q3** is the cell switch. The firmware **arms** it (PB2 LOW) while the
  phone is off-hook and **releases** it (PB2 high-impedance) 250 ms after a
  hang-up.
- **R18** holds Q3 off whenever the MCU is not driving the pin.
- **D6** stops the loop supply ever charging the primary cell.
- **PB2 is the only free ATtiny pin.** On R2 it was the unused "mode" input;
  see `../hardware_r2/firmware/README.md` §3.
- **Holder:** an off-board CR1632 holder with flying leads, soldered to BT1's
  two pads (+ is the square pad).

The full firmware logic, including every situation (dialing, hook-flash,
hang-up, ringing, brown-out), is in [`firmware/README.md`](firmware/README.md) §2.

**SPICE:**
- On-hook drain with Q3 off is 0.03 µA, so the cell's life is set by its shelf
  life.
- If the firmware never released the cell, the MCU would drain it at
  0.93 mA, emptying it in **about 5 days**.
- That makes the release logic the only real risk the cell adds.

## 5. Building it without the cell (what used to be "V2")

**Leave off BT1 (the cell and its holder), Q3 (the switch), D6 (the
reverse-charge diode), R18, and optionally TP3–TP5.** This does **not** change
how the converter works:

- **Electrically:** D5 then feeds VDD alone, exactly as when the cell sits
  idle. That is how it behaves in every simulated case anyway (§3). PB2 drives
  nothing.
- **Firmware:** run the same V3 image. Arming and releasing just toggle an
  unconnected pin. No build option is needed.
- **The only loss** is the backup on a line delivering under about 1.5 mA.

In the JLC BOM and placement files (`kicad/fab/`), mark Q3, D6 and R18
do-not-place.

## 6. Test points and bench checks

| TP | Net | On-hook | Off-hook, idle | While dialing |
|---|---|---|---|---|
| TP1 | VCC (upper shunt) | 0 V | about 5.0 V | collapses at each break |
| TP2 | VDD (MCU) | 0 V | about 4.67 V | stays at 4.4 V or more on any line of 3 mA or more |
| TP3 | BATT+ | cell voltage (about 3.0–3.2 V) | cell voltage | cell voltage |
| TP4 | BATT_EN (Q3 gate) | about BATT+ (released) | about 0 V (armed) | about 0 V (armed) |
| TP5 | CELL (Q3 drain / D6 anode) | about 0 V | about BATT+ | about BATT+ |
| TP6 | GND (circuit common) | — | — | — |

On the first board:
1. **TP1** at 10, 25 and 40 mA: about 5.0 V with no oscillation on a scope.
   The real TLV431 has a capacitive-load stability region the model doesn't
   capture.
2. **DTMF level and twist** at the FXS; every digit decodes.
3. **Pulse detection** at the slowest dial you need. The firmware's 150 ms
   digit timeout splits digits on dials under about 6.7 pps.
4. **Cell release** (if fitted): TP4 returns to BATT+ within about 250 ms of
   hanging up.
5. **Q2's temperature** at 40 mA (about 0.19 W).

## 7. Bill of materials

The full BOM is `kicad/fab/BRD170127_V3_bom.csv`. These are the cell parts
(leave them off for a cell-less build):

| Ref | Part | Note |
|---|---|---|
| BT1 | CR1632 + off-board holder with wire leads | two through-hole pads |
| Q3 | DMG2301L-7 (P-MOS, SOT-23) | cell switch |
| D6 | BAT46WH (SOD-123) | reverse-charge block; the same part as D1–D5 |
| R18 | 1 MΩ, 0805 | Q3 gate pull-up to BATT+ |
| TP3–TP5 | test pads | BATT+, BATT_EN, CELL |
