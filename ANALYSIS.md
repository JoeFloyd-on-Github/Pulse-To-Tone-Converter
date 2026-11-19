# Engineering analysis: Pulse-to-Tone Converter (BRD170127, ATtiny85)

A review of the design as built. It covers three areas that cause trouble in
the field:
- how the board is powered, and why low-loop-current IP phone systems starve it;
- why some voltage-regulator parts fail while others from the same batch work;
- how the ATtiny firmware behaves, and how it could be improved.

It ends with the feature set compared with other converters.

The design comes from LieBtrau's (Christoph Tack's) open-source
[Pulse to Tone Converter](https://hackaday.io/project/28557-pulse-to-tone-converter)
on Hackaday.io.

**Sources, in order of authority:**
1. The **firmware source** in [`firmware/`](firmware). It is the ground truth
   for everything the software does (§4).
2. The **upstream PCB netlist**, extracted from LieBtrau's EasyEDA export
   (`BRD170127.pcbdoc` in the upstream repo's `Hardware/` folder).
3. The schematic (`hardware_r2/Schematic_pluse_to_tone.JPG`), the BOM, and the
   measured-voltage photo (`hardware_r2/photos/20201219_140931-voltages.jpg`).
4. The ngspice simulation in [`hardware_v3/spice`](hardware_v3/spice/README.md).
5. ETSI ES 201 235-2, the DTMF transmitter specification (copy in `WEB_SAVES/`).

> **Revised 2026-11-18.** The first version of this document was written
> before the firmware source and the netlist were available. It guessed the
> software from the compiled `.hex`, and several of those guesses were wrong.
> In particular, the tones are **not** stepped out of several PB pins into a
> resistor ladder. They come from a **single PWM pin (PB1)**, and the line
> sense is on PB0. §1, §4 and §5 have been rewritten from the source; §2 and
> §3 have been corrected where they described the circuit wrongly.

---

## 1. How it works (topology)

The board sits **in series with one wire of the subscriber loop**, between the
FXS port (ATA, PBX or exchange) and the rotary phone. From the netlist:

- **CN3, "to rotary phone":** pin 3 goes to the bridge (LINE_A).
- **CN2, "to FXS", and CN1, "to DTMF phone":** their pins 3 are joined and go
  to the other side of the bridge (LINE_B). The DTMF phone is simply in
  parallel with the FXS port.
- **Pin 4 of all three jacks** is joined and passes straight through. The
  converter does not touch that wire.

```
  rotary phone ── LINE_A ─┐                      ┌─ LINE_B ── FXS (+ DTMF phone)
                          D1..D4 BAT46WH bridge
                  VCC (+) ┘                      └ VEE (−)

  VCC ─ U2 TLV431 shunt (R1 27k / R6 10k → 4.59 V nominal) ─ GND
  GND ─ U3 TLV431 shunt (R5 39k / R7 10k → up to 6.08 V) ─── VEE
  VCC ─ R4 1k bleeder ─ GND
  VCC ─ R3 56k ─┬─ R14 10k ─► PB0  (loop sense)          C5 100 nF to GND
  VCC ─ D5 BAT46WH ─► VDD ─ C1 470 µF ─► ATtiny85 (U1) + MCP6022 (U4)
  PB1 (PWM) ─ R12/R11 ─ U4.1 Sallen-Key low-pass ─ R8/C3 ─ U4.2 + Q1 (V→I, R2 15k)
                                                                  └─► into U3's REF node
```

**How it signals:**
- **Loop current** flows through the bridge and **both shunt regulators in
  series**. The converter drops VCC plus the U3 voltage plus two Schottky drops.
- **Pulse sense:** when the dial opens the loop, VCC collapses. The bleeder R4
  pulls it down quickly. The R3/C5 node (time constant 5.6 ms) falls, and PB0
  reads LOW. VDD keeps the MCU running through the break, because D5 blocks C1
  from discharging back into VCC.
- **Tone injection:** the ATtiny produces a PWM signal on PB1 (§4). The MCP6022
  filters it, then drives Q1 as a voltage-to-current converter. Q1's collector
  current goes into U3's REF node, which shifts the voltage U3 regulates to. In
  other words, **the DTMF tone is a modulation of the converter's own voltage
  drop**. The FXS sees it as an AC voltage in series with the loop. Nothing is
  "summed onto the line" by an amplifier.
- **The 8 MHz crystal (X1)** sets the tone frequencies (§4). ETSI requires
  ±1.5 %, which the internal RC oscillator does not guarantee. Burning the
  bootloader switches the fuses over to the crystal; see the toolchain guide
  `hardware_r2/BRD170127_Pulse_To_Tone_Converter.doc`.

**Measured rails** (off-hook, from the voltage photo):

| Node | Measured | Role |
|---|---|---|
| VCC | **4.66 V** | upper shunt output (4.59 V nominal: the reference reads 1.6 % high) |
| TLV431 ref | **1.26 V** | the 1.24 V reference node |
| VDD | **4.25 V** | ATtiny + op-amp supply (VCC minus ~0.4 V across D5) |
| VEE | **−6.59 V** | lower shunt / modulator |

This measurement puts about 11.2 V across the converter. The SPICE model of
the same netlist predicts **about 6.4 V when idle**: with the tone off, Q1's
standing current pulls U3 down to about 0.9 V. The measured −6.59 V matches
U3 with no Q1 current, near its 6.08 V maximum. Re-measure VEE with the MCU
idle and off-hook before relying on either figure. The drop matters for weak
lines (§2).

---

## 2. Power and loop current: why IP phone systems starve it

### What the board needs

The converter is **entirely line-powered**. Everything it does is paid for out
of the loop current the FXS port supplies. Before the shunts get anything, the
standing draw is:

- **R4, the 1 kΩ bleeder across VCC:** about **4.6 mA**, all the time. It is
  the single largest consumer. It does a real job (§1, pulse sense), but a much
  higher value would do it too.
- **MCP6022 dual op-amp:** about **2 mA** (1.0 mA per amplifier, typical). It
  runs all the time, not just during tones.
- **ATtiny85V at 8 MHz:** about **1.5 mA on average** while waiting or counting
  pulses, because the firmware idle-sleeps between timer interrupts (§4). It
  rises to roughly 4–5 mA while a tone is being generated.
- **Divider currents** in R1/R6, R5/R7 and R3: a few hundred µA.

In SPICE, **VDD falls below the ATtiny's 2.7 V brown-out level when the loop
current drops under about 6.5 mA**. That is the board's real floor.

### Why a classic POTS line is fine and a VoIP ATA often isn't

| | Real POTS / central office | Typical VoIP ATA (IP phone system) |
|---|---|---|
| Loop/battery voltage | −48 V | often −24 to −36 V, some less |
| Loop current | 20–40 mA, well-sourced | frequently **current-limited ~18–25 mA**, sometimes lower |
| Off-hook loop voltage | plenty of headroom | can collapse to a few volts under load |
| Behaviour during a **pulse** (loop open ~60 ms) | holds up easily | may sag or fold back |

Three things go wrong on a low-current IP port:

1. **Not enough current.** A shunt regulator only regulates when the source
   delivers more current than the load. With about 8 mA already spoken for,
   a weak port can leave nothing to shunt, so VCC sags.
2. **Not enough voltage headroom.** The FXS has to push its loop current
   through the converter's drop *and* the phone. A low-voltage ATA may not
   manage both.
3. **Pulse-dial ride-through.** Each pulse opens the loop for about 60 ms of
   every 100 ms, and the board runs on **C1 (470 µF)** in the gaps. SPICE shows
   C1 rides through a full "0" comfortably whenever the loop delivers at least
   about 10 mA. Below about 7 mA, VDD sags through the brown-out level while
   dialing.

### Recommendations (most effective first)

1. **Cut the standing current.** Raise R4 from 1k to around 22k (SPICE shows
   VCC still collapses fast enough for the pulse sense), and replace or remove
   the MCP6022. Rev V3 does both and runs from about 1.5 mA of loop current.
2. **Keep the reservoir on VDD, behind D5.** A capacitor on VCC would hold VCC
   up through each break and blind the pulse sense on PB0.
3. **Protect U3** (see §3). Rev V3 adds a PNP helper transistor to each shunt.
4. **Handle brown-out sensibly:** the 2.7 V BOD fuse, plus the firmware
   changes in §4.

---

## 3. Voltage-regulator sensitivity: "same batch, some work, some fail"

> **SPICE update, 2026-11-18** ([`hardware_v3/spice`](hardware_v3/spice/README.md)):
> a simulation of the real netlist does **not** support the "biased near Imin"
> explanation below. With 10 mA or more of loop current, sweeping Vref and Imin
> moves VCC by only ±0.07 V. That holds even for a TL431 fitted by mistake, with
> Imin up to 1 mA. Two other suspects stand out:
> - **U3 is overstressed.** It is the only path between GND and VEE, so it
>   carries the whole loop current: 25 mA on a typical ATA and 40 mA on a short
>   POTS loop, against the TLV431's 15 mA recommended maximum and 20 mA absolute
>   maximum.
> - **TLV431 loop stability.** The model cannot assess it.
>
> Rev V3 adds a PNP helper to each shunt, so each TLV431 runs at about 1.6 mA.
> The original discussion is kept below for the record.

The regulators are **two TLV431** adjustable shunt references (U2, U3). The
original hypothesis: when units from the same reel behave differently, the
classic cause is **biasing a shunt reference too close to its minimum operating
current**.

### Original hypothesis (not supported by the simulation)

A TLV431 only regulates once its **cathode current exceeds I_KA(min)**, which
is about 55 µA typical and 100 µA maximum for the TLV431, and up to 1 mA for a
TL431. If the board biased the reference near that minimum:

- a part at the **low end** of the I_KA(min) spread would regulate ("works");
- a part at the **high end** would never enter regulation ("fails").

The simulation contradicts this. Above about 10 mA of loop current, U2 gets
several mA of cathode current, far above any part's minimum. U3, by contrast,
gets *too much* current.

### Fixes

1. **Take the loop current off U3.** Let the TLV431 drive a PNP that carries
   the current, as rev V3 does. Alternatively, keep U3's current within its
   rating some other way.
2. **Measure it.** On a few boards, measure U3's current and temperature
   across the ATA's real loop-current range.
3. **Check stability.** Scope VCC and VEE for oscillation at several loop
   currents. TLV431s have a capacitive-load region where they ring, and
   part-to-part spread could decide which units sit inside it.

**Q1 (BC856B)** is not a pass element. It is the DTMF voltage-to-current
modulator (§1). Inside the op-amp's feedback loop its hFE spread hardly
matters. It mainly sets the small base current the op-amp has to supply.

---

## 4. Firmware: how the original works (from the source)

The source is the upstream sketch by Christoph Tack, GPL v3, in
[`firmware/src`](firmware/src). The last upstream change was on 2023-02-20: a
`pulsesBuffer` overflow fix, a configurable send delay, and a move to
PlatformIO. The repo's `firmware/images/pulse-dtmf-converter.ino_R0.hex` holds 2,482 bytes of
code, so the build uses about 30 % of the ATtiny85's 8 KB of flash. That image
is a build of an earlier revision, so it may not match the current source
exactly.

### Pin map

| ATtiny85 pin | Port | Use (source → board) |
|---|---|---|
| 1 | PB5 | RESET, pulled up by R13 10k |
| 2, 3 | PB3, PB4 | 8 MHz crystal X1 (C8/C9 18 pF) |
| 5 | PB0 | **loop/pulse sense input.** `pins.h` calls it `PIN_DTMF_OUT`, but it is passed to `RotaryDialer` as the *pulse* pin |
| 6 | PB1 | **DTMF PWM output OC1A.** Hard-coded as `dtmfpin = 1` in `dtmfgenerator.cpp` |
| 7 | PB2 | `PIN_MODE_SELECT`, read once at start-up with the internal pull-up. **Not connected on the board**, so the sketch always runs in mode 1 |

### Start-up

The board has no battery, so **it powers up from reset at every off-hook and
loses everything at hang-up**. Nothing survives between calls. `setup()` does
the following:
- reads PB2 once to choose the sending mode;
- `reducePower()`: turns off the USI, the analog comparator and the ADC;
- `dtmf.init()`: sets Timer1 to 8-bit fast PWM (OCR1C = 255), clocked from the
  system clock with the PLL unused, which gives **31.25 kHz PWM**;
- `rd.init()`: attaches Bounce2 to PB0 as a plain input (no pull-up) with a
  **10 ms debounce interval**.

The code does not set the clock source or the brown-out detector. Those come
from the fuses written by "Burn Bootloader" in the Arduino IDE flow. Note that
`platformio.ini` targets the **`attiny45`** board, and upstream says the
PlatformIO build was never tested on hardware. `pins.h` also refers to
ATtiny45 pin numbers. The two parts share the same pinout.

### Main loop

Each pass through the loop:
1. `sleepNow()` puts the chip into IDLE sleep. It wakes on the next interrupt:
   the `millis()` timer tick, or the 31.25 kHz Timer1 interrupt while a tone
   plays.
2. `rd.update()` decodes pulses.
3. The mode logic runs.

IDLE is the only sleep mode usable here, because `millis()` has to keep running.

### Pulse decoding (`rotarydialer.cpp`)

- Each **falling edge** on PB0 is counted as one pulse. That is the start of a
  loop break, after Bounce2's 10 ms stability window.
- Every falling edge restarts a **150 ms one-shot timer**. When 150 ms pass
  with no new falling edge, the digit is complete and `available()` returns
  true.
- The count maps to a digit: **n pulses → "n", 10 pulses → "0"**. A
  compile-time `REVERSE_DIAL_MODE` switch gives digit = 10 − n, for New Zealand.

What this means in practice:
- **Dial speed:** the 150 ms is measured from break start to break start.
  A 10 pps dial (100 ms per pulse) works. A slow dial under about 6.7 pps
  (over 150 ms per pulse) splits one digit into several.
- **No check on pulse width.** Anything that opens the loop for more than about
  10 ms counts as a pulse. A **hook-flash is decoded as the digit 1** and sends
  a DTMF "1". Hanging up also counts as a pulse, but the MCU is losing power
  and the loop is open, so that one is harmless. Line glitches longer than
  10 ms add phantom pulses.
- **More than 10 pulses** (two digits merged by a fast hand) gives a character
  that is not in the keypad string `123A456B789C*0#D`. `generateTone()` returns
  false and **the digit is dropped silently**, though the 80 ms delays still run.
- **Only 0–9 can be produced.** The generator knows all 16 keys, but nothing
  maps a dial count to \*, #, or A–D.
- The original pulses are **not suppressed**. The converter sits in series
  with the loop, so the FXS always sees the loop breaks as well as the tones.
  An exchange that also accepts pulse dialing receives both.

### Sending modes (`pulse-dtmf-converter.ino`)

- **Mode 1** (PB2 open; the board's only mode): digits are stored in a
  15-entry buffer. Any further digits are dropped silently. **1,200 ms after the
  last digit** (`DTMF_DELAY_AFTER_LAST_DIALED_DIGIT_ms`), the whole number is
  sent as **80 ms tone + 80 ms pause** per digit.
- **Mode 0** (PB2 grounded): each digit is sent as an 80 ms tone as soon as it
  completes, 150 ms after its last pulse.
- **Both modes block.** `delay()` stops `rd.update()` from running. A digit
  dialed while a number is being sent is lost. In mode 1 a full 15-digit buffer
  takes about 2.4 s to send.

### DTMF synthesis (`dtmfgenerator.cpp`, `timer.cpp`)

This is direct digital synthesis (DDS). The Timer1 overflow interrupt fires
every 32 µs, which is every 256 CPU cycles, and updates the PWM duty each time:
- Two 16-bit phase accumulators each advance by a tuning word on every
  interrupt. Tables for 8, 12 and 16 MHz are selected by `F_CPU`; any other
  clock is a compile error.
- The top 8 bits of each accumulator are masked with `& 0x7F`. They index a
  **128-entry, 7-bit sine table**, which therefore plays twice per accumulator
  wrap. The tuning words are half of 2¹⁶·f/31,250 to match.
- **Frequency accuracy:** the 8 MHz tuning words give 697.1, 769.6, 851.6,
  941.3, 1209.3, 1336.1, 1477.2 and 1632.7 Hz. Every one is within 0.05 % of
  nominal. In practice the crystal's tolerance sets the accuracy, comfortably
  inside ETSI's ±1.5 %.
- **Mixing:** duty = high tone + ¾ × low tone. That makes the **high tone
  2.5 dB louder** than the low one at the pin, inside ETSI's required 1–4 dB.
  The maximum duty is 222 of 255, so it never clips.
- **Timing:** 80 ms tones with 80 ms pauses meet ETSI's 65 ms minimums and
  stay under its 90 ms recommended maximum burst.
- `stopTone()` disconnects OC1A from the timer and drives PB1 LOW.

**The hardware sets the line level and the final twist** (§1). SPICE of the
original netlist gives about −7 dBm for the low tone and −6 dBm for the high
tone into 600 Ω. That is about −9.4 and −7.8 dBV, inside ETSI's windows of
−11 dBV (+2.5/−2) and −9 dBV (+2/−2.5). The twist after the filter is +0.8 to
+1.8 dB, at the low edge of 1–4 dB. The simulated waveform also clips at its
troughs, because U3 bottoms out
([`hardware_v3/spice`](hardware_v3/spice/README.md)).

### What the firmware does not do

- It stores nothing: no EEPROM use, no settings, no redial.
- It has no watchdog and no supply monitoring. The ADC is switched off, and
  brown-out handling is left entirely to the BOD fuse.
- It does not validate pulse width, detect hook-flash, or report errors.
- It has no programming mode. Timing values are compile-time constants:
  10 ms debounce, 150 ms digit timeout, 1,200 ms send delay, 80/80 ms tone and
  pause, 15-digit buffer.
- Minor: `SingleTimer` compares `millis() < start + timeout`, which breaks when
  `millis()` wraps after about 49 days. That cannot happen here, because power
  is lost at every hang-up.

### Improvements

No extra hardware is needed for any of these.

1. **Measure break length.** Time each break from falling edge to rising edge.
   Then:
   - accept roughly 30–100 ms breaks as dial pulses;
   - treat roughly 100–500 ms as a **hook-flash** and pass it through without
     sending a "1";
   - treat anything longer as hang-up;
   - end a digit a fixed time after the last *make*, rather than after the last
     break start. That makes slow dials work.
2. **Non-blocking playback.** Replace the `delay(80)` loops with a small state
   machine driven by `millis()`, so dialing during playback isn't lost.
3. **Don't drop digits silently.** For counts of 11 or more, play an error
   tone, or split the count at an inter-digit gap.
4. **Make timing and level configurable.** Expose the 150 ms, 1,200 ms and
   80/80 ms values and the ¾ low-tone weighting, so the tones can be tuned for
   fussy ATAs. Raising the high-tone share gives more twist margin.
5. **Use the spare flash and the EEPROM** for the features in §5. About 5.5 KB
   of flash and all 512 B of EEPROM are free.

> **Rev V3 note:** the V3 board uses **PB2 for the coin-cell enable**, because
> it is the only free pin. A V3 build must remove the `PIN_MODE_SELECT` read
> and fix `mode` in code. See `firmware/src/battery_control.ino`.

---

## 5. Feature set vs. other converters

| Feature | In the original firmware | How to add |
|---|---|---|
| A/B/C/D, \*, # tones | generator supports all 16 keys, but **dialing can only produce 0–9** | map special dial sequences to them, e.g. in a programming mode |
| **Speed dial** | no | programming mode (for example a long first digit), store numbers in **EEPROM** (512 B holds many short numbers), recall by dialing one digit |
| **Last-number redial** | no (nothing survives hang-up) | store the last number in EEPROM, trigger with a reserved sequence |
| Pause / wait insertion | no; mode 1 sends the whole number 1.2 s after the last digit | timed gap on a reserved code (useful for PBX "9,…") |
| **Hook-flash / Recall** | **decoded as digit "1"**, so a DTMF 1 is sent after every flash | detect long breaks (§4 improvement 1) and pass them through without a tone |
| Programmable timing | compile-time constants only | §4 improvement 4 |
| Pulse pass-through | **always**: loop breaks are never suppressed | option to also suppress them (needs hardware) |
| Single-frequency or MF tones (e.g. 2600 Hz) | no | the DDS can produce any frequency or pair with new tuning words |

**Suggested minimum feature set:** hook-flash and pulse-width handling,
non-blocking playback, then EEPROM-backed **speed dial** and **last-number
redial** through a dial-based programming mode. None of it needs extra
hardware, and it all fits in the free flash and EEPROM.

---

## TL;DR

- **Topology:** a two-terminal device in series with one loop wire. The Schottky
  bridge feeds two series shunt regulators. VCC (about 4.6 V) powers the MCU
  through D5. Loop breaks are sensed on PB0. **DTMF is sent by modulating the
  lower shunt's voltage** from a single PWM pin (PB1) through an MCP6022 filter
  and Q1.
- **Powering:** the standing draw is about 8 mA (the 1k bleeder alone is
  4.6 mA, the op-amp 2 mA, the MCU about 1.5 mA). SPICE shows VDD drops under
  the brown-out level below about 6.5 mA of loop current. Rev V3 cuts that to
  1.5 mA.
- **Regulator batch failures:** SPICE does not support the "biased near Imin"
  theory. **U3 carries the full loop current, 25–40 mA, against a 15 mA
  rating**, which makes it the likely culprit. Rev V3 adds PNP helpers.
- **Firmware (from the source):**
  - Small and clean: idle-sleep loop, Bounce2 with a 10 ms debounce, a 150 ms
    digit timeout, 31.25 kHz PWM DDS from a crystal, frequencies within 0.05 %,
    2.5 dB pre-emphasis, 80/80 ms tones, which meets ETSI ES 201 235-2 timing.
  - Weaknesses: a hook-flash becomes a "1"; pulse width is never checked;
    11+ pulses are dropped silently; playback blocks dialing; dials slower
    than about 6.7 pps split digits; nothing is stored between calls.
  - About 70 % of flash and all of the EEPROM are free for features.
