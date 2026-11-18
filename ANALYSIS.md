# Engineering analysis — Pulse-to-Tone Converter (BRD170127, ATtiny85)

A full review of the design as built, focused on the three areas that cause the
most trouble in the field: **how the board is powered and why low-loop-current
IP phone systems starve it, why some voltage-regulator parts fail while others
from the same batch work, and how the ATtiny firmware behaves and could be
improved** — plus a look at the feature set versus other converters.

The design originates from LieBtrau's open-source
[Pulse to Tone Converter](https://hackaday.io/project/28557-pulse-to-tone-converter)
on Hackaday.io; this analysis reviews the board as built here.

This is reconstructed from the schematic (`Schematic_pluse_to_tone.JPG`), the
BOM, the measured-voltage photo (`20201219_140931-voltages.jpg`), the build
docs, and the compiled firmware (`pulse-dtmf-converter.ino_R0.hex`). The Arduino
source itself is not in this folder, so firmware comments are at the structural
level, read from the hex (keypad/sine tables), the BOM (Bounce2, external
crystal) and the build notes.

---

## 1. How it works (topology)

The board sits **inline in the subscriber loop** between the line/ATA and the
phone(s):

- **CN2 → "to FXS"** — the line side (the ATA/PBX FXS port that supplies loop
  current and voltage).
- **CN3 → "to rotary phone"** — the pulse-dialing phone whose dialing is converted.
- **CN1 → "to DTMF phone"** — a pass-through for a normal tone phone.

```
   FXS/ATA line ──┬── D1..D4 BAT46WH bridge ──► VCC (+)  ... VEE (−)
   (loop power)   │          (polarity-independent rectifier)
                  │                               │
   rotary phone ──┘        TLV431 shunt (U2)  ────┤ clamps VCC ≈ 4.66 V
                           TLV431 (U3) + R5/R7 ───┤ loop / pulse sense (VEE path)
                                                  │
                         Q1 BC856B + C1 470 µF ───┤ reservoir / pass
                                                  │
                            D5 BAT48WH (series) ──► VDD ≈ 4.25 V
                                                  │
                     VDD powers: ATtiny85 (U1) + MCP6022 (U4)
                                                  │
   ATtiny PB0..PB5 ─► R8..R13 (10k summing/R-2R) ─► MCP6022 2-stage active
   filter (C2 6n8, C3/C6 3n3) ─► clean DTMF sine summed onto the line.
```

**Signal path:** the ATtiny reads the rotary phone's pulse dialing (loop
interruptions), counts pulses into a digit, looks the digit up in the DTMF
matrix, and synthesizes the two DTMF tones by stepping two sine lookup tables out
of its PB pins; the MCP6022 turns those stepped/PWM outputs into a clean dual-tone
sine and injects it on the line. The **8 MHz crystal (X1)** is essential — DTMF
frequencies must hold to ±1.5%, which the ATtiny's internal RC oscillator cannot
do, which is why the build notes say the bootloader switches the part to the
external oscillator.

**Measured rails (off-hook, from the voltage photo):**

| Node | Measured | Role |
|---|---|---|
| VCC | **4.66 V** | rectified + shunt-regulated supply |
| TLV431 ref | **1.26 V** | the 1.24 V reference node (confirms the regulator) |
| VDD | **4.25 V** | ATtiny + op-amp supply (VCC − ~0.4 V across D5) |
| VEE | **−6.59 V** | negative rail / sense return |

Total voltage developed across the loop off-hook ≈ **VCC − VEE ≈ 11.2 V**. That
is the headroom the whole design has to live inside, and it is the crux of the
IP-phone problem below.

---

## 2. Power and loop current — why IP phone systems starve it

### What the board needs

The converter is **entirely line-powered** — there is no battery or wall supply.
Everything it does is paid for out of the subscriber-loop current the FXS port
provides. The continuous draw is dominated by:

- **MCP6022** dual op-amp — ~**2.1 mA** (1.0 mA/channel typical). This is the
  single biggest consumer and it runs **all the time**, not just while dialing.
- **ATtiny85V** at 8 MHz / 4.25 V — roughly **2–4 mA**.
- **TLV431 shunt regulators + bias dividers** — the shunt topology *deliberately
  burns* whatever current the loop supplies above the circuit's draw, plus the
  divider currents through R1/R3/R6 (27k/56k/10k) and R5/R7.

Call it **~5–10 mA continuous**, and the shunt wants *headroom above that* to
regulate.

### Why a classic POTS line is fine and a VoIP ATA often isn't

| | Real POTS / central office | Typical VoIP ATA (IP phone system) |
|---|---|---|
| Loop/battery voltage | −48 V | often −24 to −36 V, some less |
| Loop current | 20–40 mA, well-sourced | frequently **current-limited ~18–25 mA**, sometimes lower |
| Off-hook loop voltage | plenty of headroom | can collapse to a few volts under load |
| Behaviour during a **pulse** (loop open ~40 ms) | holds up easily | may sag or fold back |

Three things go wrong on a low-current IP port, and they compound:

1. **Not enough current for a shunt regulator.** A shunt regulator only works
   when the source delivers *more* current than the load, so the shunt can bleed
   the excess. On a 40 mA POTS line there's margin to spare. On an ATA
   current-limited to ~20 mA, with ~5–10 mA already consumed by the op-amp and
   MCU, there may be **nothing left to shunt**, so VCC never reaches its 4.66 V
   clamp — it just droops to whatever the loop can hold.
2. **Not enough voltage headroom.** The design assumes ~11 V across the loop. An
   ATA that only develops 6–8 V off-hook, minus the two Schottky drops of the
   bridge and the series D5, can leave VDD below the **~2.5 V the MCP6022 needs**
   — at which point tone generation degrades or stops even though the ATtiny
   (good to 1.8 V) is still alive.
3. **Pulse-dial ride-through.** Every rotary pulse *opens the loop* for ~33–40 ms.
   During that window the board runs entirely off **C1 (470 µF)**. If the ATA
   also sags or current-limits, the reservoir can't hold VDD up across a full
   10-pulse "0," and the MCU browns out or the op-amp quits **mid-dial** — which
   looks like "it works on some lines and not others," or "it drops digits."

### Recommendations (most effective first)

1. **Cut the standing current — replace the MCP6022.** It is the biggest draw
   and it runs continuously. The active filter only needs a few kHz of
   bandwidth, so a **low-Iq rail-to-rail dual op-amp** (e.g. MCP6L2/MCP6V7-class,
   ~a few hundred µA total, GBW ≥ ~200 kHz) can replace it and drop the baseline
   draw by ~1.5–2 mA. On a starved line that is often the difference between
   working and not. (Verify the filter's required GBW before swapping.)
2. **Only draw current while dialing.** Power the op-amp through a MOSFET/BJT the
   ATtiny enables **only during tone output**, and keep just the MCU (and its
   brown-out detector) alive between digits. This slashes average loop current
   and leaves far more in the reservoir for pulse ride-through.
3. **Lower the regulated setpoint.** 4.66 V is generous. The ATtiny85V runs to
   1.8 V and the op-amp to ~2.5 V, so regulating VCC to **~3.0–3.3 V** recovers
   over a volt of headroom for low-voltage ATAs and reduces the shunt's burden.
4. **Bigger reservoir for ride-through.** Increase **C1 to 1000 µF** (or add a
   second cap) so VDD holds across a full 10-pulse digit even when the ATA sags
   during the loop-open interval.
5. **Move off the shunt topology for low-current sources.** A **series-pass
   (LDO-style) regulator** only takes the current the load needs instead of
   demanding excess to shunt — a much better fit for a 20 mA ATA. (Watch the
   LDO's own quiescent current; see §3.)
6. **Add a brown-out / under-voltage lockout** in firmware (see §4) so a partial
   sag aborts cleanly and re-arms, instead of emitting corrupted tones.

---

## 3. Voltage-regulator sensitivity — "same batch, some work, some fail"

The regulators are **two TLV431** adjustable shunt references (U2, U3). The
symptom you describe — units from the same reel that should be identical, some
regulating and some not — is the classic signature of **biasing a shunt
reference too close to its minimum operating current**.

### Root cause

A TLV431 only regulates once its **cathode (bias) current exceeds I_KA(min)** —
on the order of **~100–500 µA depending on the unit and datasheet grade** — and
its reference has a **tolerance spread** (the measured 1.26 V vs 1.24 V nominal
is already ~1.5% high). This board biases the TLV431 through fairly high-value
dividers (R1 27k, R3 56k) *and* is trying to survive on scarce loop current, so
the cathode current sits **near the datasheet minimum**. The consequence:

- A part at the **low end** of the I_KA(min) spread regulates fine → "works."
- A part at the **high end** of the spread needs more bias current than the
  board provides at that loop current → it never enters regulation, VCC doesn't
  come up correctly → "fails."

Nothing is wrong with the failing parts; the **design is riding the edge of the
part's guaranteed operating window**, so normal lot-to-lot parametric spread
decides pass/fail. Low loop current makes it worse because there's even less
current available to bias the reference.

### Fixes

1. **Guarantee the bias current.** Add/lower a resistor from VCC to the TLV431
   cathode so that **even a worst-case I_KA(min) unit, at the lowest expected
   loop current, still sees comfortably more than the datasheet maximum
   I_KA(min)** (design for, say, ≥ 0.5–1 mA of cathode current). The tension is
   that more guaranteed bias = more current burned, which hurts §2 — so this
   trades directly against low-loop-current operation and argues again for a
   **series regulator** instead of a shunt.
2. **Measure it.** On a few boards, measure the TLV431 cathode current across the
   real range of ATA loop currents you need to support; confirm it stays above
   the part's I_KA(min) **max**, not just typical.
3. **Tighter / lower-I_KA part.** Use a reference specified for lower and more
   tightly bounded minimum operating current (or a 0.5% grade if offset also
   matters), so the spread that currently decides pass/fail is narrowed.
4. **If you keep the shunt, incoming-inspect or bin** the TLV431s for minimum
   operating current — but fixing the bias (1) removes the sensitivity entirely
   and is the right answer.

Also check **Q1 (BC856B)** if it is acting as a pass element: PNP **hFE spread**
(BC856B is the mid-gain "B" bin) can similarly cause unit-to-unit variation if
its base drive is marginal. Ensure worst-case low-hFE still saturates/passes the
needed current.

---

## 4. Firmware — behaviour and improvements

**What's there (from the hex + BOM + build notes):**

- Compiled sketch is **~2.48 KB of the ATtiny85's 8 KB flash (~70 % free)** —
  lots of room for new features.
- Built in the **Arduino IDE with ATTinyCore**, using the **Bounce2** library to
  debounce the pulse-dial input, and an **external 8 MHz crystal** for DTMF
  frequency accuracy.
- The hex contains the **DTMF keypad matrix** `123A456B789C*0#D` (so the design
  already knows the full 16-key set, **including the A/B/C/D fourth-column
  tones**) and **sine lookup tables** used to synthesize the two DTMF tones out
  of the PB pins into the MCP6022 filter.
- Operation: count loop-break pulses per digit (1 pulse → "1" … 10 pulses →
  "0"), map digit → DTMF pair, emit the tone for a fixed duration.

**Improvements (no extra hardware needed unless noted):**

1. **Brown-out-aware dialing.** Enable the ATtiny's **BOD**, and before emitting
   a tone, check VDD is healthy; if the loop sags mid-digit, **abort and re-arm**
   rather than emit a corrupted/partial tone. Directly addresses the
   low-loop-current field failures in §2.
2. **Robust pulse decoding for noisy IP lines.** VoIP loops ring and bounce more
   than a CO line. Make-/break-time **windowing** (accept only pulses within the
   ~61/39 ms make/break and ~10 pps envelope) plus the Bounce2 debounce rejects
   glitches; an **inter-digit timeout** (~200–300 ms of no pulses) reliably
   closes a digit. Consider auto-calibrating to the measured pulse rate.
3. **Configurable tone level and duration.** Expose DTMF **on/off duration** and
   **output amplitude** (and twist — high group typically +2 dB) so the tones
   meet spec on ATAs that are fussy about level; some ATA DTMF detectors reject
   too-short or too-quiet tones.
4. **Make the spare flash earn its keep** — the features in §5 all fit in the
   ~5.5 KB free.

> Note: the Arduino **source is not in this folder** (only the compiled
> `.hex`/`.bin`). To implement any of the above, recover the `.ino` (the sibling
> `Internal_Pulse_To_Tone_Converter` project on the same share carries related
> `dtmf.c`/`dtmf.h`/`rotarydial` source and a "blue-box-mode" variant worth
> diffing against this one).

---

## 5. Feature set vs. other converters

The hardware (ATtiny with ~70 % free flash, full DTMF matrix already in the
tables, a pass-through DTMF phone port) can support most "deluxe" converter
features purely in firmware:

| Feature | Status here | How to add |
|---|---|---|
| A/B/C/D tones | **matrix already present** | expose them via a programming/star code |
| **Speed dial** | not present | enter a programming mode (e.g. dial a long "0"/hook-flash), store N digit strings in **EEPROM** (512 B on the ATtiny85 — fits many short numbers), recall by dialing a 1-digit slot |
| **Last-number redial** | not present | keep the last dialed string in RAM/EEPROM, trigger on a reserved sequence |
| **Pause / wait insertion** | not present | insert a timed gap on a reserved code (useful for PBX "9,…") |
| **Hook-flash / Recall (R)** | check | pass a timed loop-break through as a flash for call-waiting/transfer |
| **Programmable inter-digit & tone timing** | fixed | see §4.3 |
| **Pulse pass-through / bypass** | partial (DTMF port) | option to relay dialing unmodified |
| Special MF / 2600 Hz ("blue-box") tones | in sibling variant | the related project ships a blue-box-mode build; the sine engine here can generate arbitrary tone pairs if desired |

**Suggested minimum feature add:** EEPROM-backed **speed dial** + **last-number
redial** + **configurable timing**, entered through a dialing-based programming
mode (no extra hardware, well within the free flash/EEPROM). Pair it with the
**brown-out-aware dialing** from §4 so the new features don't misbehave on the
very IP lines that motivated this review.

---

## TL;DR

- **Powering:** fully loop-powered through a Schottky bridge into a **shunt**
  regulator; it needs ~5–10 mA continuous and ~11 V of loop headroom. IP/VoIP
  FXS ports that current-limit (~20 mA) or run at low voltage can't feed a shunt
  topology, and the ~40 ms loop-open of each pulse browns out VDD mid-dial. Fix
  by cutting standing current (swap the MCP6022, power the analog only while
  dialing), lowering the regulated setpoint to ~3.3 V, enlarging C1, and moving
  to a series regulator.
- **Regulator batch failures:** the **TLV431 shunt references are biased near
  their minimum operating current**, so normal part-to-part spread in
  I_KA(min)/V_ref decides which ones regulate. Guarantee the cathode bias current
  (or go series-pass) and the sensitivity disappears.
- **Firmware:** small, clean, Arduino/ATTinyCore + Bounce2, full DTMF matrix and
  sine tables already present, ~70 % flash free. Add brown-out-aware dialing and
  noisy-line pulse decoding, then spend the free flash on **speed dial,
  last-number redial, and configurable timing**.
