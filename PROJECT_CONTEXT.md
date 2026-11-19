# Project context — Pulse-to-Tone Converter

Persistent notes for future sessions (human or Claude): **why** this repo exists,
what has been done, the decisions made along the way, and what is still open.
Last updated 2026-11-18 (after the SPICE simulation and the V3 layout). Update this file when a goal, decision or open item
changes.

## Goal

Make the BRD170127 ATtiny85 pulse-to-tone converter (a build of LieBtrau's open
design) **work reliably on IP/VoIP phone systems** — FXS ports/ATAs with low loop
current (~20 mA limited) and low line voltage — where the original drops digits
or runs "in bursts or not at all". Secondary goals: document the design properly
and credit/license the upstream work correctly.

## What has been done (all on 2026-11-18)

1. **Initial commit** of the build files: Gerbers, schematic, BOM, build docs,
   photos, compiled `.hex`/`.BIN`, bundled ATTinyCore and Bounce2.
2. **`ANALYSIS.md`** — review of the original:
   - Loop-powered via a BAT46WH Schottky bridge into a **TLV431 shunt** (~4.66 V),
     then a series Schottky D5 to VDD (~4.25 V). Needs ~5–10 mA standing current
     and ~11 V of loop headroom; the MCP6022 active filter alone draws ~2 mA.
   - Each pulse opens the loop ~70 ms of every 100 ms → the reservoir droops and
     VDD browns out mid-dial on weak lines.
   - **"Same batch, some work, some fail"** → the TLV431s are biased near their
     minimum cathode current, so normal part spread decides which regulate.
   - Firmware: small, ~70 % flash free; ideas for brown-out-aware dialing, noisy
     pulse decoding, speed dial, redial, configurable timing.
3. **Credit** to LieBtrau / Hackaday 28557 added throughout.
4. **Rev V2 (`hardware_v2/`)** — new supply + passive DTMF filter. The first
   draft's "direct drive" (no D5, reservoir on the loop rail) and its Python sim
   were superseded on 2026-11-18. The page was rewritten from the SPICE results,
   the firmware source and upstream's Hackaday log. The log shows upstream already
   fixed the VoIP problems it hit: 2.7 V BOD for start-up, `sleepNow()` idle,
   R5 39k for DTMF level, and mode 1 for DECT. V2 is now the V3 circuit without
   the cell: PNP helpers, R17 22k, a passive filter into Q1. It is built on the
   V3 PCB with BT1/Q3/R18/D6/TP3–5 unfitted, and runs the upstream firmware unchanged.
5. **Rev V3 (`hardware_v3/`)** — V2 plus a **CR1632 coin-cell backup**: BT1 →
   Q3 DMG2301L (gate = BATT_EN on PB2, R18 1M pull-up to BATT+) → D6 BAT46WH into
   VDD, ORed with D5. The first draft (`schematic.svg`, the Python
   `sim/battery_backup_sim.py`, BATT_EN on PB1, a C_vc on the loop side) was
   removed or corrected on 2026-11-18. `hardware_v3/README.md` was rewritten from
   SPICE: the cell never sources current during dialing.
   - Holder: off-board CR1632 holder with flying leads; only BATT+/BATT− THT pads
     on the 49 × 34 mm board.
6. **Upstream firmware included** (`firmware/`, verbatim, GPL v3) and our
   `battery_control.ino` aligned with it (uses the existing `sleepNow()`).
7. **V3 on-hook detection, software only.** Corrected an earlier wrong claim that
   the MCU loses power on-hook — once armed, the cell holds VDD up, so hang-up
   must be detected. Reuses the RotaryDialer loop sense via a one-line
   `rd.lineIsOpen()` accessor: a sustained loop-open > ~250 ms (well above a
   ~70–100 ms pulse break and a ~100 ms hook-flash) → `cellRelease()`. No new
   sense hardware. Estimated ~0.3 µAh per call → cell life is shelf-life-limited.
8. **Session notes** (`CLAUDE.md`, this file) added, and the repo pushed to GitHub
   as `JoeFloyd-on-Github/Pulse-To-Tone-Converter` with full history.
9. **ngspice simulation** ([`hardware_v3/spice`](hardware_v3/spice/README.md)).
   The original's netlist was pulled from the upstream EasyEDA PCB export
   (`BRD170127.pcbdoc` in github.com/LieBtrau/pulse-dtmf-converter/Hardware).
   Models are generic and fitted to datasheets. Six benches: DC drop/budget,
   TLV431/TL431 spread, dialing on six line types, DTMF level/spectrum, hang-up
   and cell drain, on-hook ringing. Key results:
   - Original needs ≥ 6.5 mA of loop current; **V3 works from 1.5 mA**.
   - Original **U3 carries the whole loop current** (25–40 mA, rated 15 mA).
   - Original DTMF ≈ −6/−7 dBm but clips; V3 ≈ −8.6/−9.5 dBm, clean in-band,
     −40 dBm PWM carrier at 31 kHz.
   - The 470 µF reservoir rides through dialing on every line simulated, so
     **the coin cell never sources current**.
   The TLV431 batch-spread theory in `ANALYSIS.md` §3 is **not** supported (note added there).
10. **V3 circuit finalized during simulation:**
    - PNP helpers BCX53 (Q2, Q4) on both shunts, with 470 Ω bias resistors so a
      TL431 also works (2.2 kΩ failed with a TL431).
    - C12 1 nF compensation.
    - R17 22k bleeder replaces R4 1k.
    - Passive DTMF filter into Q1; values tuned on the DTMF bench: R2 39k, R5 47k, R13 160k.
    - BATT_EN moved to **PB2**: PB1 is the OC1A DTMF output, so the old
      `battery_control.ino` pin choice was wrong (fixed).
11. **KiCad 9 layout** ([`hardware_v3/kicad`](hardware_v3/kicad/README.md)),
    generated from `design.py` (one data file for schematic + PCB), auto-routed
    with Freerouting 2.5.0 (analytics disabled, network blocked).
    - Result: 0 DRC violations, 0 unconnected, 0 schematic-parity issues.
    - RJ11 holes identical to R2; 0805 passives.
    - Gerbers, drill, BOM and JLC-style CPL in `hardware_v3/kicad/fab/`.
    - The owner chose to **keep and populate** the coin cell despite the simulation result.

12. **Repo reorganized (2026-11-18):**
    - the original kit board's files moved from the top level to `hardware_r2/`
      (photos in `hardware_r2/photos/`);
    - the firmware images moved to `firmware/images/`;
    - ATTinyCore and Bounce2 moved to `third_party/`;
    - the byte-identical `Gerber_BRD170127_R2 (1).zip` was deleted.
    `hardware_r2/` holds the original R2 board; `hardware_v2/` holds the
    redesign. The two are different things despite the similar names.

## Reference material in the repo

- `hardware_r2/BRD170127_Pulse_To_Tone_Converter.doc` — the owner's toolchain/programming
  guide. Key points: program the ATtiny85 with an Arduino UNO as ISP (capacitor
  from RESET to GND on the UNO so it doesn't reset; SOP8 socket/clip); install
  ATTinyCore and Bounce2; select ATtiny85, programmer "Arduino as ISP"; **"Burn
  Bootloader" first — that only sets the fuses, switching the chip to the
  external 8 MHz crystal, so after that a crystal on pins 2–3 is required to
  program it**; then upload the firmware. Also holds the BOM with LCSC and
  Digi-Key numbers. Mostly screenshots; text is sparse.
- `hardware_r2/KIT_build.doc` — assembly guide for the **kit the owner sold**, based on the
  original rev R2 board: an 18-step component build order (diodes, Q1, TLV431s,
  resistors/caps, ATtiny85, MCP6022, crystal, RJ11s, C1 last).
- `WEB_SAVES/` (added 2026-11-18, ~32 MB, 241 files) — local copies of the web
  sources in case they go offline: the Hackaday.io project page and its full
  log, the EasyEDA project, the ATTinyCore and Bounce2 GitHub pages, the Arduino
  Project Hub "Programming ATtiny85 with Arduino Uno" article, and **ETSI ES 201
  235-2** (the DTMF transmitter spec). These are third-party copyrighted pages.

## Key decisions (summary)

- No series regulator in the MCU path: VDD comes from VCC through D5 only, with C1 on
  VDD. A reservoir on VCC ("direct drive") would blind the pulse sense.
- Shunt clamp stays, now with a PNP helper on each shunt (TLV431 only biases it).
- Coin cell kept and populated (owner's call, 2026-11-18), even though SPICE shows
  the reservoir alone rides through dialing down to ~1.5 mA.
- BATT_EN on PB2; the mode-select jumper is dropped and the mode is fixed in firmware.
- DTMF tones are generated on loop power (loop closed), never from the cell.
- On-hook detection in firmware, reusing the existing sense — BOM stays
  P-FET + diode + battery.

## Concerns

- **Nothing is bench-tested.** V3 is simulated (generic models) and routed, but
  no board has been built. Check TP1 for shunt oscillation, the DTMF level, and the
  on-hook disarm on the first board.
- The SPICE models don't cover TLV431 capacitive-load stability, temperature or
  absolute-max ratings (those were checked separately).
- Firmware for V3 is not written yet: `battery_control.ino` is integration notes,
  and the PB2 change (drop mode select) is not applied to the sketch.
- **Cell-drain risk:** if on-hook detection fails, the armed cell drains fast.
  Bench-verify that the loop sense really tracks the hook switch.
- **Two corrections already happened** (series-LDO idea; "MCU loses power
  on-hook"). Double-check power-path reasoning against the sims before stating it
  as fact.
- `ANALYSIS.md` was revised on 2026-11-18. It now uses the firmware source and
  the upstream netlist as ground truth. The first version had guessed the
  firmware from the .hex: an R-2R/multi-pin tone output (wrong; it is one PWM
  pin, PB1) and a sense on VEE (wrong; it is VCC via R3/C5 into PB0).
- **Licensing:** firmware and anything combined with it is GPL v3; the board
  derives from upstream — check upstream terms before redistributing hardware.

## Open items / possible next steps

- Build and bench-test V3 on a real low-current VoIP ATA: VDD through a full
  dial, the on-hook disarm, cell current when idle.
- Fill in LCSC numbers for 0805 passives, BCX53-16 and DMG2301L; check part
  rotations in the fab's assembly preview; order boards.
- Write the V3 firmware changes (PIN_BATT_EN = 2, fixed mode, on-hook disarm).
- Firmware features from `ANALYSIS.md` §4–5 (redial, speed dial, timing config).
- Firmware fixes found in the source review (ANALYSIS.md §4):
  - a hook-flash is decoded as digit "1";
  - pulse width is never checked;
  - 11+ pulses are dropped silently;
  - `delay()` blocks dialing during playback;
  - dials slower than about 6.7 pps split digits.
- A reference clone of upstream sits at `/tmp/lb_pdtmf` (temporary — lost on
  reboot; re-clone from github.com/LieBtrau/pulse-dtmf-converter if needed).
