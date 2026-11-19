# Project context — Pulse-to-Tone Converter

Persistent notes for future sessions (human or Claude): **why** this repo exists,
what has been done, the decisions made along the way, and what is still open.
Last updated 2026-11-18. Update this file when a goal, decision or open item
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
4. **Rev V2 (`hardware_v2/`)** — new supply + passive DTMF filter, with
   `sim/supply_sim.py`.
   - **Decision / correction:** the first V2 draft put a series LDO between the
     reservoir cap and the MCU. That was **wrong**: during a pulse gap the only
     requirement is VDD > BOD, and any series element costs headroom. Final V2:
     shunt clamp (unavoidable — the converter is in series with the loop and must
     absorb excess current) + **MCU driven directly from the reservoir**, 2.7 V
     BOD, idle-sleep, passive filter replacing the MCP6022.
5. **Rev V3 (`hardware_v3/`)** — V2 plus a **CR1632 coin-cell backup** ("option
   B"), with `schematic.svg` and `sim/battery_backup_sim.py`.
   - Cell → **P-MOS Q_batt** (driven by `BATT_EN`, PB1, active-low, pull-up to
     BATT+ so default is off) → **D_rev** (PMEG Schottky, blocks charging the
     primary cell) ORed with **D_loop** into VDD. The cell only sources during
     loop-open gaps; between pulses the loop holds VDD above it.
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

## Key decisions (summary)

- No series regulator in the MCU path (direct drive from the reservoir).
- Shunt clamp stays; coin cell bridges the pulse gaps rather than trying to make
  the loop alone carry the MCU through them.
- DTMF tones are generated on loop power (loop closed), never from the cell.
- On-hook detection in firmware, reusing the existing sense — BOM stays
  P-FET + diode + battery.

## Concerns

- **Nothing is bench-tested or routed.** V2/V3 are circuits + simulations; there
  is no KiCad/EasyEDA layout yet.
- **Cell-drain risk:** if on-hook detection fails, the armed cell drains fast.
  Bench-verify that the loop sense really tracks the hook switch.
- **Two corrections already happened** (series-LDO idea; "MCU loses power
  on-hook"). Double-check power-path reasoning against the sims before stating it
  as fact.
- `ANALYSIS.md` was written before the firmware source was added and still says
  the source isn't in the folder — its firmware section is structural only.
- **Licensing:** firmware and anything combined with it is GPL v3; the board
  derives from upstream — check upstream terms before redistributing hardware.

## Open items / possible next steps

- Create the GitHub repo (`origin` = `JoeFloyd-on-Github/Pulse-To-Tone-Converter`
  is configured but the repo doesn't exist) and push; decide public vs private.
- Build and bench-test V3 on a real low-current VoIP ATA: VDD through a full
  dial, the on-hook disarm, cell current when idle.
- Route a V3 PCB in the original form factor.
- Firmware features from `ANALYSIS.md` §4–5 (redial, speed dial, timing config).
- Refresh `ANALYSIS.md`'s firmware section now that the source is in `firmware/`.
- A reference clone of upstream sits at `/tmp/lb_pdtmf` (temporary — lost on
  reboot; re-clone from github.com/LieBtrau/pulse-dtmf-converter if needed).
