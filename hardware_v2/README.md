# Pulse-to-Tone Converter, rev V2: the low-loop-current supply

Rev V2 is the power and DTMF front-end redesign of the BRD170127
pulse-to-tone converter. It is meant to work on **IP/VoIP ports (ATAs) with
low loop current**, where the original is marginal. Rev V3 is the same circuit
plus a CR1632 coin-cell backup.

V2 has no board of its own. **Build it as the rev-V3 PCB with the coin-cell
parts left off** (see "Building a V2"). The circuit description and the numbers
on this page come from:
- the ngspice simulation in [`../hardware_v3/spice`](../hardware_v3/spice/README.md),
  whose "V3, no cell" cases are exactly V2;
- the original firmware source in [`../firmware/src`](../firmware/src);
- upstream's own development log (a copy of the Hackaday.io project log is in
  `../WEB_SAVES/`).

> **Rewritten 2026-11-18.** The earlier version of this page relied on a
> first-order Python model. It proposed **"direct drive"**: dropping the
> series diode D5 and putting the reservoir straight on the loop rail. The
> simulation shows that breaks pulse detection. The firmware counts pulses
> when VCC collapses at each loop break (PB0, see `../ANALYSIS.md` §1, §4).
> A reservoir on VCC holds it up through the break, so no pulses are seen.
> D5 and the reservoir on VDD stay. The old Python model (`sim/`) has been
> removed. An unverified reference to a third-party "2024 VoIP fix" has also
> been dropped.

---

## 1. What upstream already fixed

LieBtrau's log records the original breadboard failing on an internet
gateway's FXS port ("runs in bursts", digits not dialed). Upstream fixed it in
four steps, and all four are in the firmware source and the R1/R2 board:

| Problem (upstream log) | Upstream fix | Where it is now |
|---|---|---|
| Unreliable start-up: VCC ramps slowly through the 470 µF, with no reset circuit and BOD off | **enable the ATtiny's 2.7 V BOD** (instead of a reset controller) | the fuse setting written by "Burn Bootloader" (not in code) |
| VCC sagging to 3.08 V with the MCU always active | **IDLE sleep in the main loop**, woken by the Timer0 tick, which raised the sag to 3.57 V | `sleepNow()` in `pulse-dtmf-converter.ino` |
| DTMF too weak for the receiver | **R5 raised to 39k** (more swing on the lower shunt) | R1/R2 board |
| The DECT base expects the number first, then the tones | **mode 1**: collect the number, send it 1.2 s after the last digit | `mode` / `DTMF_DELAY_AFTER_LAST_DIALED_DIGIT_ms` |

## 2. What still limits the original (SPICE of the real netlist)

The simulation in [`../hardware_v3/spice`](../hardware_v3/spice/README.md)
uses the upstream EasyEDA netlist and generic, datasheet-fitted models:

- **The current floor is about 6.5 mA.** About 8 mA is spoken for before the
  shunts get anything: the 1 kΩ bleeder R4 takes 4.6 mA, the MCP6022 2 mA, and
  the idle-sleeping ATtiny about 1.5 mA. Below about 6.5 mA of loop current,
  VDD falls under the 2.7 V BOD. Dialing a "0" on a 7 mA line takes VDD down
  to **2.25 V**, so the MCU resets.
- **U3 is overstressed.** It is the only path between GND and VEE, so it
  carries the **whole loop current**: 25 mA on a typical ATA and 40 mA on a
  short POTS loop. The TLV431 is rated 15 mA, 20 mA absolute maximum.
- **The DTMF clips.** The level is fine (about −7/−6 dBm into 600 Ω), but the
  troughs flatten where U3 bottoms out. That leaves distortion around −50 dBm
  across the voice band.
- **Ride-through is not the problem.** C1 (470 µF on VDD) carries the MCU
  through a full "0" on every line that delivers 10 mA or more.

## 3. The V2 circuit

Everything not listed here is unchanged from R2: the bridge D1–D4, the pulse
sense R3/C5/R14, D5, C1 470 µF on VDD, and the ATtiny85 with its crystal and
reset pull-up. The reference designators are those of the KiCad design in
[`../hardware_v3/kicad`](../hardware_v3/kicad/README.md).

| Block | Original (R2) | V2 | Why |
|---|---|---|---|
| Upper shunt | TLV431 U2 alone; R1 27k / R6 10k → 4.59 V | U2 drives a **BCX53 PNP, Q2** (R15 470 Ω base-emitter, R16 220 Ω), C12 1 nF compensation; R1 100k / R6 33k → **5.0 V** | the PNP carries the excess loop current. With 470 Ω, a TL431 fitted by mistake still works (2.2 kΩ failed with one). |
| Bleeder | R4 **1 kΩ** (4.6 mA) | R17 **22 kΩ** | still pulls VCC down fast at each break, so PB0 sees every pulse, for a twentieth of the current |
| Lower shunt / modulator | TLV431 U3 alone (R5 39k / R7 10k) | U3 drives a **BCX53 PNP, Q4** (R19 470 Ω, R20 220 Ω), C11 10 nF; **R5 47k** | U3 runs at about 1.6 mA instead of the full loop current. R5 sets the DTMF swing. |
| DTMF path | PB1 PWM → MCP6022 4th-order active filter → U4.2 + Q1 V-to-I (R2 15k) | PB1 PWM → **passive 2-pole RC** (R12 10k / R13 160k / C8 4.7 nF, then R10 10k / C9 4.7 nF) → **Q1 emitter follower**, R2 **39k** | removes the op-amp's 2 mA. Q1's emitter resistor makes the V-to-I converter without it. |

**How the modulator works without an op-amp:** PB1 carries the DDS PWM
(31.25 kHz, duty = high tone + ¾ × low tone, see `../ANALYSIS.md` §4). The RC
filter turns that into the tone pair. Q1's emitter follows its base, so its
current is (VDD − V_base − 0.65 V)/R2. That current goes into U3's REF node and
moves the lower shunt's voltage. The values centre the current at about 53 µA
during a tone, with ±48 µA of swing. At idle (PB1 LOW) the current is about
101 µA, which keeps the converter's drop low.

## 4. Simulated performance

These are the "V3, no cell" results from
[`../hardware_v3/spice`](../hardware_v3/spice/README.md).

| | original (R2) | **V2** |
|---|---|---|
| Lowest loop current keeping VDD above the 2.7 V BOD | 6.5 mA | **1.5 mA** |
| Converter drop, idle, at 20 mA | 6.4 V | 8.1 V |
| TLV431 U3 current at 25 / 40 mA loop | 24.9 / 39.9 mA | **1.6 / 1.7 mA** |
| Dialing "0", lowest VDD: POTS / ATA 25 mA / weak ATA 15 mA | 3.80 / 3.78 / 3.77 V | 4.48 V on all three |
| Dialing "0", lowest VDD: 10 / 7 / 3 mA lines | 3.43 / **2.25** / **0.67 V** | 4.48 / 4.48 / 4.39 V |
| Pulses detected (10 sent), every line | 10/10 | 10/10 |
| DTMF into 600 Ω, low / high tone | about −7 / −6 dBm, clipped | about −8.6 to −9.5 dBm, clean in-band |
| PWM carrier at 31.25 kHz | −59 dBm | −40 dBm |

**The cost:** V2 drops about 1.7 V more than the original. The PNPs' Vbe and
the 5.0 V setpoint account for it; it is the price of not overstressing U3. The
weakest line simulated (15 V compliance) still has enough headroom.

**The twist after the filter** is about −0.6 to +0.4 dB. ETSI ES 201 235-2 asks
for the high tone to be 1–4 dB above the low one. Two ways to get there: raise
the firmware's weighting (for example high + ⅝ × low), or fit C8/C9 at 3.3 nF,
which also raises the 31 kHz carrier by about 3 dB. The original's twist was
+0.8 to +1.8 dB.

## 5. Building a V2

Use the rev-V3 board ([`../hardware_v3/kicad`](../hardware_v3/kicad/README.md))
and **leave the coin-cell circuit unpopulated: BT1, Q3, R18, D6, TP3, TP4,
TP5**. Nothing else depends on those parts. In the JLC BOM and placement
files, mark Q3, R18 and D6 as do-not-place.

**Firmware:** the upstream sketch in `../firmware/src` runs unchanged. On the
V3 board, PB2 goes only to the (unfitted) cell parts, so it floats high with
the internal pull-up and the sketch runs in mode 1, as on R2. Program the fuses
for the external 8 MHz crystal and the **2.7 V BOD**, using "Burn Bootloader"
as described in `../hardware_r2/BRD170127_Pulse_To_Tone_Converter.doc`.

## 6. What to check on the first board

Nothing here has been built yet:

1. **TP1 (VCC)** is about 5.0 V with no oscillation on a scope at 10, 25 and
   40 mA. The real TLV431 has a capacitive-load stability region the model
   doesn't capture.
2. The **DTMF level and twist** at the FXS, and that every digit decodes.
3. **Pulse detection** on PB0 with R17 at 22k, at the slowest dial you need to
   support. The firmware's 150 ms digit timeout splits digits on dials under
   about 6.7 pps (`../ANALYSIS.md` §4).
4. **Q2's temperature** at 40 mA (about 0.19 W).
