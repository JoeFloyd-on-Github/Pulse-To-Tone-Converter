# Rev V3: ngspice simulation report

This folder holds a SPICE comparison of the **original board** (BRD170127 R1/R2)
and **rev V3**, the version laid out in [`../kicad`](../kicad). It uses ngspice 45
with generic models, each fitted to a datasheet figure. These numbers replace
the first-order Python estimates in the old `hardware_v2/sim` and
`hardware_v3/sim` (both since removed).

```sh
cd hardware_v3/spice
python3 run_sims.py                # all benches, about 15 min
python3 run_sims.py dtmf ring      # or just some of them
```

| File | Contents |
|---|---|
| `models.lib` | the generic models: BAT46W, BC856B, BCX53, a logic-level P-MOS, a behavioural TLV431 (Vref and Imin as parameters), an ATtiny85 load model and a CR1632 cell |
| `conv_orig.sub` | the original circuit. Its netlist was extracted from the upstream EasyEDA PCB export (`BRD170127.pcbdoc`), so it is the real board rather than a redraw. |
| `conv_v3.sub` | rev V3, with the same reference designators as the KiCad design |
| `run_sims.py` | the six test benches |
| `results/` | `summary.json`, CSV files and plots |

## How the generic models are fitted

Every model parameter comes from a datasheet number:

- **Schottky diodes:** forward voltage at 0.1 mA and 10 mA.
- **TLV431:** dynamic impedance 0.25 Ω (about 4 A/V), reference ±1.5 %, and
  a minimum cathode current of 55–100 µA. The model's internal bias draw makes
  a starved part fail the way the real one does.
- **ATtiny85V at 8 MHz:** about 1.5 mA in the firmware's idle-sleep loop and
  about 4.5 mA while it generates DTMF.

The models do not capture TLV431 stability with capacitive loads, temperature
effects, or the absolute-maximum ratings of any part. The real devices' ratings
are checked separately below.

## Results

### 1. DC: voltage drop and current budget (`dc.png`, `spread.png`)

| | original | rev V3 |
|---|---|---|
| Drop across the converter at 20 mA (idle) | 6.4 V | 8.1 V |
| Lowest loop current that keeps VDD above the 2.7 V brown-out | **6.5 mA** | **1.5 mA** |
| Current through TLV431 **U3** at 25 mA / 40 mA loop | **24.9 / 39.9 mA** | 1.6 / 1.7 mA |
| VCC spread across TLV431/TL431 tolerance at ≥ 10 mA | ±0.07 V | ±0.07 V |

- On the original board, **U3 carries the entire loop current**, because
  nothing else conducts between GND and VEE. On any normal line that is above
  the TLV431's 15 mA recommended maximum and 20 mA absolute maximum. V3 adds
  the PNP helpers Q2 and Q4, so each TLV431 only biases its transistor.
- On the original, the 1 kΩ bleeder (4.6 mA) and the MCP6022 (2 mA) use up
  the supply budget on weak lines. V3 removes both.
- **Correction to `../../ANALYSIS.md` §3:** sweeping Vref and Imin, including
  a TL431 fitted by mistake with Imin up to 1 mA, moves VCC by only ±0.07 V
  once the loop carries 10 mA or more. The simulation does **not** support
  "biased near Imin" as the cause of the batch failures. U3's overstress, or
  TLV431 loop stability, are more likely explanations.
- The extra 1.7 V that V3 drops comes from the PNP's Vbe and the 5.0 V
  setpoint. It is the cost of not overstressing U3.

### 2. Pulse dialing a "0" (`dial.png`)

Each line was run from steady state at 10 pulses per second with a 60/40
break/make ratio.

| Line | original: min VDD, pulses seen | V3 no cell | V3 + cell (fresh, mid, end-of-life) |
|---|---|---|---|
| POTS, 48 V | 3.80 V, 10/10 | 4.48 V, 10/10 | 4.48 V, 10/10 |
| ATA, 25 mA | 3.78 V, 10/10 | 4.48 V, 10/10 | 4.48 V, 10/10 |
| Weak ATA, 15 mA / 18 V | 3.77 V, 10/10 | 4.48 V, 10/10 | 4.48 V, 10/10 |
| Very weak, 10 mA / 15 V | 3.43 V, 10/10 | 4.48 V, 10/10 | 4.48 V, 10/10 |
| Starved, 7 mA | **2.25 V, below brown-out** | 4.48 V, 10/10 | 4.48 V, 10/10 |
| Starved, 3 mA | **0.67 V, dead** | 4.39 V, 10/10 | 4.39 V, 10/10 |

**The coin cell never supplies current in any of these cases.** With the V2
power fixes, the 470 µF reservoir keeps VDD above the cell's voltage through
every pulse break. The cell would only matter on a line delivering under about
1.5 mA, or one that opens for much longer than a dial break. It was kept and
populated at the owner's request (2026-11-18).

### 3. DTMF level at the FXS, into 600 Ω (`dtmf.png`)

The source is a 25 mA ATA. The PWM is modelled exactly as the firmware makes
it: Timer1 at 31.25 kHz, duty = (high tone + ¾ × low tone)/256.

| Digit | original low / high tone | V3 low / high tone | V3 twist |
|---|---|---|---|
| 1 | −7.2 / −5.6 dBm | −8.6 / −8.2 dBm | +0.4 dB |
| 5 | −7.0 / −6.3 dBm | −8.6 / −9.2 dBm | −0.6 dB |
| 9 | −7.8 / −6.0 dBm | −9.5 / −9.2 dBm | +0.3 dB |
| D | −7.2 / −5.9 dBm | −9.2 / −9.4 dBm | −0.2 dB |

- The original's waveform **clips**: its lower shunt bottoms out, leaving
  broadband distortion around −50 dBm across the voice band.
- V3 is clean in-band. It leaves a −40 dBm PWM carrier at 31.25 kHz, which is
  out of band. The original's 4th-order active filter took that down to −59 dBm.
- The V3 modulator was tuned on this bench. A first try (R2 36k, R5 39k,
  R13 20k) gave only −12 dBm and touched the shunt floor, so the values were
  changed to R2 39k, R5 47k, R13 160k. To push the high tone up, change the
  firmware's ¾ low-tone weighting, or use 3.3 nF for C8 and C9 (this raises
  the carrier by about 3 dB).

### 4. Hang-up and cell drain (`onhook.png`)

| Case | Result |
|---|---|
| Firmware disarms 250 ms after the loop opens | VDD collapses; cell current 0.02 µA |
| Firmware never disarms (a fault) | MCU stays on the cell at **0.93 mA**: a 125 mAh CR1632 is flat in about 5 days |
| On-hook drain with the gate pulled up | 0.03 µA typical; 1.04 µA if Q3 is at its worst-case 1 µA leakage (about 11 years for 100 mAh) |

### 5. Incoming ring while on-hook (`ring.png`)

The source is 75 V rms at 25 Hz on 48 V, through a 1 µF + 2.5 kΩ ringer.

The ring current through the bridge **powers the MCU on both boards** (VDD
4.2–4.7 V). On V3, that means the firmware wakes up, arms the cell, and
disarms it once the ringing stops. That is harmless: VDD sits above the cell
voltage during the ring. The shunts clamp VCC at ≤ 5.06 V. The lower shunt
briefly reaches 8.9 V on the first cycle, well under the TLV431's 18 V rating.

### 6. Shunt stability (TLV431 + PNP)

A 5→40 mA loop step settles in less than 0.3 ms with 0.12 V of overshoot.
C12 (1 nF, cathode→REF) is fitted for margin. The real TLV431 has a
load-capacitance stability region the model does not capture, so **check VCC
(TP1) for oscillation on the first board**.

## What to verify on the bench

1. TP1 (VCC) ≈ 5.0 V with no ringing on a scope, at 10, 25 and 40 mA.
2. The DTMF level at the FXS. Compare with the −8 to −9 dBm predicted here,
   and check the exchange or ATA decodes every digit.
3. TP4 (BATT_EN) goes back to about 3 V within 250 ms of hanging up
   (firmware), and TP3/TP5 confirm the cell is isolated on-hook.
4. Q2/Q4 temperature at 40 mA, if the line can deliver it. Expect about
   0.19 W in Q2 (5 V × the excess loop current) and 0.09 W in Q4. A BCX53
   in SOT-89 is rated about 1 W on a small copper pad.
