# CLAUDE.md — Pulse-to-Tone Converter

**Before doing anything in this repo, read [`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md).**
It holds the goals, history, key decisions, concerns and open items from earlier
sessions — the things that are not obvious from the code or the git log.

## Quick orientation

- An ATtiny85 board (BRD170127) that sits inside a rotary phone and turns pulse
  dialing into DTMF. Derived from LieBtrau's (Christoph Tack) Hackaday project
  28557 / github.com/LieBtrau/pulse-dtmf-converter.
- **Each board revision is self-contained** — its own BOM, firmware and build docs:
  - `hardware_r2/` — the original kit board. `hardware_r2/firmware/` holds the
    **2019 upstream source (`31ae4ba`) that built the production image** (verified
    by rebuild), the images, the R2 toolchain/fuses, and the PB2 mode-jumper story.
  - `hardware_v3/` — the redesign (V2 was folded in: V3 without BT1/Q3/D6/R18 works
    the same). `firmware/` = 2023 upstream (`593e746`) + battery control, with
    build.sh, fuses and Arduino-as-ISP wiring; `spice/` = ngspice; `kicad/` = the
    board, generated from `design.py` (edit that and rerun the generators, not the
    `.kicad_*` files).
- `ANALYSIS.md` — engineering review of the original (power, regulators, firmware).
- `third_party/` — ATTinyCore 1.4.2-dev snapshot and Bounce2 2.55 as bundled with R2.

## Working conventions

- **Licensing matters here.** Both firmware folders are GPL v3 (© 2018 Christoph
  Tack); keep `hardware_r2/firmware` verbatim, describe every V3 change, and keep
  the credit in README/ANALYSIS. ATTinyCore and Bounce2 keep their own licenses.
- Don't mix the firmware versions: R2 = 2019 (3 s send delay, PB2 mode pin); V3 =
  2023-based (1.2 s, PB2 = BATT_EN). The old top-level `firmware/` (2023 source
  mislabelled as the kit firmware) was removed.
- V3 firmware builds with arduino-cli + ATTinyCore 1.5.2 + Bounce2 2.71
  (`hardware_v3/firmware/build.sh`); ATTinyCore's defaults (internal clock, BOD off)
  are wrong for this board — always use the FQBN in build.sh.
- V3 is routed, simulated and its firmware compiles, but **nothing V3 has been built
  or bench-tested**. Don't describe it as proven hardware.
- `hardware_v3/spice` (ngspice) is the only simulation; the KiCad schematic is
  authoritative.
- Commit or push only when asked. `main` tracks `origin/main` on GitHub
  (`JoeFloyd-on-Github/Pulse-To-Tone-Converter`).
